"""
Query tools for data retrieval and analysis.
"""
from oracle_duckdb_sync.application.query_service import QueryService

from .base import BaseTool, ToolResult


class ListTablesTool(BaseTool):
    """Tool to list available tables."""

    def __init__(self, query_service: QueryService):
        self._service = query_service

    @property
    def name(self) -> str:
        return "list_tables"

    @property
    def description(self) -> str:
        return "DuckDB에서 조회 가능한 테이블 목록을 반환합니다. 어떤 테이블이 있는지 확인할 때 사용합니다."

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {},
            "required": []
        }

    def execute(self) -> ToolResult:
        tables = self._service.get_available_tables()
        return ToolResult(
            success=True,
            data={"tables": tables, "count": len(tables)},
            message=f"{len(tables)}개 테이블 발견: {', '.join(tables)}"
        )


class GetTableStatsTool(BaseTool):
    """Tool to get table statistics."""

    def __init__(self, query_service: QueryService):
        self._service = query_service

    @property
    def name(self) -> str:
        return "get_table_stats"

    @property
    def description(self) -> str:
        return "특정 테이블의 행 수와 기본 통계를 조회합니다. 테이블의 데이터 규모를 파악할 때 사용합니다."

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "table_name": {
                    "type": "string",
                    "description": "조회할 테이블 이름"
                }
            },
            "required": ["table_name"]
        }

    def execute(self, table_name: str) -> ToolResult:
        try:
            row_count = self._service.get_table_row_count(table_name)
            return ToolResult(
                success=True,
                data={"table_name": table_name, "row_count": row_count},
                message=f"'{table_name}' 테이블: {row_count:,}행"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"테이블 통계 조회 실패: {str(e)}"
            )


class QueryTableTool(BaseTool):
    """Tool to query table data."""

    def __init__(self, query_service: QueryService):
        self._service = query_service

    @property
    def name(self) -> str:
        return "query_table"

    @property
    def description(self) -> str:
        return "테이블 데이터를 조회하고 요약 정보를 반환합니다. 실제 데이터를 확인하거나 샘플을 볼 때 사용합니다."

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "table_name": {
                    "type": "string",
                    "description": "조회할 테이블 이름"
                },
                "limit": {
                    "type": "integer",
                    "description": "반환할 최대 행 수 (기본값: 10)",
                    "default": 10
                }
            },
            "required": ["table_name"]
        }

    def execute(self, table_name: str, limit: int = 10) -> ToolResult:
        try:
            result = self._service.query_table(table_name, limit=limit)

            if result.success:
                df = result.data
                summary = {
                    "table_name": table_name,
                    "columns": list(df.columns),
                    "row_count": len(df),
                    "sample": df.head(5).to_dict(orient='records')
                }
                return ToolResult(
                    success=True,
                    data=summary,
                    message=f"'{table_name}' 테이블에서 {len(df)}행 조회됨"
                )
            return ToolResult(
                success=False,
                error=result.error
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"테이블 조회 실패: {str(e)}"
            )
