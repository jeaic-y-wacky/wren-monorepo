"""
Wren Errors Module

Error classes and classification.
"""

from .base import (
    AIProviderError,
    ConfigurationError,
    TypeInferenceError,
    WrenError,
    handle_error,
)
from .classifier import (
    ClassifiedError,
    ErrorLocation,
    ErrorType,
    classify_exception,
    format_error_for_agent,
)

__all__ = [
    # Base errors
    "WrenError",
    "ConfigurationError",
    "AIProviderError",
    "TypeInferenceError",
    "handle_error",
    # Classifier
    "classify_exception",
    "format_error_for_agent",
    "ClassifiedError",
    "ErrorLocation",
    "ErrorType",
]
