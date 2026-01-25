"""
Integration tests for the Wren Agent.

These tests make real API calls to OpenAI and require OPENAI_API_KEY.

Run with:
    uv run python -m tests.integration.test_agent           # All tests
    uv run python -m tests.integration.test_agent -t simple_schedule  # Single test
    uv run python -m tests.integration.test_agent --list    # List tests
"""

import asyncio

from agent import run_agent

# Test cases: (name, request, expected_features)
TEST_CASES = [
    (
        "simple_schedule",
        "Create a script that prints hello world on a 9 AM schedule",
        {"has_schedule": True, "has_integration": False},
    ),
    (
        "gmail_notification",
        "Create a script that uses gmail to send a notification when an email arrives",
        {"has_schedule": False, "has_integration": True, "integration": "gmail"},
    ),
    (
        "email_classification",
        "Classify incoming emails as urgent or normal and post urgent ones to Slack",
        {"has_schedule": False, "has_integration": True, "uses_ai": True},
    ),
    (
        "daily_summary",
        "Every day at 6 PM, summarize all emails received that day and post to Slack",
        {"has_schedule": True, "has_integration": True},
    ),
    (
        "extract_invoice",
        "When an email with subject containing 'Invoice' arrives, extract the amount and sender",
        {"has_schedule": False, "has_integration": False, "uses_ai": True},
    ),
]


async def run_test(name: str, request: str, expected: dict) -> dict:
    """Run a single test case."""
    print(f"\n{'=' * 60}")
    print(f"TEST: {name}")
    print(f"{'=' * 60}")
    print(f"Request: {request}")
    print()

    result = await run_agent(
        request,
        workspace=f"./scripts/{name}",
        verbose=False,
    )

    passed = result["success"]

    # Check expected features if test passed
    if passed and result.get("final_result"):
        metadata = result["final_result"].get("metadata", {})

        if expected.get("has_schedule"):
            if not metadata.get("schedules"):
                print("  [WARN] Expected schedule trigger but none found")

        if expected.get("has_integration"):
            if not metadata.get("integrations"):
                print("  [WARN] Expected integration but none found")
            elif expected.get("integration"):
                if expected["integration"] not in metadata["integrations"]:
                    print(f"  [WARN] Expected {expected['integration']} integration")

    status = "PASS" if passed else "FAIL"
    print(f"\nResult: [{status}]")
    print(f"Script: {result.get('script_path')}")
    print(f"Iterations: {result.get('iterations')}")

    if not passed and result.get("final_result"):
        print(f"Error: {result['final_result'].get('message')}")
        print(f"Hint: {result['final_result'].get('fix_hint')}")

    return {"name": name, "passed": passed, "result": result}


async def run_all_tests():
    """Run all test cases."""
    print("=" * 60)
    print("WREN AGENT TEST SUITE")
    print("=" * 60)

    results = []
    for name, request, expected in TEST_CASES:
        try:
            result = await run_test(name, request, expected)
            results.append(result)
        except Exception as e:
            print(f"\n[ERROR] Test {name} threw exception: {e}")
            results.append({"name": name, "passed": False, "error": str(e)})

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    passed = sum(1 for r in results if r["passed"])
    total = len(results)

    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"  [{status}] {r['name']}")

    print(f"\nTotal: {passed}/{total} passed")

    return results


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Run Wren Agent test suite")
    parser.add_argument("--test", "-t", help="Run specific test by name")
    parser.add_argument("--list", "-l", action="store_true", help="List available tests")
    args = parser.parse_args()

    if args.list:
        print("Available tests:")
        for name, request, _ in TEST_CASES:
            print(f"  {name}: {request[:50]}...")
        return

    if args.test:
        # Run specific test
        for name, request, expected in TEST_CASES:
            if name == args.test:
                asyncio.run(run_test(name, request, expected))
                return
        print(f"Test '{args.test}' not found")
        return

    # Run all tests
    asyncio.run(run_all_tests())


if __name__ == "__main__":
    main()
