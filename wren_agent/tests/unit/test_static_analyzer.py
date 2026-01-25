"""
Unit tests for static analyzer - Wren API validation and security checks.

Run with: uv run pytest tests/unit/test_static_analyzer.py -v
"""

import pytest

from agent.tools.static_analyzer import AnalysisResult, StaticAnalyzer
from agent.tools.wren_validator import ValidationIssue, WrenAPIValidator


# Module-scoped fixtures - created once, reused across all tests
# This dramatically reduces semgrep startup overhead
@pytest.fixture(scope="module")
def validator():
    """Provide a shared WrenAPIValidator instance."""
    return WrenAPIValidator()


@pytest.fixture(scope="module")
def analyzer():
    """Provide a shared StaticAnalyzer instance."""
    return StaticAnalyzer()


class TestWrenAPIValidator:
    """Tests for Wren API validation using fuzzy matching."""

    def test_valid_ai_method(self, validator):
        """Test that valid wren.ai methods pass."""
        code = """
import wren

result = wren.ai.extract(text, MyModel)
"""
        issues = validator.validate(code)
        ai_method_issues = [i for i in issues if i.error_code == "UNKNOWN_AI_METHOD"]
        assert len(ai_method_issues) == 0

    def test_unknown_ai_method_with_suggestion(self, validator):
        """Test that typos get 'Did you mean?' suggestions."""
        code = """
import wren

result = wren.ai.extrct(text)
"""
        issues = validator.validate(code)
        assert len(issues) >= 1
        issue = next(i for i in issues if i.error_code == "UNKNOWN_AI_METHOD")
        assert "extrct" in issue.message
        assert "extract" in issue.fix_hint

    def test_unknown_ai_method_classify_typo(self, validator):
        """Test classify typo detection."""
        code = """
import wren

cat = wren.ai.clasify(text, ["a", "b"])
"""
        issues = validator.validate(code)
        issue = next(i for i in issues if i.error_code == "UNKNOWN_AI_METHOD")
        assert "clasify" in issue.message
        assert "classify" in issue.fix_hint

    def test_unknown_ai_method_summarize_typo(self, validator):
        """Test summarize typo detection."""
        code = """
import wren

summary = wren.ai.summerize(text)
"""
        issues = validator.validate(code)
        issue = next(i for i in issues if i.error_code == "UNKNOWN_AI_METHOD")
        assert "summerize" in issue.message
        assert "summarize" in issue.fix_hint

    def test_unknown_integration_with_suggestion(self, validator):
        """Test integration name typos get suggestions."""
        code = """
import wren

gmal = wren.integrations.gmal.init()
"""
        issues = validator.validate(code)
        issue = next(i for i in issues if i.error_code == "UNKNOWN_INTEGRATION")
        assert "gmal" in issue.message
        assert "gmail" in issue.fix_hint

    def test_integration_in_function_warns(self, validator):
        """Test that integration init inside function is flagged."""
        code = """
import wren

@wren.on_email()
def handler(email):
    gmail = wren.integrations.gmail.init()
    gmail.send(to="x@y.com", subject="Hi")
"""
        issues = validator.validate(code)
        issue = next(i for i in issues if i.error_code == "INTEGRATION_IN_FUNCTION")
        assert "module level" in issue.fix_hint

    def test_integration_at_module_level_ok(self, validator):
        """Test that integration init at module level is fine."""
        code = """
import wren

gmail = wren.integrations.gmail.init()

@wren.on_email()
def handler(email):
    gmail.send(to="x@y.com", subject="Hi")
"""
        issues = validator.validate(code)
        function_issues = [i for i in issues if i.error_code == "INTEGRATION_IN_FUNCTION"]
        assert len(function_issues) == 0

    def test_extract_missing_type_warns(self, validator):
        """Test that extract without type is flagged."""
        code = """
import wren

result = wren.ai.extract(email_text)
"""
        issues = validator.validate(code)
        issue = next(i for i in issues if i.error_code == "EXTRACT_MISSING_TYPE")
        assert "type" in issue.fix_hint.lower()

    def test_extract_with_type_ok(self, validator):
        """Test that extract with type is fine."""
        code = """
import wren

result = wren.ai.extract(email_text, BookingModel)
"""
        issues = validator.validate(code)
        type_issues = [i for i in issues if i.error_code == "EXTRACT_MISSING_TYPE"]
        assert len(type_issues) == 0

    def test_extract_with_target_type_kwarg_ok(self, validator):
        """Test that extract with target_type kwarg is fine."""
        code = """
import wren

result = wren.ai.extract(email_text, target_type=BookingModel)
"""
        issues = validator.validate(code)
        type_issues = [i for i in issues if i.error_code == "EXTRACT_MISSING_TYPE"]
        assert len(type_issues) == 0

    def test_syntax_error_returns_empty(self, validator):
        """Test that syntax errors don't crash the validator."""
        code = """
def broken(
    pass
"""
        issues = validator.validate(code)
        # Should return empty, let other tools handle syntax errors
        assert issues == []


class TestStaticAnalyzer:
    """Tests for the combined static analyzer."""

    def test_safe_code_passes(self, analyzer):
        """Test that safe code passes validation."""
        code = """
import wren
from pydantic import BaseModel

class Booking(BaseModel):
    name: str

gmail = wren.integrations.gmail.init()

@wren.on_email()
def handler(email):
    booking = wren.ai.extract(email.body, Booking)
    gmail.send(to="x@y.com", subject="Got it")
"""
        result = analyzer.analyze(code)
        # Should pass (may have warnings but valid=True)
        assert result.valid is True

    def test_wren_warnings_dont_block(self, analyzer):
        """Test that Wren API warnings don't block write."""
        code = """
import wren

# Missing type in extract - should warn, not block
result = wren.ai.extract(text)
"""
        result = analyzer.analyze(code)
        # Should be valid (warnings only)
        assert result.valid is True
        assert len(result.warnings) > 0

    def test_analysis_result_to_dict_valid(self, analyzer):
        """Test AnalysisResult.to_dict() for valid code."""
        result = AnalysisResult(valid=True, issues=[])
        d = result.to_dict()
        assert d["valid"] is True
        assert "warnings" not in d or d["warnings"] is None

    def test_analysis_result_to_dict_with_warnings(self):
        """Test AnalysisResult.to_dict() with warnings."""
        issues = [
            ValidationIssue(
                severity="MEDIUM",
                error_code="TEST_WARN",
                message="Test warning",
                fix_hint="Fix it",
                line=5,
            )
        ]
        result = AnalysisResult(valid=True, issues=issues)
        d = result.to_dict()
        assert d["valid"] is True
        assert len(d["warnings"]) == 1

    def test_analysis_result_to_dict_blocked(self):
        """Test AnalysisResult.to_dict() for blocked code."""
        issues = [
            ValidationIssue(
                severity="CRITICAL",
                error_code="block-eval-exec",
                message="eval is blocked",
                fix_hint="Remove eval",
                line=3,
            )
        ]
        result = AnalysisResult(valid=False, issues=issues)
        d = result.to_dict()
        assert d["valid"] is False
        assert d["error_type"] == "SecurityError"
        assert d["error_code"] == "block-eval-exec"


class TestWriteScriptIntegration:
    """Full integration tests for write_script with static analysis."""

    @pytest.fixture
    def mock_ctx(self, tmp_path):
        """Create a mock context for testing."""
        from agent.context import AgentContext

        class MockCtx:
            def __init__(self):
                self.context = AgentContext(workspace_dir=tmp_path)

        return MockCtx()

    @pytest.mark.asyncio
    async def test_blocks_dangerous_import_os(self, mock_ctx, tmp_path):
        """Dangerous import os is blocked, file not written."""
        import json

        from agent.tools.write_script import write_wren_script

        code = """
import os
os.system("whoami")
"""
        result = await write_wren_script.on_invoke_tool(
            mock_ctx, json.dumps({"filename": "evil.py", "code": code})
        )

        # Should return JSON error
        result_json = json.loads(result)
        assert result_json["valid"] is False
        assert result_json["error_type"] == "SecurityError"
        assert "block-dangerous-imports" in result_json["error_code"]

        # File should NOT exist
        assert not (tmp_path / "evil.py").exists()

    @pytest.mark.asyncio
    async def test_blocks_eval(self, mock_ctx, tmp_path):
        """eval() is blocked, file not written."""
        import json

        from agent.tools.write_script import write_wren_script

        code = """
user_input = "1 + 1"
result = eval(user_input)
"""
        result = await write_wren_script.on_invoke_tool(
            mock_ctx, json.dumps({"filename": "eval_script.py", "code": code})
        )

        result_json = json.loads(result)
        assert result_json["valid"] is False
        assert "block-eval-exec" in result_json["error_code"]
        assert not (tmp_path / "eval_script.py").exists()

    @pytest.mark.asyncio
    async def test_blocks_file_write(self, mock_ctx, tmp_path):
        """File write operations are blocked."""
        import json

        from agent.tools.write_script import write_wren_script

        code = """
with open("data.txt", "w") as f:
    f.write("secret")
"""
        result = await write_wren_script.on_invoke_tool(
            mock_ctx, json.dumps({"filename": "writer.py", "code": code})
        )

        result_json = json.loads(result)
        assert result_json["valid"] is False
        assert "block-file-write" in result_json["error_code"]
        assert not (tmp_path / "writer.py").exists()

    @pytest.mark.asyncio
    async def test_blocks_subprocess(self, mock_ctx, tmp_path):
        """subprocess import is blocked."""
        import json

        from agent.tools.write_script import write_wren_script

        code = """
import subprocess
subprocess.run(["ls", "-la"])
"""
        result = await write_wren_script.on_invoke_tool(
            mock_ctx, json.dumps({"filename": "shell.py", "code": code})
        )

        result_json = json.loads(result)
        assert result_json["valid"] is False
        assert not (tmp_path / "shell.py").exists()

    @pytest.mark.asyncio
    async def test_allows_safe_wren_script(self, mock_ctx, tmp_path):
        """Safe Wren script is written successfully."""
        import json

        from agent.tools.write_script import write_wren_script

        code = """
import wren
from pydantic import BaseModel

class Order(BaseModel):
    item: str
    quantity: int

gmail = wren.integrations.gmail.init()

@wren.on_email(sender="*@orders.com")
def handle_order(email):
    order = wren.ai.extract(email.body, Order)
    gmail.send(to="warehouse@company.com", subject=f"New order: {order.item}")
"""
        result = await write_wren_script.on_invoke_tool(
            mock_ctx, json.dumps({"filename": "order_handler.py", "code": code})
        )

        # Should succeed
        assert "order_handler.py" in result
        assert "written" in result.lower() or "Script" in result

        # File should exist with correct content
        script_path = tmp_path / "order_handler.py"
        assert script_path.exists()
        assert "wren.ai.extract" in script_path.read_text()

    @pytest.mark.asyncio
    async def test_allows_with_warnings(self, mock_ctx, tmp_path):
        """Code with warnings is written, warnings returned."""
        import json

        from agent.tools.write_script import write_wren_script

        # Missing type in extract - should warn but still write
        code = """
import wren

@wren.on_schedule("0 9 * * *")
def daily():
    result = wren.ai.extract(some_text)
    print(result)
"""
        result = await write_wren_script.on_invoke_tool(
            mock_ctx, json.dumps({"filename": "with_warnings.py", "code": code})
        )

        # Should succeed (warnings don't block)
        script_path = tmp_path / "with_warnings.py"
        assert script_path.exists()

        # Result should mention warnings
        assert "warning" in result.lower()

    @pytest.mark.asyncio
    async def test_context_updated_on_success(self, mock_ctx, tmp_path):
        """Context is updated after successful write."""
        import json

        from agent.tools.write_script import write_wren_script

        code = """
import wren

@wren.on_schedule("0 9 * * *")
def job():
    print("done")
"""
        await write_wren_script.on_invoke_tool(
            mock_ctx, json.dumps({"filename": "context_test.py", "code": code})
        )

        # Context should be updated
        assert mock_ctx.context.script_path is not None
        assert mock_ctx.context.script_content == code

    @pytest.mark.asyncio
    async def test_context_updated_on_block(self, mock_ctx, tmp_path):
        """Context stores error result when blocked."""
        import json

        from agent.tools.write_script import write_wren_script

        code = "import os"
        await write_wren_script.on_invoke_tool(
            mock_ctx, json.dumps({"filename": "blocked.py", "code": code})
        )

        # Context should have the error result
        assert mock_ctx.context.last_test_result is not None
        assert mock_ctx.context.last_test_result["valid"] is False

    @pytest.mark.asyncio
    async def test_filename_sanitization(self, mock_ctx, tmp_path):
        """Path traversal in filename is blocked."""
        import json

        from agent.tools.write_script import write_wren_script

        code = """
import wren

@wren.on_schedule("* * * * *")
def tick():
    pass
"""
        # Try path traversal
        await write_wren_script.on_invoke_tool(
            mock_ctx, json.dumps({"filename": "../../../etc/evil.py", "code": code})
        )

        # Should write to workspace, not /etc
        assert not (tmp_path.parent.parent.parent / "etc" / "evil.py").exists()
        # Should write as just "evil.py" in workspace
        assert (tmp_path / "evil.py").exists()

    @pytest.mark.asyncio
    async def test_adds_py_extension(self, mock_ctx, tmp_path):
        """Filename without .py gets extension added."""
        import json

        from agent.tools.write_script import write_wren_script

        code = """
import wren

@wren.on_schedule("0 0 * * *")
def midnight():
    pass
"""
        await write_wren_script.on_invoke_tool(
            mock_ctx, json.dumps({"filename": "no_extension", "code": code})
        )

        assert (tmp_path / "no_extension.py").exists()
