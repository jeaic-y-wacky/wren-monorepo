"""
Wren Types Module

Provides type inference, dynamic objects, and type conversion utilities.
Enables automatic type detection from context and type hints.
"""

import builtins
import inspect
import json
import re
from dataclasses import is_dataclass
from datetime import date, datetime
from typing import (
    Any,
    TypeVar,
    Union,
    cast,
    get_args,
    get_origin,
    get_type_hints,
)

from pydantic import BaseModel, create_model

T = TypeVar("T")


class DynamicObject:
    """Dynamic object that allows flexible attribute access.

    Provides both dict-style and attribute-style access to data.
    Includes smart type conversion methods.
    """

    def __init__(self, data: dict[str, Any] | None = None):
        self._data = data or {}

    def __getattr__(self, name: str) -> Any:
        """Get attribute value."""
        if name.startswith("_"):
            return super().__getattribute__(name)
        return self._data.get(name)

    def __setattr__(self, name: str, value: Any) -> None:
        """Set attribute value."""
        if name.startswith("_"):
            super().__setattr__(name, value)
        else:
            self._data[name] = value

    def __getitem__(self, key: str) -> Any:
        """Dict-style access."""
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        """Dict-style setting."""
        self._data[key] = value

    def __contains__(self, key: str) -> bool:
        """Check if key exists."""
        return key in self._data

    def __repr__(self) -> str:
        """String representation."""
        items = [f"{k}={v!r}" for k, v in self._data.items()]
        return f"DynamicObject({', '.join(items)})"

    def __bool__(self) -> bool:
        """Boolean conversion."""
        return bool(self._data)

    # Type conversion methods
    def to_bool(self) -> bool:
        """Convert to boolean."""
        if isinstance(self._data, dict) and len(self._data) == 1:
            # If there's a single value, use it
            value = next(iter(self._data.values()))
            return bool(value)
        return bool(self._data)

    def to_int(self) -> int:
        """Convert to integer."""
        if isinstance(self._data, dict) and len(self._data) == 1:
            value = next(iter(self._data.values()))
            return int(value)
        raise ValueError(f"Cannot convert {self._data} to int")

    def to_float(self) -> float:
        """Convert to float."""
        if isinstance(self._data, dict) and len(self._data) == 1:
            value = next(iter(self._data.values()))
            return float(value)
        raise ValueError(f"Cannot convert {self._data} to float")

    def to_str(self) -> str:
        """Convert to string."""
        if isinstance(self._data, dict) and len(self._data) == 1:
            value = next(iter(self._data.values()))
            return str(value)
        return json.dumps(self._data)

    def to_date(self) -> date:
        """Convert to date."""
        if isinstance(self._data, dict):
            if "date" in self._data:
                return parse_date(self._data["date"])
            if len(self._data) == 1:
                value = next(iter(self._data.values()))
                return parse_date(value)
        raise ValueError(f"Cannot convert {self._data} to date")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return self._data.copy()

    def to_json(self, **kwargs) -> str:
        """Convert to JSON string."""
        return json.dumps(self._data, default=str, **kwargs)

    @classmethod
    def from_dict(cls, data: builtins.dict[str, Any]) -> "DynamicObject":
        """Create from dictionary."""
        return cls(data)

    @classmethod
    def from_json(cls, json_str: str) -> "DynamicObject":
        """Create from JSON string."""
        return cls(json.loads(json_str))


def parse_date(value: Any) -> date:
    """Parse various date formats."""
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        # Try common date formats
        formats = [
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%B %d, %Y",
            "%b %d, %Y",
            "%B %dth, %Y",
            "%B %dst, %Y",
            "%B %dnd, %Y",
            "%B %drd, %Y",
        ]

        # Handle ordinal dates like "December 25th"
        value = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", value)

        for fmt in formats:
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue

        # Try ISO format as last resort
        try:
            return datetime.fromisoformat(value).date()
        except (ValueError, TypeError):
            pass

    raise ValueError(f"Cannot parse date from: {value}")


def infer_type(value: Any) -> type:
    """Infer the Python type of a value."""
    if value is None:
        return type(None)
    if isinstance(value, bool):
        return bool
    if isinstance(value, int):
        return int
    if isinstance(value, float):
        return float
    if isinstance(value, str):
        return str
    if isinstance(value, list):
        return list[Any]
    if isinstance(value, dict):
        return dict[str, Any]
    if isinstance(value, BaseModel) or is_dataclass(value):
        return type(value)
    return type(value)


def get_return_type(func) -> type | None:
    """Get the return type hint of a function.

    Returns None if no type hint is specified.
    """
    hints = get_type_hints(func)
    return hints.get("return")


def convert_to_type(value: Any, target_type: type[T]) -> T:
    """Convert a value to the target type.

    Handles:
    - Basic types (int, str, bool, etc.)
    - Pydantic models
    - Dataclasses
    - Optional types
    - Union types
    """
    # Handle None
    if value is None:
        if target_type is type(None):
            return cast(T, None)
        origin = get_origin(target_type)
        if origin is Union:
            args = get_args(target_type)
            if type(None) in args:
                return cast(T, None)
        raise ValueError(f"Cannot convert None to {target_type}")

    # Handle Optional
    origin = get_origin(target_type)
    if origin is Union:
        args = get_args(target_type)
        # Try each type in the Union
        for arg_type in args:
            if arg_type is type(None):
                continue
            try:
                return convert_to_type(value, arg_type)
            except (ValueError, TypeError):
                continue
        raise ValueError(f"Cannot convert {value} to any type in {target_type}")

    # Handle basic types
    if target_type in [int, float, str, bool]:
        if isinstance(value, dict) and len(value) == 1:
            # Extract single value from dict
            value = next(iter(value.values()))
        return target_type(value)  # type: ignore[call-arg]

    # Handle date/datetime
    if target_type is date:
        return cast(T, parse_date(value))
    if target_type is datetime:
        if isinstance(value, str):
            return cast(T, datetime.fromisoformat(value))
        raise ValueError(f"Cannot convert {type(value)} to datetime")

    # Handle Pydantic models
    if isinstance(target_type, type) and issubclass(target_type, BaseModel):
        if isinstance(value, dict):
            return target_type(**value)
        if isinstance(value, str):
            # Try to parse JSON
            try:
                data = json.loads(value)
                return target_type(**data)
            except (json.JSONDecodeError, TypeError, ValueError):
                # Try to create with single field
                return target_type(value=value)
        elif isinstance(value, DynamicObject):
            return target_type(**value._data)
        else:
            return target_type(value)  # type: ignore[call-arg]

    # Handle dataclasses
    if is_dataclass(target_type):
        if isinstance(value, dict):
            return target_type(**value)
        if isinstance(value, DynamicObject):
            return target_type(**value._data)
        return target_type(value)  # type: ignore[call-arg]

    # Handle List
    if origin is list or origin is list:
        args = get_args(target_type)
        if args:
            item_type = args[0]
            if isinstance(value, list):
                return cast(T, [convert_to_type(item, item_type) for item in value])
            return cast(T, [convert_to_type(value, item_type)])
        return cast(T, list(value))

    # Handle Dict
    if origin is dict or origin is dict:
        if isinstance(value, dict):
            return cast(T, value)
        if isinstance(value, DynamicObject):
            return cast(T, value._data)
        return cast(T, dict(value))

    # Handle DynamicObject
    if target_type is DynamicObject:
        if isinstance(value, DynamicObject):
            return cast(T, value)
        if isinstance(value, dict):
            return cast(T, DynamicObject(value))
        return cast(T, DynamicObject({"value": value}))

    # Default: try direct conversion
    return cast(T, target_type(value))  # type: ignore[call-arg]


def create_dynamic_model(name: str, fields: dict[str, Any]) -> type[BaseModel]:
    """Create a dynamic Pydantic model with the given fields.

    Example:
        Model = create_dynamic_model('Booking', {
            'name': str,
            'date': date,
            'guests': int
        })
    """
    return create_model(name, **fields)


def extract_type_from_assignment() -> type | None:
    """Extract the expected type from variable assignment in the calling frame.

    Example:
        booking: BookingRequest = wren.ai.extract(text)
        # This function can detect that BookingRequest is expected
    """
    frame = inspect.currentframe()
    if not frame or not frame.f_back or not frame.f_back.f_back:
        return None

    # Get the caller's frame (2 levels up)
    caller_frame = frame.f_back.f_back

    # Try to find type annotations in the frame
    if hasattr(caller_frame, "f_locals") and "__annotations__" in caller_frame.f_locals:
        annotations = caller_frame.f_locals["__annotations__"]

        # Get the variable being assigned (heuristic: last annotation)
        if annotations:
            # This is a simplified approach - in practice we'd need more sophisticated parsing
            last_var = list(annotations.keys())[-1]
            return annotations[last_var]

    return None


class TypedResult:
    """Result wrapper that provides typed access methods."""

    def __init__(self, value: Any, inferred_type: type | None = None):
        self.value = value
        self.inferred_type = inferred_type or infer_type(value)

    def as_type(self, target_type: type[T]) -> T:
        """Convert to specific type."""
        return convert_to_type(self.value, target_type)

    def to_bool(self) -> bool:
        """Convert to boolean."""
        return convert_to_type(self.value, bool)

    def to_int(self) -> int:
        """Convert to integer."""
        return convert_to_type(self.value, int)

    def to_float(self) -> float:
        """Convert to float."""
        return convert_to_type(self.value, float)

    def to_str(self) -> str:
        """Convert to string."""
        return convert_to_type(self.value, str)

    def to_date(self) -> date:
        """Convert to date."""
        return convert_to_type(self.value, date)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return convert_to_type(self.value, dict[str, Any])

    def __repr__(self) -> str:
        return f"TypedResult(value={self.value!r}, type={self.inferred_type})"
