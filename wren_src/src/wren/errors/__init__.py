"""
Wren Errors Module

Error classes and classification.
"""

from .base import (
    WrenError,
    ConfigurationError,
    AIProviderError,
    TypeInferenceError,
    handle_error,
)
from .classifier import (
    classify_exception,
    format_error_for_agent,
    ClassifiedError,
    ErrorLocation,
    ErrorType,
)

__all__ = [
    # Base errors
    'WrenError',
    'ConfigurationError',
    'AIProviderError',
    'TypeInferenceError',
    'handle_error',
    # Classifier
    'classify_exception',
    'format_error_for_agent',
    'ClassifiedError',
    'ErrorLocation',
    'ErrorType',
]
