"""
Wren Agent Context - State tracking for agent execution.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class AgentContext:
    """Context passed through the agent run, tracking script state."""

    # User's original request
    user_request: str = ""

    # Working directory for scripts (default: wren_agent/scripts/)
    workspace_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent / "scripts")

    # Current script being worked on
    script_path: Path | None = None
    script_content: str | None = None

    # Iteration tracking
    iteration_count: int = 0
    max_iterations: int = 5

    # Test results
    last_test_result: dict[str, Any] | None = None

    # Error history (for learning from mistakes)
    error_history: list[dict[str, Any]] = field(default_factory=list)

    def record_error(self, error: dict[str, Any]) -> None:
        """Record an error for history tracking."""
        self.error_history.append({
            "iteration": self.iteration_count,
            "error": error,
        })

    def can_iterate(self) -> bool:
        """Check if we can still iterate on fixes."""
        return self.iteration_count < self.max_iterations

    def is_valid(self) -> bool:
        """Check if the current script is valid."""
        return (
            self.last_test_result is not None
            and self.last_test_result.get("valid", False)
        )
