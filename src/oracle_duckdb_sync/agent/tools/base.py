"""
Base class for agent tools with standardized interface.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class ToolResult:
    """도구 실행 결과."""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    message: str = ""


class BaseTool(ABC):
    """
    Abstract base class for all agent tools.

    각 도구는 이 클래스를 상속받아 구현합니다.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool name (e.g., 'start_sync')."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description for LLM (한글 권장)."""
        pass

    @property
    @abstractmethod
    def parameters_schema(self) -> dict:
        """JSON Schema for parameters."""
        pass

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters."""
        pass

    def to_openai_schema(self) -> dict:
        """Convert to OpenAI function calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema
            }
        }
