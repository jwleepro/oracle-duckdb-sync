"""
UI Presenter Interface - Framework-independent UI abstraction.

This module defines abstract interfaces that allow the application layer
to communicate with any UI framework without direct dependencies.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class MessageContext:
    """Context information for UI messages."""
    level: str  # 'info', 'warning', 'error', 'success'
    message: str
    details: Optional[str] = None
    expandable: bool = False


class UIPresenter(ABC):
    """
    Abstract interface for UI presentation layer.

    This allows the application to be UI framework agnostic.
    Implementations can be created for Streamlit, Flask, CLI, etc.
    """

    @abstractmethod
    def show_message(self, context: MessageContext) -> None:
        """Display a message to the user."""
        pass

    @abstractmethod
    def show_progress(self, percentage: float, message: str) -> None:
        """Display progress indicator."""
        pass

    @abstractmethod
    def show_spinner(self, message: str) -> Any:
        """Show loading spinner. Returns context manager."""
        pass

    @abstractmethod
    def get_user_input(self,
                       label: str,
                       default_value: Any = None,
                       input_type: str = 'text',
                       **kwargs) -> Any:
        """Get input from user."""
        pass

    @abstractmethod
    def show_button(self, label: str, disabled: bool = False, **kwargs) -> bool:
        """Show button and return True if clicked."""
        pass

    @abstractmethod
    def show_dataframe(self, df: Any, max_rows: Optional[int] = None) -> None:
        """Display a DataFrame."""
        pass

    @abstractmethod
    def show_chart(self, chart_data: Any, **kwargs) -> None:
        """Display a chart."""
        pass

    @abstractmethod
    def trigger_rerun(self) -> None:
        """Trigger UI refresh/rerun."""
        pass


class SessionStateManager(ABC):
    """
    Abstract interface for session state management.

    Provides framework-independent access to session state.
    """

    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """Get value from session state."""
        pass

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """Set value in session state."""
        pass

    @abstractmethod
    def has(self, key: str) -> bool:
        """Check if key exists in session state."""
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """Remove key from session state."""
        pass

    @abstractmethod
    def clear_pattern(self, pattern: str) -> None:
        """Clear all keys matching a pattern."""
        pass


class LayoutManager(ABC):
    """
    Abstract interface for UI layout management.
    """

    @abstractmethod
    def create_columns(self, ratios: list[int]) -> list[Any]:
        """Create column layout. Returns column contexts."""
        pass

    @abstractmethod
    def create_expander(self, title: str, expanded: bool = False) -> Any:
        """Create expandable section. Returns context manager."""
        pass

    @abstractmethod
    def create_sidebar(self) -> Any:
        """Get sidebar context. Returns context manager."""
        pass

    @abstractmethod
    def add_divider(self) -> None:
        """Add a visual divider."""
        pass
