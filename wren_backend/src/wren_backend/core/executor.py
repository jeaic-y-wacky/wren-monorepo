"""Script executor using subprocess for basic isolation."""

import asyncio
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import structlog

from wren_backend.models.run import RunStatus

logger = structlog.get_logger()

# Path to wren SDK source (for PYTHONPATH injection)
_WREN_SRC_PATH = Path(__file__).parent.parent.parent.parent.parent / "wren_src" / "src"

# Load environment variables from monorepo root .env (for API keys like OPENAI_API_KEY)
_MONOREPO_ROOT = Path(__file__).parent.parent.parent.parent.parent
_DOTENV_PATH = _MONOREPO_ROOT / ".env"


def _load_dotenv_vars() -> dict[str, str]:
    """Load variables from .env file if it exists."""
    env_vars = {}
    if _DOTENV_PATH.exists():
        for line in _DOTENV_PATH.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                env_vars[key.strip()] = value.strip()
    return env_vars


_DOTENV_VARS = _load_dotenv_vars()


@dataclass
class ExecutionResult:
    """Result of a script execution."""

    status: RunStatus
    exit_code: int | None
    stdout: str
    stderr: str
    error_message: str | None = None


class Executor:
    """Execute scripts in isolated subprocess."""

    def __init__(self, timeout_seconds: int = 300, python_path: str | None = None):
        self.timeout_seconds = timeout_seconds
        self.python_path = python_path or sys.executable

    async def execute(
        self,
        script_content: str,
        func_name: str,
        env: dict[str, str] | None = None,
    ) -> ExecutionResult:
        """Execute a script function in a subprocess.

        Args:
            script_content: The Python script to execute
            func_name: The function to call within the script
            env: Environment variables to pass to the subprocess

        Returns:
            ExecutionResult with status, output, and any errors
        """
        log = logger.bind(func_name=func_name)

        # Create a wrapper script that imports and calls the function
        wrapper_script = f"""
import sys
import traceback

# Execute the user script to define functions
exec('''{script_content.replace("'", "\\'")}''')

# Call the target function
if __name__ == "__main__":
    try:
        result = {func_name}()
        if result is not None:
            print(result)
    except Exception as e:
        print(f"Error executing {func_name}: {{e}}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
"""

        # Write to temp file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as f:
            f.write(wrapper_script)
            script_path = Path(f.name)

        try:
            log.info("executing_script", script_path=str(script_path))

            # Prepare environment
            process_env = dict(os.environ)  # Start with current env
            process_env.update(_DOTENV_VARS)  # Add .env vars (API keys, etc.)
            if env:
                process_env.update(env)  # Add injected credentials

            # Run the script using uv from wren_src to get all dependencies
            wren_src_dir = _WREN_SRC_PATH.parent  # wren_src directory (parent of src/)

            # Run the script
            process = await asyncio.create_subprocess_exec(
                "uv",
                "run",
                "python",
                str(script_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=process_env if process_env else None,
                cwd=str(wren_src_dir),  # Run from wren_src to use its venv
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(), timeout=self.timeout_seconds
                )
                stdout = stdout_bytes.decode("utf-8", errors="replace")
                stderr = stderr_bytes.decode("utf-8", errors="replace")
                exit_code = process.returncode

                if exit_code == 0:
                    log.info("execution_success", exit_code=exit_code)
                    return ExecutionResult(
                        status=RunStatus.SUCCESS,
                        exit_code=exit_code,
                        stdout=stdout,
                        stderr=stderr,
                    )
                else:
                    log.warning(
                        "execution_failed",
                        exit_code=exit_code,
                        stderr=stderr[:500],
                    )
                    return ExecutionResult(
                        status=RunStatus.FAILED,
                        exit_code=exit_code,
                        stdout=stdout,
                        stderr=stderr,
                        error_message=f"Script exited with code {exit_code}",
                    )

            except asyncio.TimeoutError:
                log.error("execution_timeout", timeout=self.timeout_seconds)
                process.kill()
                await process.wait()
                return ExecutionResult(
                    status=RunStatus.TIMEOUT,
                    exit_code=None,
                    stdout="",
                    stderr="",
                    error_message=f"Execution timed out after {self.timeout_seconds} seconds",
                )

        except Exception as e:
            log.exception("execution_error", error=str(e))
            return ExecutionResult(
                status=RunStatus.FAILED,
                exit_code=None,
                stdout="",
                stderr=str(e),
                error_message=f"Failed to execute script: {e}",
            )
        finally:
            # Clean up temp file
            try:
                script_path.unlink()
            except OSError:
                pass
