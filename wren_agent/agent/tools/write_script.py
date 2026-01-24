"""
Write Script Tool - Writes Python scripts to the workspace.

Includes static analysis to catch security issues and common mistakes
before the script is written to disk.
"""

import json
from pathlib import Path

from agents import function_tool, RunContextWrapper

from ..context import AgentContext
from .static_analyzer import get_analyzer


@function_tool
async def write_wren_script(
    ctx: RunContextWrapper[AgentContext],
    filename: str,
    code: str,
) -> str:
    """Write a Python script using the Wren SDK to the workspace.

    Args:
        filename: Name of the script file (e.g., "email_processor.py")
        code: The Python code to write

    Returns:
        Confirmation message with the script path, or error if blocked
    """
    # Static analysis BEFORE writing
    analyzer = get_analyzer()
    analysis = analyzer.analyze(code)

    if not analysis.valid:
        # Return structured error matching test_wren_script format
        result = analysis.to_dict()
        ctx.context.last_test_result = result
        return json.dumps(result, indent=2)

    # Store warnings for context (but continue with write)
    if analysis.warnings:
        ctx.context.last_test_result = analysis.to_dict()

    # Ensure workspace exists (resolve to absolute path)
    workspace = ctx.context.workspace_dir.resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    # Sanitize filename
    if not filename.endswith(".py"):
        filename = f"{filename}.py"

    # Remove any path components for security
    filename = Path(filename).name

    script_path = workspace / filename

    # Write the script
    script_path.write_text(code, encoding="utf-8")

    # Update context
    ctx.context.script_path = script_path
    ctx.context.script_content = code

    # Reset iteration count for new scripts, increment for rewrites
    if ctx.context.last_test_result is None:
        ctx.context.iteration_count = 0
    else:
        ctx.context.iteration_count += 1

    # Build response message
    msg = f"Script written to {script_path}."
    if analysis.warnings:
        warning_count = len(analysis.warnings)
        msg += f" ({warning_count} warning{'s' if warning_count > 1 else ''} found)"
    msg += " Use test_wren_script() to validate it."

    return msg
