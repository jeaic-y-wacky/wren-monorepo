"""
Batch Security Test - Run semgrep once on all dangerous patterns.

This is much faster than per-pattern tests since semgrep only starts once.
Run with: uv run pytest tests/unit/test_security_batch.py -v
"""

import json
import subprocess
import tempfile
from pathlib import Path

import pytest

RULES_PATH = Path(__file__).parent.parent.parent / "agent" / "tools" / "semgrep_rules.yaml"


# All dangerous code patterns we expect to be blocked
# Format: (code_snippet, expected_rule_id)
DANGEROUS_PATTERNS = [
    # === block-dangerous-imports ===
    ("import os", "block-dangerous-imports"),
    ("import subprocess", "block-dangerous-imports"),
    ("import commands", "block-dangerous-imports"),
    ("import pty", "block-dangerous-imports"),
    ("import fcntl", "block-dangerous-imports"),
    ("import socket", "block-dangerous-imports"),
    ("import socketserver", "block-dangerous-imports"),
    ("import requests", "block-dangerous-imports"),
    ("import urllib", "block-dangerous-imports"),
    ("import urllib3", "block-dangerous-imports"),
    ("import httplib", "block-dangerous-imports"),
    ("import http.client", "block-dangerous-imports"),
    ("import ftplib", "block-dangerous-imports"),
    ("import smtplib", "block-dangerous-imports"),
    ("import poplib", "block-dangerous-imports"),
    ("import imaplib", "block-dangerous-imports"),
    ("import telnetlib", "block-dangerous-imports"),
    ("import ctypes", "block-dangerous-imports"),
    ("import cffi", "block-dangerous-imports"),
    ("import pickle", "block-dangerous-imports"),
    ("import cPickle", "block-dangerous-imports"),
    ("import shelve", "block-dangerous-imports"),
    ("import marshal", "block-dangerous-imports"),
    ("import shutil", "block-dangerous-imports"),
    ("import tempfile", "block-dangerous-imports"),
    ("import glob", "block-dangerous-imports"),
    ("import multiprocessing", "block-dangerous-imports"),
    ("import threading", "block-dangerous-imports"),
    ("import concurrent", "block-dangerous-imports"),
    ("import platform", "block-dangerous-imports"),
    ("import getpass", "block-dangerous-imports"),
    ("import pwd", "block-dangerous-imports"),
    ("import grp", "block-dangerous-imports"),

    # === block-dangerous-from-imports ===
    ("from os import system", "block-dangerous-from-imports"),
    ("from os import path", "block-dangerous-from-imports"),
    ("from subprocess import run", "block-dangerous-from-imports"),
    ("from subprocess import Popen", "block-dangerous-from-imports"),
    ("from socket import socket", "block-dangerous-from-imports"),
    ("from ctypes import CDLL", "block-dangerous-from-imports"),
    ("from pickle import loads", "block-dangerous-from-imports"),
    ("from shutil import rmtree", "block-dangerous-from-imports"),
    ("from multiprocessing import Process", "block-dangerous-from-imports"),
    ("from threading import Thread", "block-dangerous-from-imports"),

    # === block-eval-exec ===
    ('eval("1 + 1")', "block-eval-exec"),
    ("eval(user_input)", "block-eval-exec"),
    ('exec("print(1)")', "block-eval-exec"),
    ("exec(code_string)", "block-eval-exec"),
    ('compile("x", "file", "exec")', "block-eval-exec"),
    ('__import__("os")', "block-eval-exec"),

    # === block-file-write ===
    ('open("file.txt", "w")', "block-file-write"),
    ('open("file.txt", "a")', "block-file-write"),
    ('open("file.txt", "x")', "block-file-write"),
    ('open("file.txt", "wb")', "block-file-write"),
    ('open("file.txt", "ab")', "block-file-write"),
    ('open(path, mode="w")', "block-file-write"),
    ('open(path, mode="a")', "block-file-write"),

    # === block-dangerous-builtins ===
    ("globals()", "block-dangerous-builtins"),
    ("locals()", "block-dangerous-builtins"),
    ("vars()", "block-dangerous-builtins"),
    ("vars(obj)", "block-dangerous-builtins"),
    ('setattr(obj, "attr", value)', "block-dangerous-builtins"),
    ('delattr(obj, "attr")', "block-dangerous-builtins"),
    ("breakpoint()", "block-dangerous-builtins"),
]

# Code that should NOT be blocked
SAFE_PATTERNS = [
    "import json",
    "import re",
    "import datetime",
    "import collections",
    "import functools",
    "import math",
    "import typing",
    "import wren",
    "from pydantic import BaseModel",
    'print("hello")',
    "len([1, 2, 3])",
    "str(123)",
    'open("file.txt", "r")',
    'open("file.txt")',  # default is read
    "# import os",  # commented out
    '"""import os"""',  # in docstring
]


class TestSecurityBatch:
    """Batch security tests - run semgrep once."""

    @pytest.fixture(scope="class")
    def semgrep_results(self):
        """Run semgrep once on all dangerous patterns, return findings."""
        # Build a single file with all patterns, each on its own line
        # We use markers to track which line has which pattern
        lines = []
        line_to_pattern = {}

        for i, (code, rule_id) in enumerate(DANGEROUS_PATTERNS):
            # Each pattern gets its own line(s)
            code_lines = code.strip().split('\n')
            start_line = len(lines) + 1
            lines.extend(code_lines)
            # Map each line of this pattern
            for offset in range(len(code_lines)):
                line_to_pattern[start_line + offset] = (code, rule_id)

        combined_code = '\n'.join(lines)

        # Write to temp file and run semgrep
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(combined_code)
            temp_path = f.name

        try:
            result = subprocess.run(
                [
                    "semgrep", "scan",
                    "--config", str(RULES_PATH),
                    "--json",
                    "--quiet",
                    temp_path,
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.stdout:
                data = json.loads(result.stdout)
                findings = data.get("results", [])
            else:
                findings = []

            return {
                "findings": findings,
                "line_to_pattern": line_to_pattern,
                "code": combined_code,
            }
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_all_dangerous_patterns_detected(self, semgrep_results):
        """Verify every dangerous pattern triggers the expected rule."""
        findings = semgrep_results["findings"]
        line_to_pattern = semgrep_results["line_to_pattern"]

        # Build map of line -> list of rule_ids from findings
        found_by_line = {}
        for f in findings:
            line = f.get("start", {}).get("line", 0)
            rule_id = f.get("check_id", "")
            if line not in found_by_line:
                found_by_line[line] = []
            found_by_line[line].append(rule_id)

        # Check each pattern was found (semgrep prefixes rules with path)
        missing = []
        for line, (code, expected_rule) in line_to_pattern.items():
            matched_rules = found_by_line.get(line, [])
            # Check if any matched rule ends with expected rule (handles prefix)
            if not any(r.endswith(expected_rule) for r in matched_rules):
                if not matched_rules:
                    missing.append(f"Line {line}: {code!r} - expected {expected_rule}, got nothing")
                else:
                    missing.append(f"Line {line}: {code!r} - expected {expected_rule}, got {matched_rules}")

        if missing:
            pytest.fail(f"Missing detections:\n" + "\n".join(missing))

    def test_finding_count(self, semgrep_results):
        """Verify we get the expected number of findings."""
        findings = semgrep_results["findings"]
        expected = len(DANGEROUS_PATTERNS)
        actual = len(findings)

        # Allow some variance due to multi-line patterns
        assert actual >= expected * 0.9, f"Expected ~{expected} findings, got {actual}"

        print(f"\n✓ Security coverage: {actual} findings from {expected} patterns")

    def test_no_false_positives_on_safe_code(self):
        """Verify safe code doesn't trigger security rules."""
        combined_code = '\n'.join(SAFE_PATTERNS)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(combined_code)
            temp_path = f.name

        try:
            result = subprocess.run(
                [
                    "semgrep", "scan",
                    "--config", str(RULES_PATH),
                    "--json",
                    "--quiet",
                    temp_path,
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.stdout:
                data = json.loads(result.stdout)
                findings = data.get("results", [])
            else:
                findings = []

            if findings:
                false_positives = [
                    f"Line {f['start']['line']}: {f['check_id']}"
                    for f in findings
                ]
                pytest.fail(f"False positives on safe code:\n" + "\n".join(false_positives))

            print(f"\n✓ No false positives on {len(SAFE_PATTERNS)} safe patterns")

        finally:
            Path(temp_path).unlink(missing_ok=True)


class TestSecurityCoverage:
    """Coverage metrics for security rules."""

    def test_rule_coverage_summary(self):
        """Print coverage summary for all rules."""
        rule_counts = {}
        for _, rule_id in DANGEROUS_PATTERNS:
            rule_counts[rule_id] = rule_counts.get(rule_id, 0) + 1

        print("\n=== Security Rule Coverage ===")
        for rule_id, count in sorted(rule_counts.items()):
            print(f"  {rule_id}: {count} patterns")
        print(f"  TOTAL: {len(DANGEROUS_PATTERNS)} dangerous patterns")
        print(f"  SAFE: {len(SAFE_PATTERNS)} safe patterns (no false positives)")
