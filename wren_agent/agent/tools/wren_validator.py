"""
Wren API Validator - Dynamic validation using introspection and fuzzy matching.

This validator checks Wren SDK usage patterns by:
1. Introspecting actual SDK methods at import time
2. Using fuzzy matching (difflib) for typo suggestions
3. Checking Wren-specific patterns (integration location, etc.)

This approach mirrors Python 3.10+'s "Did you mean?" error suggestions.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from difflib import get_close_matches
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Set


@dataclass
class ValidationIssue:
    """A validation issue found in the code."""

    severity: str  # "CRITICAL", "HIGH", "MEDIUM", "LOW"
    error_code: str
    message: str
    fix_hint: str
    line: int
    col: int | None = None

    def to_dict(self) -> dict:
        result = {
            "severity": self.severity,
            "error_code": self.error_code,
            "message": self.message,
            "fix_hint": self.fix_hint,
            "location": {"line": self.line, "col": self.col},
        }
        return result


class WrenAPIValidator:
    """
    Validates Wren SDK usage using introspection and fuzzy matching.

    Discovers valid API methods at initialization and uses difflib
    to suggest corrections for typos.
    """

    # Known wren.ai methods (fallback if import fails)
    DEFAULT_AI_METHODS: Set[str] = {
        "extract",
        "classify",
        "sentiment",
        "summarize",
        "translate",
        "bool",
        "int",
        "float",
        "str",
        "date",
    }

    # Known integrations
    DEFAULT_INTEGRATIONS: Set[str] = {
        "gmail",
        "slack",
        "cron",
        "messaging",
    }

    def __init__(self) -> None:
        """Initialize validator, introspecting SDK if available."""
        self.valid_ai_methods = self._discover_ai_methods()
        self.valid_integrations = self._discover_integrations()

    def _discover_ai_methods(self) -> Set[str]:
        """Discover valid wren.ai methods via introspection."""
        try:
            import inspect

            import wren

            methods = set()
            for name, _ in inspect.getmembers(wren.ai):
                if not name.startswith("_"):
                    methods.add(name)
            return methods if methods else self.DEFAULT_AI_METHODS
        except ImportError:
            return self.DEFAULT_AI_METHODS

    def _discover_integrations(self) -> Set[str]:
        """Discover valid wren.integrations via SDK's list function."""
        try:
            from wren.integrations import list_integrations

            integrations = set(list_integrations())
            return integrations if integrations else self.DEFAULT_INTEGRATIONS
        except ImportError:
            return self.DEFAULT_INTEGRATIONS

    def validate(self, code: str) -> list[ValidationIssue]:
        """
        Validate code for Wren API issues.

        Args:
            code: Python source code to validate

        Returns:
            List of validation issues found
        """
        try:
            tree = ast.parse(code)
        except SyntaxError:
            # Syntax errors are handled by semgrep or wren test
            return []

        issues: list[ValidationIssue] = []

        # Run all checks
        issues.extend(self._check_ai_methods(tree))
        issues.extend(self._check_integration_names(tree))
        issues.extend(self._check_integration_location(tree))
        issues.extend(self._check_extract_type(tree))

        return issues

    def _check_ai_methods(self, tree: ast.AST) -> list[ValidationIssue]:
        """Check for unknown or misspelled wren.ai methods."""
        issues = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            # Check for wren.ai.METHOD pattern
            method = self._get_wren_ai_method(node)
            if method is None:
                continue

            if method not in self.valid_ai_methods:
                suggestions = get_close_matches(
                    method, list(self.valid_ai_methods), n=1, cutoff=0.6
                )
                if suggestions:
                    hint = f"Did you mean 'wren.ai.{suggestions[0]}'?"
                else:
                    hint = f"Valid methods: {', '.join(sorted(self.valid_ai_methods))}"

                issues.append(
                    ValidationIssue(
                        severity="MEDIUM",
                        error_code="UNKNOWN_AI_METHOD",
                        message=f"Unknown method 'wren.ai.{method}'",
                        fix_hint=hint,
                        line=node.lineno,
                        col=node.col_offset,
                    )
                )

        return issues

    def _check_integration_names(self, tree: ast.AST) -> list[ValidationIssue]:
        """Check for unknown or misspelled integration names."""
        issues = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.Attribute):
                continue

            # Check for wren.integrations.NAME pattern
            integration = self._get_integration_name(node)
            if integration is None:
                continue

            if integration not in self.valid_integrations:
                suggestions = get_close_matches(
                    integration, list(self.valid_integrations), n=1, cutoff=0.6
                )
                if suggestions:
                    hint = f"Did you mean 'wren.integrations.{suggestions[0]}'?"
                else:
                    hint = f"Valid integrations: {', '.join(sorted(self.valid_integrations))}"

                issues.append(
                    ValidationIssue(
                        severity="MEDIUM",
                        error_code="UNKNOWN_INTEGRATION",
                        message=f"Unknown integration 'wren.integrations.{integration}'",
                        fix_hint=hint,
                        line=node.lineno,
                        col=node.col_offset,
                    )
                )

        return issues

    def _check_integration_location(self, tree: ast.AST) -> list[ValidationIssue]:
        """Check that integrations are initialized at module level."""
        issues = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue

            # Search for integration.init() calls inside this function
            for child in ast.walk(node):
                if not isinstance(child, ast.Call):
                    continue

                if self._is_integration_init(child):
                    issues.append(
                        ValidationIssue(
                            severity="MEDIUM",
                            error_code="INTEGRATION_IN_FUNCTION",
                            message="Integration initialized inside function",
                            fix_hint="Move integration init() to module level (after imports, before functions).",
                            line=child.lineno,
                            col=child.col_offset,
                        )
                    )

        return issues

    def _check_extract_type(self, tree: ast.AST) -> list[ValidationIssue]:
        """Check that wren.ai.extract() has a type parameter."""
        issues = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            # Check if this is wren.ai.extract()
            method = self._get_wren_ai_method(node)
            if method != "extract":
                continue

            # Check if type is provided (2nd arg or target_type kwarg)
            has_type = len(node.args) >= 2 or any(
                kw.arg == "target_type" for kw in node.keywords
            )

            if not has_type:
                issues.append(
                    ValidationIssue(
                        severity="MEDIUM",
                        error_code="EXTRACT_MISSING_TYPE",
                        message="wren.ai.extract() called without type parameter",
                        fix_hint="Add type: wren.ai.extract(text, MyModel) or use type annotation.",
                        line=node.lineno,
                        col=node.col_offset,
                    )
                )

        return issues

    def _get_wren_ai_method(self, node: ast.Call) -> str | None:
        """Extract method name from wren.ai.METHOD() call."""
        # Pattern: wren.ai.METHOD(...)
        if not isinstance(node.func, ast.Attribute):
            return None

        attr = node.func  # .METHOD
        if not isinstance(attr.value, ast.Attribute):
            return None

        ai_attr = attr.value  # .ai
        if ai_attr.attr != "ai":
            return None

        if not isinstance(ai_attr.value, ast.Name):
            return None

        if ai_attr.value.id != "wren":
            return None

        return attr.attr

    def _get_integration_name(self, node: ast.Attribute) -> str | None:
        """Extract integration name from wren.integrations.NAME."""
        # Pattern: wren.integrations.NAME
        if not isinstance(node.value, ast.Attribute):
            return None

        integrations_attr = node.value
        if integrations_attr.attr != "integrations":
            return None

        if not isinstance(integrations_attr.value, ast.Name):
            return None

        if integrations_attr.value.id != "wren":
            return None

        return node.attr

    def _is_integration_init(self, node: ast.Call) -> bool:
        """Check if call is wren.integrations.NAME.init()."""
        if not isinstance(node.func, ast.Attribute):
            return False

        if node.func.attr != "init":
            return False

        # node.func.value should be wren.integrations.NAME
        if not isinstance(node.func.value, ast.Attribute):
            return False

        return self._get_integration_name(node.func.value) is not None
