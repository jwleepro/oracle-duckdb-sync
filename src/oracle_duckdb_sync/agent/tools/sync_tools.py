"""
Synchronization tools for the agent.
"""
from oracle_duckdb_sync.application.sync_service import SyncService

from .base import BaseTool, ToolResult


class StartSyncTool(BaseTool):
    """Tool to start data synchronization."""

    def __init__(self, sync_service: SyncService):
        self._service = sync_service

    @property
    def name(self) -> str:
        return "start_sync"

    @property
    def description(self) -> str:
        return "Oracle 데이터베이스에서 지정된 테이블의 데이터를 DuckDB로 동기화합니다. 사용자가 동기화를 요청하거나 데이터를 최신화하고 싶을 때 사용합니다."

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "table_name": {
                    "type": "string",
                    "description": "동기화할 Oracle 테이블 이름 (예: USERS, ORDERS)"
                },
                "row_limit": {
                    "type": "integer",
                    "description": "동기화할 최대 행 수 (선택사항, 테스트용)",
                    "default": None
                }
            },
            "required": ["table_name"]
        }

    def execute(self, table_name: str, row_limit: int = None) -> ToolResult:
        """Execute synchronization."""
        params = {"oracle_table": table_name}
        if row_limit:
            params["row_limit"] = row_limit

        success = self._service.start_sync(params)

        if success:
            return ToolResult(
                success=True,
                data={"table_name": table_name, "started": True},
                message=f"'{table_name}' 테이블 동기화를 시작했습니다."
            )
        return ToolResult(
            success=False,
            error="동기화를 시작할 수 없습니다. 다른 동기화가 진행 중일 수 있습니다."
        )


class GetSyncStatusTool(BaseTool):
    """Tool to get synchronization status."""

    def __init__(self, sync_service: SyncService):
        self._service = sync_service

    @property
    def name(self) -> str:
        return "get_sync_status"

    @property
    def description(self) -> str:
        return "현재 동기화 작업의 상태와 진행 상황을 확인합니다. 동기화가 진행 중인지, 완료되었는지, 오류가 발생했는지 등을 알 수 있습니다."

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {},
            "required": []
        }

    def execute(self) -> ToolResult:
        """Get current sync status."""
        status = self._service.get_status()

        # Direct field access (Plan에서 수정 지시한 부분)
        status_data = {
            "state": status.state,
            "progress": status.progress,
            "result": status.result,
            "error": status.error
        }

        state_messages = {
            "idle": "현재 대기 중이며 실행 중인 작업은 없습니다.",
            "running": f"동기화가 진행 중입니다. 진행률: {status_data.get('progress', 0)}%",
            "completed": "최근 동기화 작업이 완료되었습니다.",
            "failed": f"동기화 작업이 실패했습니다. 오류: {status_data.get('error', '알 수 없음')}"
        }

        message = state_messages.get(status.state, f"현재 상태: {status.state}")

        return ToolResult(
            success=True,
            data=status_data,
            message=message
        )
