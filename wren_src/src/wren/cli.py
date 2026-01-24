"""
Wren CLI - Command line interface for wren SDK.

Usage:
    wren test <script.py>      Import a script to check for errors
    wren validate <script.py>  Extract metadata and validate integrations
    wren deploy <script.py>    Deploy script and metadata to platform
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import wren

from .errors.classifier import format_error_for_agent
from .core.runtime import import_script


def _load_script_metadata(script_path: str) -> dict[str, Any]:
    """
    Import a user script and extract metadata.

    Returns a dict with:
    - valid: bool
    - error: str (if invalid)
    - error_type: AgentFixableError | UserFacingConfigError (if invalid)
    - error_code: machine-readable code (if invalid)
    - fix_hint: actionable suggestion (if invalid)
    - location: {file, line, col} (if available)
    - metadata: dict (if valid)
    - functions: list[str] (if valid)
    - duration_ms: int (always)
    """
    start_time = time.time()

    try:
        import_script(script_path)
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        error_info = format_error_for_agent(e)
        return {
            "valid": False,
            "error": error_info.get("message", str(e)),
            "duration_ms": duration_ms,
            **error_info,
        }

    duration_ms = int((time.time() - start_time) * 1000)
    metadata = wren.get_metadata()
    functions = wren.registry.get_functions()

    return {
        "valid": True,
        "metadata": metadata,
        "functions": list(functions.keys()),
        "duration_ms": duration_ms,
    }


def _get_platform_config() -> tuple[str | None, str | None]:
    config = wren.get_config()
    return config.platform_url, config.platform_api_key


def _parse_response(body: str) -> Any:
    if not body:
        return None
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return body


def _platform_post_json(
    url: str,
    payload: dict[str, Any],
    api_key: str | None,
    *,
    timeout: int = 10,
) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    request = Request(url, data=data, headers=headers, method="POST")
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            return {"ok": True, "status": response.status, "data": _parse_response(body)}
    except HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        return {"ok": False, "status": e.code, "error": body or str(e)}
    except URLError as e:
        return {"ok": False, "error": str(e.reason)}


def _platform_validate_integrations(
    integrations: list[str],
    platform_url: str | None,
    api_key: str | None,
) -> dict[str, Any]:
    if not integrations:
        return {"ok": True, "skipped": True, "reason": "No integrations declared."}
    if not platform_url:
        return {
            "ok": False,
            "error": "Platform URL not configured. Set WREN_PLATFORM_URL.",
        }
    if not api_key:
        return {
            "ok": False,
            "error": "Platform API key not configured. Set WREN_PLATFORM_API_KEY.",
        }

    url = f"{platform_url.rstrip('/')}/v1/integrations/validate"
    return _platform_post_json(url, {"integrations": integrations}, api_key)


def _platform_deploy_script(
    script_path: str,
    metadata: dict[str, Any],
    platform_url: str | None,
    api_key: str | None,
) -> dict[str, Any]:
    if not platform_url:
        return {
            "ok": False,
            "error": "Platform URL not configured. Set WREN_PLATFORM_URL.",
        }
    if not api_key:
        return {
            "ok": False,
            "error": "Platform API key not configured. Set WREN_PLATFORM_API_KEY.",
        }

    script = Path(script_path).read_text(encoding="utf-8")
    url = f"{platform_url.rstrip('/')}/v1/scripts/deploy"
    payload = {"script": script, "metadata": metadata}
    return _platform_post_json(url, payload, api_key)


def test_script(script_path: str) -> dict[str, Any]:
    """Import a user script and extract metadata without platform calls."""
    return _load_script_metadata(script_path)


def validate_script(script_path: str) -> dict[str, Any]:
    """
    Import a user script, extract metadata, and validate integrations.
    """
    result = _load_script_metadata(script_path)
    if not result["valid"]:
        return result

    metadata = result["metadata"]
    integrations = metadata.get("integrations", [])
    platform_url, api_key = _get_platform_config()
    platform = _platform_validate_integrations(integrations, platform_url, api_key)
    result["platform"] = platform

    if not platform.get("ok", False):
        result["valid"] = False
        result["error"] = platform.get("error", "Platform validation failed.")
        return result

    data = platform.get("data")
    if isinstance(data, dict) and data.get("valid") is False:
        result["valid"] = False
        errors = data.get("errors", [])
        if errors:
            first_error = errors[0]
            if isinstance(first_error, dict) and first_error.get("message"):
                result["error"] = first_error["message"]
            else:
                result["error"] = "Platform validation failed."
        else:
            result["error"] = "Platform validation failed."

    return result


def deploy_script(script_path: str) -> dict[str, Any]:
    """
    Import a user script, extract metadata, and deploy to the platform.
    """
    result = _load_script_metadata(script_path)
    if not result["valid"]:
        return result

    platform_url, api_key = _get_platform_config()
    platform = _platform_deploy_script(script_path, result["metadata"], platform_url, api_key)
    result["platform"] = platform

    if not platform.get("ok", False):
        result["valid"] = False
        result["error"] = platform.get("error", "Deployment failed.")
    else:
        data = platform.get("data")
        if isinstance(data, dict) and "deployment_id" in data:
            result["deployment_id"] = data["deployment_id"]

    return result


def print_test_result(result: dict[str, Any], script_path: str) -> None:
    """Pretty print test results."""
    if not result["valid"]:
        print(f"\n\u2717 Test failed: {script_path}")
        print(f"  Error: {result['error']}")

        # Show enhanced error info if available
        if result.get("error_code"):
            print(f"  Code: {result['error_code']}")
        if result.get("fix_hint"):
            print(f"  Fix: {result['fix_hint']}")
        if result.get("location"):
            loc = result["location"]
            loc_str = f"{loc['file']}:{loc['line']}"
            if loc.get("col"):
                loc_str += f":{loc['col']}"
            print(f"  Location: {loc_str}")
        return

    print(f"\n\u2713 Script imported: {script_path}")
    if result.get("duration_ms"):
        print(f"  Duration: {result['duration_ms']}ms")


def print_validation_result(result: dict[str, Any], script_path: str) -> None:
    """Pretty print validation results."""
    if not result["valid"]:
        print(f"\n\u2717 Validation failed: {script_path}")
        print(f"  Error: {result['error']}")
        return

    metadata = result["metadata"]

    print(f"\n\u2713 Script validated: {script_path}")
    print()

    # Integrations
    integrations = metadata.get("integrations", [])
    if integrations:
        print(f"Integrations ({len(integrations)}):")
        for name in integrations:
            print(f"  \u2022 {name}")
    else:
        print("Integrations: none")
    print()

    # Group triggers by type
    triggers = metadata.get("triggers", [])
    triggers_by_type: dict[str, list] = {}
    for t in triggers:
        trigger_type = t["type"]
        if trigger_type not in triggers_by_type:
            triggers_by_type[trigger_type] = []
        triggers_by_type[trigger_type].append(t)

    # Schedules
    schedules = triggers_by_type.get("schedule", [])
    if schedules:
        print(f"Schedules ({len(schedules)}):")
        for s in schedules:
            config = s["config"]
            tz = f"  ({config['timezone']})" if config.get("timezone") else ""
            print(f"  \u2022 {s['func']:<20} \"{config['cron']}\"{tz}")
    else:
        print("Schedules: none")
    print()

    # Email triggers
    email_triggers = triggers_by_type.get("email", [])
    if email_triggers:
        print(f"Email Triggers ({len(email_triggers)}):")
        for t in email_triggers:
            filter_config = t["config"].get("filter", {})
            filter_str = filter_config if filter_config else "all emails"
            print(f"  \u2022 {t['func']:<20} {filter_str}")
    else:
        print("Email Triggers: none")
    print()

    # Other trigger types
    other_types = [t for t in triggers_by_type.keys() if t not in ("schedule", "email")]
    for trigger_type in other_types:
        type_triggers = triggers_by_type[trigger_type]
        print(f"{trigger_type.title()} Triggers ({len(type_triggers)}):")
        for t in type_triggers:
            print(f"  \u2022 {t['func']:<20} {t['config']}")
        print()

    # Functions
    functions = result.get("functions", [])
    print(f"Registered functions: {len(functions)}")
    if functions:
        print(f"  {', '.join(functions)}")

    platform = result.get("platform")
    if platform and platform.get("skipped"):
        print(f"\nPlatform validation: skipped ({platform.get('reason')})")
    elif platform:
        if not platform.get("ok", False):
            print(f"\nPlatform validation: failed ({platform.get('error', 'unknown error')})")
            return
        data = platform.get("data")
        if isinstance(data, dict) and data.get("valid") is False:
            print("\nPlatform validation: failed")
            errors = data.get("errors", [])
            if errors:
                print("Errors:")
                for error in errors:
                    if isinstance(error, dict) and error.get("message"):
                        message = error["message"]
                    else:
                        message = str(error)
                    print(f"  \u2022 {message}")
            warnings = data.get("warnings", [])
            if warnings:
                print("Warnings:")
                for warning in warnings:
                    print(f"  \u2022 {warning}")
        else:
            print("\nPlatform validation: ok")


def print_deploy_result(result: dict[str, Any], script_path: str) -> None:
    """Pretty print deploy results."""
    if not result["valid"]:
        print(f"\n\u2717 Deployment failed: {script_path}")
        print(f"  Error: {result['error']}")
        return

    print(f"\n\u2713 Script deployed: {script_path}")
    deployment_id = result.get("deployment_id")
    if deployment_id:
        print(f"Deployment ID: {deployment_id}")


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="wren",
        description="Wren SDK command line interface",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # test command
    test_parser = subparsers.add_parser(
        "test",
        help="Import a script to check for errors",
    )
    test_parser.add_argument(
        "script",
        help="Path to the Python script to test",
    )
    test_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON instead of formatted text",
    )

    # validate command
    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate a script and extract its metadata",
    )
    validate_parser.add_argument(
        "script",
        help="Path to the Python script to validate",
    )
    validate_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON instead of formatted text",
    )

    # deploy command
    deploy_parser = subparsers.add_parser(
        "deploy",
        help="Deploy a script and its metadata to the platform",
    )
    deploy_parser.add_argument(
        "script",
        help="Path to the Python script to deploy",
    )
    deploy_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON instead of formatted text",
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 1

    if args.command == "test":
        result = test_script(args.script)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print_test_result(result, args.script)
        return 0 if result["valid"] else 1

    if args.command == "validate":
        result = validate_script(args.script)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print_validation_result(result, args.script)
        return 0 if result["valid"] else 1

    if args.command == "deploy":
        result = deploy_script(args.script)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print_deploy_result(result, args.script)
        return 0 if result["valid"] else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
