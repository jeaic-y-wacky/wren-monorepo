"""
Wren Core Module

Core infrastructure: configuration, context, registry, runtime, and types.
"""

from .config import WrenConfig, config, get_config, reload_config
from .context import context, get_request_id, with_context
from .registry import get_metadata, registry
from .runtime import import_script
from .types import (
    convert_to_type,
    create_dynamic_model,
    extract_type_from_assignment,
    get_return_type,
    infer_type,
    parse_date,
)

__all__ = [
    # Config
    "config",
    "get_config",
    "reload_config",
    "WrenConfig",
    # Context
    "context",
    "with_context",
    "get_request_id",
    # Registry
    "registry",
    "get_metadata",
    # Runtime
    "import_script",
    # Types
    "convert_to_type",
    "parse_date",
    "infer_type",
    "get_return_type",
    "extract_type_from_assignment",
    "create_dynamic_model",
]
