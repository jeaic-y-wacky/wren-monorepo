"""
Unit tests for agent tools - no API calls.

Run with: uv run pytest tests/unit/
"""

import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

from agent.context import AgentContext


class MockRunContextWrapper:
    """Mock for RunContextWrapper that doesn't require the agents library."""
    def __init__(self, context: AgentContext):
        self.context = context


@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temporary workspace directory."""
    workspace = tmp_path / "scripts"
    workspace.mkdir()
    return workspace


@pytest.fixture
def agent_context(temp_workspace):
    """Create an AgentContext with temp workspace."""
    return AgentContext(
        user_request="test request",
        workspace_dir=temp_workspace,
    )


@pytest.fixture
def mock_ctx(agent_context):
    """Create a mock context wrapper."""
    return MockRunContextWrapper(agent_context)


class TestWriteScript:
    """Tests for write_wren_script tool."""

    @pytest.mark.asyncio
    async def test_writes_file(self, mock_ctx, temp_workspace):
        """Test that write_wren_script creates a file."""
        from agent.tools.write_script import write_wren_script

        code = "import wren\nprint('hello')"
        result = await write_wren_script.on_invoke_tool(
            mock_ctx,
            json.dumps({"filename": "test.py", "code": code})
        )

        script_path = temp_workspace / "test.py"
        assert script_path.exists()
        assert script_path.read_text() == code
        assert "test.py" in result

    @pytest.mark.asyncio
    async def test_adds_py_extension(self, mock_ctx, temp_workspace):
        """Test that .py is added if missing."""
        from agent.tools.write_script import write_wren_script

        await write_wren_script.on_invoke_tool(
            mock_ctx,
            json.dumps({"filename": "test", "code": "# code"})
        )

        assert (temp_workspace / "test.py").exists()

    @pytest.mark.asyncio
    async def test_updates_context(self, mock_ctx, temp_workspace):
        """Test that context is updated after writing."""
        from agent.tools.write_script import write_wren_script

        code = "import wren"
        await write_wren_script.on_invoke_tool(
            mock_ctx,
            json.dumps({"filename": "test.py", "code": code})
        )

        assert mock_ctx.context.script_path is not None
        assert mock_ctx.context.script_content == code

    @pytest.mark.asyncio
    async def test_sanitizes_filename(self, mock_ctx, temp_workspace):
        """Test that path traversal is prevented."""
        from agent.tools.write_script import write_wren_script

        await write_wren_script.on_invoke_tool(
            mock_ctx,
            json.dumps({"filename": "../../../etc/passwd.py", "code": "# evil"})
        )

        # Should only create passwd.py in workspace, not traverse
        assert (temp_workspace / "passwd.py").exists()
        assert not Path("/etc/passwd.py").exists()


class TestTestScript:
    """Tests for test_wren_script tool."""

    @pytest.mark.asyncio
    async def test_no_script_error(self, mock_ctx):
        """Test error when no script exists."""
        from agent.tools.test_script import test_wren_script

        result = await test_wren_script.on_invoke_tool(mock_ctx, "{}")
        result_json = json.loads(result)

        assert result_json["valid"] is False
        assert result_json["error_code"] == "NO_SCRIPT"

    @pytest.mark.asyncio
    async def test_file_not_found(self, mock_ctx):
        """Test error when script file doesn't exist."""
        from agent.tools.test_script import test_wren_script

        mock_ctx.context.script_path = Path("/nonexistent/script.py")
        result = await test_wren_script.on_invoke_tool(mock_ctx, "{}")
        result_json = json.loads(result)

        assert result_json["valid"] is False
        assert result_json["error_code"] == "FILE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_runs_wren_test(self, mock_ctx, temp_workspace):
        """Test that wren test is called correctly."""
        from agent.tools.test_script import test_wren_script

        # Create a test script
        script = temp_workspace / "test.py"
        script.write_text("import wren")
        mock_ctx.context.script_path = script

        # Mock subprocess to avoid actually running wren
        mock_result = MagicMock()
        mock_result.stdout = json.dumps({"valid": True, "metadata": {}})
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = await test_wren_script.on_invoke_tool(mock_ctx, "{}")

            # Verify subprocess was called with correct args
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert "wren" in call_args[0][0]
            assert "test" in call_args[0][0]
            assert "--json" in call_args[0][0]

        result_json = json.loads(result)
        assert result_json["valid"] is True

    @pytest.mark.asyncio
    async def test_stores_result_in_context(self, mock_ctx, temp_workspace):
        """Test that test result is stored in context."""
        from agent.tools.test_script import test_wren_script

        script = temp_workspace / "test.py"
        script.write_text("import wren")
        mock_ctx.context.script_path = script

        mock_result = MagicMock()
        mock_result.stdout = json.dumps({
            "valid": False,
            "error_type": "AgentFixableError",
            "error_code": "SYNTAX_ERROR",
            "message": "Invalid syntax",
        })

        with patch("subprocess.run", return_value=mock_result):
            await test_wren_script.on_invoke_tool(mock_ctx, "{}")

        assert mock_ctx.context.last_test_result is not None
        assert mock_ctx.context.last_test_result["valid"] is False


class TestAgentContext:
    """Tests for AgentContext."""

    def test_default_workspace(self):
        """Test default workspace is set."""
        ctx = AgentContext()
        assert ctx.workspace_dir is not None

    def test_is_valid(self):
        """Test is_valid() method."""
        ctx = AgentContext()
        assert ctx.is_valid() is False

        ctx.last_test_result = {"valid": True}
        assert ctx.is_valid() is True

        ctx.last_test_result = {"valid": False}
        assert ctx.is_valid() is False

    def test_can_iterate(self):
        """Test can_iterate() method."""
        ctx = AgentContext(max_iterations=3)
        assert ctx.can_iterate() is True

        ctx.iteration_count = 3
        assert ctx.can_iterate() is False

    def test_record_error(self):
        """Test error history tracking."""
        ctx = AgentContext()
        ctx.iteration_count = 2

        ctx.record_error({"error_code": "TEST"})

        assert len(ctx.error_history) == 1
        assert ctx.error_history[0]["iteration"] == 2
        assert ctx.error_history[0]["error"]["error_code"] == "TEST"
