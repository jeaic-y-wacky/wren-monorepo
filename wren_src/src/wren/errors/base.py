"""
Wren Errors Module

Provides educational error messages that teach users how to fix problems.
Every error includes: what went wrong, what was expected, how to fix it, and examples.
"""

import traceback
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

console = Console(stderr=True)


class WrenError(Exception):
    """Base exception for all Wren errors."""

    def __init__(
        self,
        message: str,
        expected: str | None = None,
        found: str | None = None,
        fix: str | None = None,
        example: str | None = None,
        docs_url: str | None = None,
        original_error: Exception | None = None,
    ):
        self.message = message
        self.expected = expected
        self.found = found
        self.fix = fix
        self.example = example
        self.docs_url = docs_url
        self.original_error = original_error

        # Build the full error message
        super().__init__(self._build_message())

    def _build_message(self) -> str:
        """Build the complete error message."""
        parts = [f"❌ {self.message}"]

        if self.expected:
            parts.append(f"\nExpected: {self.expected}")

        if self.found:
            parts.append(f"Found: {self.found}")

        if self.fix:
            parts.append(f"\n✅ Fix: {self.fix}")

        if self.example:
            parts.append(f"\n📝 Example:\n{self.example}")

        if self.docs_url:
            parts.append(f"\n📚 Learn more: {self.docs_url}")

        if self.original_error:
            parts.append(f"\n\nOriginal error: {str(self.original_error)}")

        return "\n".join(parts)

    def display(self) -> None:
        """Display the error with rich formatting."""
        console.print(
            Panel(
                self._build_message(), title="[bold red]Wren Error[/bold red]", border_style="red"
            )
        )


class ConfigurationError(WrenError):
    """Error related to configuration issues."""

    @classmethod
    def missing_api_key(cls, provider: str = "Portkey") -> "ConfigurationError":
        """Create error for missing API key."""
        return cls(
            message=f"{provider} API key not configured",
            expected=f"Valid {provider} API key in environment variables",
            found="No API key configured",
            fix=f"Set up {provider} authentication",
            example="""# Get your Portkey API key from https://app.portkey.ai
export PORTKEY_API_KEY="your-portkey-api-key"

# Optional: Set a virtual key for a specific provider
export PORTKEY_VIRTUAL_KEY="your-virtual-key"

# Or in .env file:
echo 'PORTKEY_API_KEY=your-api-key' >> .env""",
            docs_url="https://docs.portkey.ai/docs/api-reference/authentication",
        )

    @classmethod
    def invalid_config(cls, key: str, value: Any, expected_type: type) -> "ConfigurationError":
        """Create error for invalid configuration value."""
        return cls(
            message=f"Invalid configuration value for {key}",
            expected=f"Value of type {expected_type.__name__}",
            found=f"Value '{value}' of type {type(value).__name__}",
            fix=f"Provide a valid {expected_type.__name__} value",
            example=f"""# Set correct value type
export WREN_{key.upper()}=<valid_{expected_type.__name__}_value>""",
            docs_url=f"https://docs.wren.ai/configuration#{key}",
        )


class AIProviderError(WrenError):
    """Error related to AI provider issues."""

    @classmethod
    def api_error(cls, provider: str, error: Exception) -> "AIProviderError":
        """Create error for AI API issues."""
        return cls(
            message=f"{provider} API error occurred",
            expected="Successful API response",
            found=str(error),
            fix="Check your API key, network connection, and rate limits",
            example="""# Verify your API key is valid
wren.config.openai_api_key  # Should not be None

# Check network connectivity
import requests
requests.get('https://api.openai.com')  # Should succeed

# Consider rate limiting
import time
time.sleep(1)  # Add delay between requests""",
            docs_url=f"https://docs.wren.ai/providers/{provider.lower()}",
            original_error=error,
        )

    @classmethod
    def model_not_found(cls, model: str, provider: str) -> "AIProviderError":
        """Create error for unknown model."""
        return cls(
            message=f"Model '{model}' not found for {provider}",
            expected="Valid model name",
            found=f"'{model}'",
            fix=f"Use a valid {provider} model",
            example=f"""# Valid {provider} models:
- gpt-4-turbo-preview
- gpt-3.5-turbo
- claude-3-opus-20240229
- claude-3-sonnet-20240229

# Set model:
export WREN_MODEL="gpt-4-turbo-preview" """,
            docs_url="https://docs.wren.ai/models",
        )


class TypeInferenceError(WrenError):
    """Error related to type inference issues."""

    @classmethod
    def cannot_convert(cls, value: Any, target_type: type) -> "TypeInferenceError":
        """Create error for type conversion failure."""
        value_repr = repr(value)[:100] + "..." if len(repr(value)) > 100 else repr(value)

        return cls(
            message=f"Cannot convert value to {target_type.__name__}",
            expected=f"Value convertible to {target_type.__name__}",
            found=f"Value: {value_repr} (type: {type(value).__name__})",
            fix=f"Ensure the value can be converted to {target_type.__name__}",
            example="""# For Pydantic models:
from pydantic import BaseModel
from datetime import date

class Booking(BaseModel):
    name: str
    date: date

# Provide compatible data:
data = {"name": "John", "date": "2024-12-25"}
booking: Booking = wren.ai.extract(data)""",
            docs_url="https://docs.wren.ai/types",
        )

    @classmethod
    def no_type_hint(cls, context: str) -> "TypeInferenceError":
        """Create error for missing type hint."""
        return cls(
            message="Cannot infer type without type hint",
            expected="Type hint for variable assignment",
            found="No type hint provided",
            fix="Add a type hint to specify expected type",
            example="""# Add type hint to variable:
from typing import List
from pydantic import BaseModel

class Item(BaseModel):
    name: str
    price: float

# With type hint - Wren knows what to extract:
items: List[Item] = wren.ai.extract(text)

# Or use explicit type parameter:
items = wren.ai.extract(text, List[Item])""",
            docs_url="https://docs.wren.ai/type-inference",
        )


class ContextError(WrenError):
    """Error related to context management."""

    @classmethod
    def missing_context(cls, key: str) -> "ContextError":
        """Create error for missing context value."""
        return cls(
            message=f"Context key '{key}' not found",
            expected=f"Context to contain '{key}'",
            found="Key not in current context",
            fix="Ensure the context is properly set",
            example=f"""# Set context before accessing:
from wren import context

# Option 1: Direct setting
context.{key} = value

# Option 2: Context scope
with context.scope({key}=value):
    # Access context.{key} here
    process()

# Option 3: Decorator
@wren.on_email()
def handler(email):
    # email automatically in context
    pass""",
            docs_url="https://docs.wren.ai/context",
        )


def handle_error(error: Exception, context: str = "") -> None:
    """Handle and display any error with educational formatting.

    Args:
        error: The exception that occurred
        context: Additional context about what was being attempted
    """
    if isinstance(error, WrenError):
        error.display()
    else:
        # Wrap in generic WrenError with helpful message
        wrapped = WrenError(
            message=f"Unexpected error{f' while {context}' if context else ''}",
            expected="Operation to succeed",
            found=f"{type(error).__name__}: {str(error)}",
            fix="Check the error details and ensure your input is valid",
            example="""# Debug the error:
import wren
wren.config.debug = True  # Enable debug mode
wren.config.verbose = True  # Show detailed output

# Then retry your operation""",
            docs_url="https://docs.wren.ai/debugging",
            original_error=error,
        )
        wrapped.display()

        # In debug mode, also show the traceback
        from .config import get_config

        if get_config().debug:
            console.print("\n[dim]Full traceback:[/dim]")
            console.print(
                Syntax(traceback.format_exc(), "python", theme="monokai", line_numbers=True)
            )


def assert_config_valid(config) -> None:
    """Assert that configuration is valid, raise educational error if not."""
    if not config.has_ai_provider:
        raise ConfigurationError.missing_api_key()


def safe_import(module_name: str, package_name: str | None = None) -> Any:
    """Safely import a module with educational error if missing."""
    try:
        import importlib

        return importlib.import_module(module_name)
    except ImportError as e:
        package = package_name or module_name
        raise WrenError(
            message=f"Required package '{package}' is not installed",
            expected=f"Package '{package}' to be available",
            found="Package not found in environment",
            fix="Install the required package",
            example=f"""# Install with pip:
pip install {package}

# Or with uv:
uv pip install {package}

# For Wren with extras:
pip install wren[integrations]""",
            docs_url="https://docs.wren.ai/installation",
            original_error=e,
        )
