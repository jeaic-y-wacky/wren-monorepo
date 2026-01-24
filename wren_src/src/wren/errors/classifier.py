"""
Error classification for agent-friendly feedback.

Classifies exceptions into actionable categories with fix hints,
following the AgentFixableError / UserFacingConfigError taxonomy.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

ErrorType = Literal["AgentFixableError", "UserFacingConfigError", "InternalError"]


@dataclass
class ErrorLocation:
    """Location of an error in source code."""

    file: str
    line: int
    col: int | None = None

    def to_dict(self) -> dict:
        d = {"file": self.file, "line": self.line}
        if self.col is not None:
            d["col"] = self.col
        return d


@dataclass
class ClassifiedError:
    """A classified error with actionable information for agents."""

    error_type: ErrorType
    error_code: str
    message: str
    fix_hint: str | None = None
    location: ErrorLocation | None = None
    original_error: str | None = None

    def to_dict(self) -> dict:
        d = {
            "error_type": self.error_type,
            "error_code": self.error_code,
            "message": self.message,
        }
        if self.fix_hint:
            d["fix_hint"] = self.fix_hint
        if self.location:
            d["location"] = self.location.to_dict()
        if self.original_error:
            d["original_error"] = self.original_error
        return d


def extract_name_from_nameerror(msg: str) -> str | None:
    """Extract the undefined name from a NameError message."""
    # "name 'foo' is not defined"
    match = re.search(r"name '([^']+)' is not defined", msg)
    return match.group(1) if match else None


def extract_module_from_importerror(msg: str) -> str | None:
    """Extract module name from ImportError message."""
    # "No module named 'foo'"
    match = re.search(r"No module named '([^']+)'", msg)
    if match:
        return match.group(1)
    # "cannot import name 'bar' from 'foo'"
    match = re.search(r"cannot import name '([^']+)' from '([^']+)'", msg)
    if match:
        return f"{match.group(2)}.{match.group(1)}"
    return None


def extract_location_from_tb(exc: Exception) -> ErrorLocation | None:
    """Extract error location from exception traceback."""
    tb = exc.__traceback__
    if tb is None:
        return None

    # Walk to the last frame (where the error occurred)
    while tb.tb_next is not None:
        tb = tb.tb_next

    return ErrorLocation(
        file=tb.tb_frame.f_code.co_filename,
        line=tb.tb_lineno,
    )


def classify_syntax_error(exc: SyntaxError) -> ClassifiedError:
    """Classify a SyntaxError."""
    location = None
    if exc.filename and exc.lineno:
        location = ErrorLocation(
            file=exc.filename,
            line=exc.lineno,
            col=exc.offset,
        )

    # Provide specific hints for common syntax errors
    msg = str(exc.msg) if exc.msg else str(exc)
    fix_hint = "Fix the syntax error in the code."

    if "invalid syntax" in msg.lower():
        fix_hint = "Check for missing colons, brackets, or incorrect indentation."
    elif "unexpected indent" in msg.lower():
        fix_hint = "Remove extra indentation or align with the previous line."
    elif "expected an indented block" in msg.lower():
        fix_hint = "Add an indented block after the colon (e.g., 'pass' or actual code)."
    elif "unterminated string" in msg.lower():
        fix_hint = "Close the string with a matching quote."
    elif "unmatched" in msg.lower():
        fix_hint = "Check for matching parentheses, brackets, or braces."

    return ClassifiedError(
        error_type="AgentFixableError",
        error_code="SYNTAX_ERROR",
        message=msg,
        fix_hint=fix_hint,
        location=location,
        original_error=f"SyntaxError: {msg}",
    )


def classify_name_error(exc: NameError) -> ClassifiedError:
    """Classify a NameError."""
    msg = str(exc)
    name = extract_name_from_nameerror(msg)
    location = extract_location_from_tb(exc)

    fix_hint = "Check spelling or add the missing import."
    if name:
        # Check for common Wren patterns
        if name in ("gmail", "slack", "calendar", "sheets"):
            fix_hint = f"Add 'from wren.integrations import {name}' and call '{name}.init()' at module level."
        elif name == "wren":
            fix_hint = "Add 'import wren' at the top of the file."
        else:
            fix_hint = f"'{name}' is not defined. Check spelling or add the missing import."

    return ClassifiedError(
        error_type="AgentFixableError",
        error_code="NAME_ERROR",
        message=msg,
        fix_hint=fix_hint,
        location=location,
        original_error=f"NameError: {msg}",
    )


def classify_import_error(exc: ImportError | ModuleNotFoundError) -> ClassifiedError:
    """Classify an ImportError or ModuleNotFoundError."""
    msg = str(exc)
    module = extract_module_from_importerror(msg)
    location = extract_location_from_tb(exc)

    fix_hint = "Check the module name or install the missing package."
    if module:
        if module.startswith("wren."):
            fix_hint = f"Module '{module}' not found in Wren SDK. Check the import path."
        else:
            fix_hint = f"Install missing package: pip install {module.split('.')[0]}"

    return ClassifiedError(
        error_type="AgentFixableError",
        error_code="IMPORT_ERROR",
        message=msg,
        fix_hint=fix_hint,
        location=location,
        original_error=f"{type(exc).__name__}: {msg}",
    )


def classify_type_error(exc: TypeError) -> ClassifiedError:
    """Classify a TypeError."""
    msg = str(exc)
    location = extract_location_from_tb(exc)

    fix_hint = "Check the types of arguments being passed."

    # Common patterns
    if "positional argument" in msg:
        fix_hint = "Check the number of arguments passed to the function."
    elif "unexpected keyword argument" in msg:
        fix_hint = "Remove the invalid keyword argument."
    elif "missing" in msg and "required" in msg:
        fix_hint = "Add the missing required argument."
    elif "not callable" in msg:
        fix_hint = "Check that you're calling a function, not a value."

    return ClassifiedError(
        error_type="AgentFixableError",
        error_code="TYPE_ERROR",
        message=msg,
        fix_hint=fix_hint,
        location=location,
        original_error=f"TypeError: {msg}",
    )


def classify_attribute_error(exc: AttributeError) -> ClassifiedError:
    """Classify an AttributeError."""
    msg = str(exc)
    location = extract_location_from_tb(exc)

    fix_hint = "Check the attribute name or ensure the object is correctly initialized."

    # Extract object type and attribute from message
    match = re.search(r"'([^']+)' object has no attribute '([^']+)'", msg)
    if match:
        obj_type, attr = match.groups()
        fix_hint = f"'{obj_type}' has no attribute '{attr}'. Check spelling or API documentation."

    return ClassifiedError(
        error_type="AgentFixableError",
        error_code="ATTRIBUTE_ERROR",
        message=msg,
        fix_hint=fix_hint,
        location=location,
        original_error=f"AttributeError: {msg}",
    )


def classify_value_error(exc: ValueError) -> ClassifiedError:
    """Classify a ValueError."""
    msg = str(exc)
    location = extract_location_from_tb(exc)

    fix_hint = "Check the value being passed."

    # Check for cron-related errors
    if "cron" in msg.lower():
        fix_hint = "Fix the cron expression. Format: 'minute hour day month weekday' (e.g., '0 9 * * 1-5')."

    return ClassifiedError(
        error_type="AgentFixableError",
        error_code="VALUE_ERROR",
        message=msg,
        fix_hint=fix_hint,
        location=location,
        original_error=f"ValueError: {msg}",
    )


def classify_file_not_found(exc: FileNotFoundError) -> ClassifiedError:
    """Classify a FileNotFoundError."""
    msg = str(exc)

    return ClassifiedError(
        error_type="AgentFixableError",
        error_code="FILE_NOT_FOUND",
        message=msg,
        fix_hint="Check the file path. Use absolute paths or paths relative to the script location.",
        original_error=f"FileNotFoundError: {msg}",
    )


def classify_exception(exc: Exception) -> ClassifiedError:
    """
    Classify any exception into an actionable error for agents.

    Returns a ClassifiedError with:
    - error_type: AgentFixableError, UserFacingConfigError, or InternalError
    - error_code: A machine-readable error code
    - message: Human-readable error message
    - fix_hint: Actionable suggestion for fixing the error
    - location: File/line/col where error occurred (if available)
    """
    if isinstance(exc, SyntaxError):
        return classify_syntax_error(exc)

    if isinstance(exc, NameError):
        return classify_name_error(exc)

    if isinstance(exc, (ImportError, ModuleNotFoundError)):
        return classify_import_error(exc)

    if isinstance(exc, TypeError):
        return classify_type_error(exc)

    if isinstance(exc, AttributeError):
        return classify_attribute_error(exc)

    if isinstance(exc, ValueError):
        return classify_value_error(exc)

    if isinstance(exc, FileNotFoundError):
        return classify_file_not_found(exc)

    # Check for common credential/config errors that need user action
    msg = str(exc).lower()
    if any(kw in msg for kw in ["api key", "credentials", "oauth", "authentication", "unauthorized", "403", "401"]):
        return ClassifiedError(
            error_type="UserFacingConfigError",
            error_code="AUTH_ERROR",
            message=str(exc),
            fix_hint="Configure credentials via the platform UI or environment variables.",
            original_error=f"{type(exc).__name__}: {exc}",
        )

    # Default: treat as agent-fixable with generic message
    location = extract_location_from_tb(exc)
    return ClassifiedError(
        error_type="AgentFixableError",
        error_code="RUNTIME_ERROR",
        message=str(exc),
        fix_hint="Check the error message and fix the underlying issue.",
        location=location,
        original_error=f"{type(exc).__name__}: {exc}",
    )


def format_error_for_agent(exc: Exception) -> dict:
    """
    Format an exception as a dict suitable for agent consumption.

    This is the main entry point for the CLI to use.
    """
    classified = classify_exception(exc)
    return classified.to_dict()
