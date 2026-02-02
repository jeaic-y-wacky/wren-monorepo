"""
Test Script Tool - Tests Wren scripts using the CLI.
"""

import json
import subprocess
from pathlib import Path

from agents import RunContextWrapper, function_tool

from ..context import AgentContext


@function_tool
async def test_wren_script(
    ctx: RunContextWrapper[AgentContext],
    script_path: str | None = None,
) -> str:
    """Test a Wren script using `wren test` and get structured error feedback.

    Args:
        script_path: Optional path to script. If not provided, uses current script from context.

    Returns:
        JSON-formatted test results including:
        - valid: Whether the script is valid
        - error_type: "AgentFixableError" | "UserFacingConfigError" | "InternalError"
        - error_code: Machine-readable error code
        - message: Human-readable error message
        - fix_hint: Actionable suggestion for fixing
        - location: {file, line, col} if available
    """
    # Verbose logging: entry
    if ctx.context.verbose:
        print(f"  [iter {ctx.context.iteration_count}] test_wren_script called (script_path={script_path})")

    # Determine script path
    if script_path:
        path = Path(script_path)
    elif ctx.context.script_path:
        path = ctx.context.script_path
    else:
        return json.dumps(
            {
                "valid": False,
                "error_type": "AgentFixableError",
                "error_code": "NO_SCRIPT",
                "message": "No script to test. Write a script first using write_wren_script.",
                "fix_hint": "Call write_wren_script(filename, code) to create a script first.",
            },
            indent=2,
        )

    if not path.exists():
        return json.dumps(
            {
                "valid": False,
                "error_type": "AgentFixableError",
                "error_code": "FILE_NOT_FOUND",
                "message": f"Script not found: {path}",
                "fix_hint": "Check the script path or write the script first.",
            },
            indent=2,
        )

    # Run wren test with JSON output
    try:
        # Find wren_src directory (go up: tools/ -> agent/ -> wren_agent/ -> wren/)
        wren_src_dir = Path(__file__).parent.parent.parent.parent / "wren_src"

        # Ensure we pass absolute path to wren test
        abs_path = path.resolve()

        # Use uv run from wren_src to access the wren CLI
        result = subprocess.run(
            ["uv", "run", "wren", "test", str(abs_path), "--json"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(wren_src_dir),
        )

        # Try to parse JSON output
        output = result.stdout.strip()
        if output:
            try:
                test_result = json.loads(output)
            except json.JSONDecodeError:
                # If stdout isn't valid JSON, check stderr
                test_result = {
                    "valid": False,
                    "error_type": "InternalError",
                    "error_code": "PARSE_ERROR",
                    "message": result.stderr or result.stdout or "Unknown error during test",
                    "fix_hint": "Check the script syntax and try again.",
                }
        else:
            # No stdout, check stderr
            test_result = {
                "valid": False,
                "error_type": "InternalError",
                "error_code": "NO_OUTPUT",
                "message": result.stderr or "wren test produced no output",
                "fix_hint": "Ensure wren CLI is installed and working.",
            }

        # Store in context
        ctx.context.last_test_result = test_result

        # Track error history for learning
        if not test_result.get("valid", False):
            ctx.context.record_error(test_result)

        # Verbose logging
        if ctx.context.verbose:
            valid = test_result.get("valid", False)
            if valid:
                meta = test_result.get("metadata", {})
                integrations = meta.get("integrations", [])
                schedules = meta.get("schedules", [])
                print(f"  [iter {ctx.context.iteration_count}] test_wren_script → ✓ VALID")
                if integrations:
                    print(f"    integrations: {integrations}")
                if schedules:
                    for s in schedules:
                        print(f"    schedule: {s['cron']} → {s['func_name']}")
            else:
                err_type = test_result.get("error_type", "Unknown")
                msg = test_result.get("message", "")
                hint = test_result.get("fix_hint", "")
                print(f"  [iter {ctx.context.iteration_count}] test_wren_script → ✗ FAILED ({err_type})")
                print(f"    error: {msg}")
                if hint:
                    print(f"    hint: {hint}")

        return json.dumps(test_result, indent=2)

    except subprocess.TimeoutExpired:
        error_result = {
            "valid": False,
            "error_type": "InternalError",
            "error_code": "TIMEOUT",
            "message": "Script test timed out after 30 seconds",
            "fix_hint": "Check for infinite loops or long-running operations at module level.",
        }
        ctx.context.last_test_result = error_result
        return json.dumps(error_result, indent=2)

    except FileNotFoundError:
        error_result = {
            "valid": False,
            "error_type": "UserFacingConfigError",
            "error_code": "WREN_CLI_NOT_FOUND",
            "message": "wren CLI not found. Is it installed?",
            "fix_hint": "Install the Wren SDK: pip install wren-sdk or uv add wren-sdk",
        }
        ctx.context.last_test_result = error_result
        return json.dumps(error_result, indent=2)

    except Exception as e:
        error_result = {
            "valid": False,
            "error_type": "InternalError",
            "error_code": "UNEXPECTED_ERROR",
            "message": str(e),
            "fix_hint": "An unexpected error occurred. Check the error message.",
        }
        ctx.context.last_test_result = error_result
        return json.dumps(error_result, indent=2)
