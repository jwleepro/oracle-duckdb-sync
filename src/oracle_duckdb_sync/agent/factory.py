"""
Factory for creating agent with all dependencies.
"""
from typing import Optional

from oracle_duckdb_sync.application.query_service import QueryService
from oracle_duckdb_sync.application.sync_service import SyncService
from oracle_duckdb_sync.config import Config
from oracle_duckdb_sync.database.duckdb_source import DuckDBSource

from .core.agent import SyncAgent
from .core.llm_client import LLMClient, LLMConfig
from .tools.query_tools import GetTableStatsTool, ListTablesTool, QueryTableTool
from .tools.registry import ToolRegistry
from .tools.sync_tools import GetSyncStatusTool, StartSyncTool


class AgentFactory:
    """Factory for creating configured agent instances."""

    @staticmethod
    def create_agent(
        config: Config,
        llm_config: Optional[LLMConfig] = None,
        sync_service: Optional[SyncService] = None,
        query_service: Optional[QueryService] = None
    ) -> SyncAgent:
        """
        Create agent with dependency injection.

        This allows injecting mock services for testing.

        Args:
            config: 애플리케이션 설정
            llm_config: LLM 클라이언트 설정 (선택)
            sync_service: SyncService 인스턴스 (선택, 테스트용)
            query_service: QueryService 인스턴스 (선택, 테스트용)

        Returns:
            SyncAgent: 완전히 구성된 에이전트 인스턴스
        """
        # Create services if not provided
        if sync_service is None:
            sync_service = SyncService(config)

        if query_service is None:
            duckdb = DuckDBSource(config)
            query_service = QueryService(duckdb)

        # Create and populate tool registry
        registry = AgentFactory._register_all_tools(
            sync_service, query_service
        )

        # Create LLM client
        llm_client = LLMClient(llm_config or LLMConfig())

        return SyncAgent(llm_client, registry)

    @staticmethod
    def _register_all_tools(
        sync_service: SyncService,
        query_service: QueryService
    ) -> ToolRegistry:
        """Register all tools with their dependencies."""
        registry = ToolRegistry()

        # Sync tools
        registry.register(StartSyncTool(sync_service))
        registry.register(GetSyncStatusTool(sync_service))

        # Query tools
        registry.register(ListTablesTool(query_service))
        registry.register(GetTableStatsTool(query_service))
        registry.register(QueryTableTool(query_service))

        return registry
