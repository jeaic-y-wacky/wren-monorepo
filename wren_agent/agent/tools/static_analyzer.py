"""
Static Analyzer - Two-layer validation for Wren scripts.

Layer 1: Semgrep (Security)
  - Blocks dangerous imports, eval/exec, file writes
  - Battle-tested pattern matching

Layer 2: Wren API Validator (Correctness)
  - Introspects actual SDK methods
  - Fuzzy matching for typo suggestions
  - Checks Wren-specific patterns

See docs/static_analysis.md for detailed documentation.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from .wren_validator import ValidationIssue, WrenAPIValidator

Severity = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]


@dataclass
class AnalysisResult:
    """Result of static analysis."""

    valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def blocking_issues(self) -> list[ValidationIssue]:
        """Issues that block the write (CRITICAL/HIGH)."""
        return [i for i in self.issues if i.severity in ("CRITICAL", "HIGH")]

    @property
    def warnings(self) -> list[ValidationIssue]:
        """Issues that warn but allow write (MEDIUM/LOW)."""
        return [i for i in self.issues if i.severity in ("MEDIUM", "LOW")]

    def to_dict(self) -> dict:
        """Format for agent consumption, matching test_wren_script format."""
        if not self.valid:
            first = self.blocking_issues[0] if self.blocking_issues else self.issues[0]
            result = {
                "valid": False,
                "error_type": "SecurityError"
                if first.severity == "CRITICAL"
                else "AgentFixableError",
                "error_code": first.error_code,
                "message": first.message,
                "fix_hint": first.fix_hint,
                "location": {"line": first.line, "col": first.col},
            }
            if len(self.issues) > 1:
                result["all_issues"] = [i.to_dict() for i in self.issues]
            return result

        result = {"valid": True}
        if self.warnings:
            result["warnings"] = [w.to_dict() for w in self.warnings]
        return result


class StaticAnalyzer:
    """
    Two-layer static analyzer for Wren scripts.

    Combines Semgrep (security) and WrenAPIValidator (correctness)
    to validate scripts before writing to disk.
    """

    def __init__(self) -> None:
        self.rules_path = Path(__file__).parent / "semgrep_rules.yaml"
        self.wren_validator = WrenAPIValidator()
        self._semgrep_available: bool | None = None

    def analyze(self, code: str) -> AnalysisResult:
        """
        Analyze code for security and correctness issues.

        Args:
            code: Python source code to analyze

        Returns:
            AnalysisResult with valid=False if blocking issues found
        """
        all_issues: list[ValidationIssue] = []

        # Layer 1: Security (Semgrep)
        security_issues = self._run_semgrep(code)
        all_issues.extend(security_issues)

        # If critical security issues, stop early
        if any(i.severity == "CRITICAL" for i in security_issues):
            return AnalysisResult(valid=False, issues=all_issues)

        # Layer 2: Wren API validation
        wren_issues = self.wren_validator.validate(code)
        all_issues.extend(wren_issues)

        # Determine validity: CRITICAL/HIGH block, MEDIUM/LOW warn
        has_blocking = any(i.severity in ("CRITICAL", "HIGH") for i in all_issues)

        return AnalysisResult(valid=not has_blocking, issues=all_issues)

    def _run_semgrep(self, code: str) -> list[ValidationIssue]:
        """Run Semgrep security scan on code."""
        # Check if semgrep is available
        if not self._is_semgrep_available():
            return []

        # Write code to temp file for semgrep
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
            tmp.write(code)
            tmp_path = tmp.name

        try:
            result = subprocess.run(
                [
                    "semgrep",
                    "scan",
                    "--config",
                    str(self.rules_path),
                    "--json",
                    "--quiet",
                    tmp_path,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            return self._parse_semgrep_output(result.stdout)

        except subprocess.TimeoutExpired:
            return [
                ValidationIssue(
                    severity="HIGH",
                    error_code="SEMGREP_TIMEOUT",
                    message="Security scan timed out",
                    fix_hint="Simplify the code or try again.",
                    line=1,
                )
            ]
        except FileNotFoundError:
            # Semgrep not installed
            self._semgrep_available = False
            return []
        finally:
            # Clean up temp file
            Path(tmp_path).unlink(missing_ok=True)

    def _is_semgrep_available(self) -> bool:
        """Check if semgrep CLI is available."""
        if self._semgrep_available is not None:
            return self._semgrep_available

        try:
            subprocess.run(
                ["semgrep", "--version"],
                capture_output=True,
                timeout=5,
            )
            self._semgrep_available = True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            self._semgrep_available = False

        return self._semgrep_available

    def _parse_semgrep_output(self, output: str) -> list[ValidationIssue]:
        """Parse Semgrep JSON output into ValidationIssues."""
        if not output:
            return []

        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            return []

        issues = []
        for finding in data.get("results", []):
            # Map semgrep severity to our severity
            severity = finding.get("extra", {}).get("severity", "HIGH").upper()
            if severity not in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
                severity = "HIGH"

            issues.append(
                ValidationIssue(
                    severity=severity,
                    error_code=finding.get("check_id", "UNKNOWN"),
                    message=finding.get("extra", {}).get("message", "Security issue detected"),
                    fix_hint="Remove or replace the flagged code.",
                    line=finding.get("start", {}).get("line", 1),
                    col=finding.get("start", {}).get("col", 0),
                )
            )

        return issues


# Global analyzer instance (stateless, reusable)
_analyzer: StaticAnalyzer | None = None


def get_analyzer() -> StaticAnalyzer:
    """Get or create the global analyzer instance."""
    global _analyzer
    if _analyzer is None:
        _analyzer = StaticAnalyzer()
    return _analyzer
