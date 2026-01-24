"""
Runtime import helpers for metadata extraction.

Importing user scripts executes module-level init() calls and decorators,
populating the registry without running function bodies.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

from .registry import registry


def import_script(
    script_path: str,
    *,
    module_name: str = "user_script",
    clear_registry: bool = True,
) -> ModuleType:
    """
    Import a user script by path to trigger metadata registration.

    Args:
        script_path: Path to the Python script.
        module_name: Module name to register in sys.modules.
        clear_registry: Clear registry before import.

    Returns:
        Imported module instance.
    """
    path = Path(script_path).resolve()

    if not path.exists():
        raise FileNotFoundError(f"File not found: {script_path}")

    if path.suffix != ".py":
        raise ValueError(f"Not a Python file: {script_path}")

    if clear_registry:
        registry.clear()

    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load: {script_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module

    script_dir = str(path.parent)
    added_path = False
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
        added_path = True

    try:
        spec.loader.exec_module(module)
    finally:
        if added_path:
            sys.path.remove(script_dir)

    return module
