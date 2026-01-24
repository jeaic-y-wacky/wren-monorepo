"""
Wren Agent CLI - Entry point for running the agent.
"""

import argparse
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Load .env from project root (one level up from agent/)
_project_dir = Path(__file__).parent.parent
_env_file = _project_dir / ".env"
if _env_file.exists():
    load_dotenv(_env_file)
else:
    load_dotenv()  # Try current directory

from agents import Runner

from .core import create_agent
from .context import AgentContext


def _run_wren_test(script_path: Path) -> dict[str, Any]:
    """Run wren test on a script and return the result."""
    wren_src_dir = Path(__file__).parent.parent.parent / "wren_src"

    try:
        result = subprocess.run(
            ["uv", "run", "wren", "test", str(script_path.resolve()), "--json"],
            cwd=str(wren_src_dir),
            capture_output=True,
            text=True,
            timeout=30,
        )
        return json.loads(result.stdout)
    except Exception as e:
        return {"valid": False, "error_type": "TestError", "message": str(e)}


async def run_agent(
    user_request: str,
    workspace: str | None = None,
    max_iterations: int = 5,
    model: str = "gpt-4o",
    verbose: bool = False,
) -> dict[str, Any]:
    """Run the Wren Agent to fulfill a user request.

    Args:
        user_request: What the user wants the script to do
        workspace: Directory for generated scripts
        max_iterations: Maximum fix iterations before giving up
        model: LLM model to use
        verbose: Print verbose output

    Returns:
        Dict with script_path, success status, and final test results
    """
    # Create context
    context = AgentContext(
        user_request=user_request,
        max_iterations=max_iterations,
    )
    if workspace:
        context.workspace_dir = Path(workspace)

    # Create agent
    agent = create_agent(model=model)

    # Build the initial prompt with workflow instructions
    initial_prompt = f"""User Request: {user_request}

Please follow this workflow:
1. Analyze the request and determine the appropriate Wren SDK patterns
2. Write the initial script using write_wren_script
3. Test it using test_wren_script
4. If there are errors and error_type is "AgentFixableError":
   - Read the fix_hint carefully
   - Rewrite the script to fix the issue
   - Test again
5. Repeat until the script passes or you've tried {max_iterations} times
6. Report the final status

Start by writing the initial script."""

    if verbose:
        print(f"[WrenAgent] Starting with request: {user_request}")
        print(f"[WrenAgent] Workspace: {workspace}")
        print(f"[WrenAgent] Model: {model}")

    # Run the agent
    result = await Runner.run(
        agent,
        initial_prompt,
        context=context,
        max_turns=20,  # Allow multiple tool calls for iterate loop
    )

    if verbose:
        print(f"[WrenAgent] Completed in {context.iteration_count} iterations")

    # Fallback: If agent wrote a script but didn't test it, run test now
    if context.script_path and context.last_test_result is None:
        if verbose:
            print("[WrenAgent] Agent didn't test script, running validation now...")
        context.last_test_result = _run_wren_test(context.script_path)

    return {
        "success": context.is_valid(),
        "script_path": str(context.script_path) if context.script_path else None,
        "iterations": context.iteration_count,
        "final_result": context.last_test_result,
        "agent_output": result.final_output,
    }


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Wren Agent - AI-powered Wren SDK script generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  wren-agent "Process incoming emails and classify them as urgent or normal"
  wren-agent "Send a Slack notification every day at 9 AM" --workspace ./my_scripts
  wren-agent "Extract invoice data from emails" --model gpt-4o-mini --verbose
        """,
    )
    parser.add_argument(
        "request",
        help="What you want the script to do",
    )
    parser.add_argument(
        "--workspace",
        default=None,
        help="Output directory for generated scripts (default: wren_agent/scripts/)",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=5,
        help="Maximum fix iterations (default: 5)",
    )
    parser.add_argument(
        "--model",
        default="gpt-4o",
        help="LLM model to use (default: gpt-4o)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print verbose output",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output result as JSON",
    )

    args = parser.parse_args()

    try:
        result = asyncio.run(
            run_agent(
                args.request,
                workspace=args.workspace,
                max_iterations=args.max_iterations,
                model=args.model,
                verbose=args.verbose,
            )
        )

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if result["success"]:
                print(f"\n[SUCCESS] Script created: {result['script_path']}")
                print(f"Iterations: {result['iterations']}")
                if result.get("agent_output"):
                    print(f"\nAgent response:\n{result['agent_output']}")
            else:
                print(f"\n[FAILED] Could not create valid script after {result['iterations']} iterations")
                if result.get("final_result"):
                    print(f"Last error: {result['final_result'].get('message', 'Unknown error')}")
                    if result["final_result"].get("fix_hint"):
                        print(f"Hint: {result['final_result']['fix_hint']}")
                sys.exit(1)

    except KeyboardInterrupt:
        print("\n[CANCELLED] Agent interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
