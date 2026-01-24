"""
Wren Context Module

Provides thread-local context management for automatic context flow.
Context flows automatically through the call stack without parameter passing.
"""

import threading
from typing import Any, Optional, Dict, List
from contextlib import contextmanager
from dataclasses import dataclass, field
import uuid
from datetime import datetime


@dataclass
class ContextFrame:
    """A single frame in the context stack."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = field(default_factory=dict)
    parent: Optional['ContextFrame'] = None

    def get(self, key: str, default: Any = None) -> Any:
        """Get value from this frame or parent frames."""
        if key in self.data:
            return self.data[key]
        elif self.parent:
            return self.parent.get(key, default)
        return default

    def set(self, key: str, value: Any) -> None:
        """Set value in this frame."""
        self.data[key] = value

    def update(self, **kwargs) -> None:
        """Update multiple values in this frame."""
        self.data.update(kwargs)

    def all_data(self) -> Dict[str, Any]:
        """Get all data from this frame and parent frames."""
        result = {}
        if self.parent:
            result.update(self.parent.all_data())
        result.update(self.data)
        return result


class WrenContext:
    """Thread-local context manager for Wren.

    Provides automatic context propagation through the call stack.
    Each thread has its own context stack.
    """

    def __init__(self):
        self._local = threading.local()

    @property
    def _stack(self) -> List[ContextFrame]:
        """Get the context stack for the current thread."""
        if not hasattr(self._local, 'stack'):
            self._local.stack = []
        return self._local.stack

    @property
    def current(self) -> Optional[ContextFrame]:
        """Get the current context frame."""
        stack = self._stack
        return stack[-1] if stack else None

    def push(self, **data) -> ContextFrame:
        """Push a new context frame onto the stack."""
        parent = self.current
        frame = ContextFrame(parent=parent)
        frame.update(**data)
        self._stack.append(frame)
        return frame

    def pop(self) -> Optional[ContextFrame]:
        """Pop the current context frame from the stack."""
        stack = self._stack
        if stack:
            return stack.pop()
        return None

    @contextmanager
    def scope(self, **data):
        """Context manager for temporary context scope.

        Example:
            with context.scope(email=email_obj, urgent=True):
                # This code has access to email and urgent in context
                process_email()
        """
        frame = self.push(**data)
        try:
            yield frame
        finally:
            self.pop()

    def get(self, key: str, default: Any = None) -> Any:
        """Get value from current context."""
        frame = self.current
        if frame:
            return frame.get(key, default)
        return default

    def set(self, key: str, value: Any) -> None:
        """Set value in current context."""
        frame = self.current
        if not frame:
            # Auto-create a frame if none exists
            frame = self.push()
        frame.set(key, value)

    def update(self, **kwargs) -> None:
        """Update multiple values in current context."""
        frame = self.current
        if not frame:
            # Auto-create a frame if none exists
            frame = self.push()
        frame.update(**kwargs)

    def clear(self) -> None:
        """Clear all context for current thread."""
        self._local.stack = []

    @property
    def all_data(self) -> Dict[str, Any]:
        """Get all data from the current context stack."""
        frame = self.current
        if frame:
            return frame.all_data()
        return {}

    # Magic attribute access for convenience
    def __getattr__(self, name: str) -> Any:
        """Allow attribute-style access to context values.

        Example:
            context.email  # Same as context.get('email')
        """
        if name.startswith('_'):
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
        return self.get(name)

    def __setattr__(self, name: str, value: Any) -> None:
        """Allow attribute-style setting of context values.

        Example:
            context.email = email_obj  # Same as context.set('email', email_obj)
        """
        if name.startswith('_') or name in ['_local']:
            super().__setattr__(name, value)
        else:
            self.set(name, value)

    def __contains__(self, key: str) -> bool:
        """Check if key exists in context."""
        frame = self.current
        if frame:
            return key in frame.all_data()
        return False

    def __repr__(self) -> str:
        """String representation of current context."""
        data = self.all_data
        if data:
            items = [f"{k}={v!r}" for k, v in data.items()]
            return f"WrenContext({', '.join(items)})"
        return "WrenContext(empty)"


# Global context instance
context = WrenContext()


# Decorator for automatic context injection
def with_context(**ctx_data):
    """Decorator to inject context for a function call.

    Example:
        @with_context(source="email")
        def process_message(text):
            # context.source is available here
            if context.source == "email":
                ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            with context.scope(**ctx_data):
                return func(*args, **kwargs)
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    return decorator


# Convenience function to get request/session ID
def get_request_id() -> str:
    """Get current request ID from context or generate new one."""
    request_id = context.get('request_id')
    if not request_id:
        request_id = str(uuid.uuid4())
        context.set('request_id', request_id)
    return request_id


# Convenience function to check if running in async context
def is_async_context() -> bool:
    """Check if running in an async context."""
    try:
        import asyncio
        asyncio.current_task()
        return True
    except RuntimeError:
        return False