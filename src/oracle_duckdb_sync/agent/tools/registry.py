"""
Tool registry for dynamic tool management.
"""
from typing import Optional

from oracle_duckdb_sync.log.logger import get_logger

from .base import BaseTool, ToolResult

logger = get_logger(__name__)


class ToolRegistry:
    """
    Central registry for agent tools.

    Supports dynamic registration and dependency injection.
    """

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool."""
        if tool.name in self._tools:
            logger.warning(f"Tool '{tool.name}' already registered, overwriting.")
        self._tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name}")

    def get(self, name: str) -> Optional[BaseTool]:
        """Get tool by name."""
        return self._tools.get(name)

    def execute(self, name: str, **kwargs) -> ToolResult:
        """Execute a tool by name."""
        tool = self.get(name)
        if not tool:
            return ToolResult(
                success=False,
                error=f"알 수 없는 도구입니다: {name}"
            )

        try:
            return tool.execute(**kwargs)
        except Exception as e:
            logger.exception(f"Tool execution error: {name}")
            return ToolResult(
                success=False,
                error=f"도구 실행 중 오류가 발생했습니다: {str(e)}"
            )

    def get_all_schemas(self) -> list[dict]:
        """Get OpenAI schemas for all registered tools."""
        return [tool.to_openai_schema() for tool in self._tools.values()]

    def list_tools(self) -> list[str]:
        """List all registered tool names."""
        return list(self._tools.keys())
