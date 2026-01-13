"""
Sync AI Agent - Main orchestrator for AI-powered data operations.
"""
import json
from dataclasses import dataclass
from typing import Optional

from oracle_duckdb_sync.log.logger import get_logger
from oracle_duckdb_sync.util.serialization import json_dumps_safe

from ..tools.registry import ToolRegistry
from .conversation import ConversationHistory
from .llm_client import AgentError, LLMClient

logger = get_logger(__name__)


@dataclass
class AgentResponse:
    """에이전트 응답 결과."""
    message: str
    tool_results: Optional[list[dict]] = None
    success: bool = True
    error: Optional[str] = None


class SyncAgent:
    """
    AI Agent that orchestrates data sync and query operations.

    Follows the ReAct pattern: Reason -> Act -> Observe
    """

    DEFAULT_SYSTEM_PROMPT = """You are an AI assistant for an Oracle-DuckDB data synchronization system.

You can help users with:
1. Starting and monitoring data synchronization
2. Querying synchronized data
3. Viewing statistics and analytics
4. Managing sync schedules

Always provide clear, concise responses in Korean.
When using tools, explain what you're doing and interpret the results for the user.

Available tools will be provided to you. Choose the appropriate tool based on the user's request."""

    def __init__(
        self,
        llm_client: LLMClient,
        tool_registry: ToolRegistry,
        system_prompt: Optional[str] = None
    ):
        self.llm = llm_client
        self.tools = tool_registry
        self.conversation = ConversationHistory(
            system_prompt or self.DEFAULT_SYSTEM_PROMPT
        )

    def process_message(self, user_message: str) -> AgentResponse:
        """
        Process user message and return response.

        Flow:
        1. Add user message to history
        2. Call LLM with tools schema
        3. If tool_calls: execute tools, add results, call LLM again
        4. Return final response
        """
        try:
            # 1. 사용자 메시지 추가
            self.conversation.add_user_message(user_message)

            # 2. LLM 호출 (도구 스키마 포함)
            tools_schema = self.tools.get_all_schemas()
            messages = self.conversation.to_openai_format()

            response = self.llm.chat_completion(
                messages=messages,
                tools=tools_schema if tools_schema else None
            )

            # 3. 도구 호출이 필요한 경우 처리
            tool_results = []
            while response.tool_calls:
                # 도구 호출 메시지 기록
                self.conversation.add_assistant_message(
                    content=response.content,
                    tool_calls=response.tool_calls
                )

                # 도구 실행
                for tool_call in response.tool_calls:
                    result = self._execute_tool_call(tool_call)
                    tool_results.append(result)

                    # 결과를 대화에 추가
                    self.conversation.add_tool_result(
                        tool_call_id=tool_call["id"],
                        name=tool_call["name"],
                        result=json_dumps_safe(result)
                    )

                # LLM 재호출 (도구 결과 포함)
                messages = self.conversation.to_openai_format()
                response = self.llm.chat_completion(
                    messages=messages,
                    tools=tools_schema if tools_schema else None
                )

            # 4. 최종 응답 기록 및 반환
            self.conversation.add_assistant_message(content=response.content)

            return AgentResponse(
                message=response.content or "작업이 완료되었습니다.",
                tool_results=tool_results if tool_results else None,
                success=True
            )

        except AgentError as e:
            logger.error(f"Agent error: {e}")
            return AgentResponse(
                message=str(e),
                success=False,
                error=str(e)
            )
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            return AgentResponse(
                message="예기치 않은 오류가 발생했습니다.",
                success=False,
                error=str(e)
            )

    def _execute_tool_call(self, tool_call: dict) -> dict:
        """Execute a single tool call and return result."""
        name = tool_call["name"]
        arguments = json.loads(tool_call["arguments"])

        logger.info(f"Executing tool: {name} with args: {arguments}")

        result = self.tools.execute(name, **arguments)

        return {
            "tool": name,
            "success": result.success,
            "data": result.data,
            "message": result.message,
            "error": result.error
        }

    def reset_conversation(self) -> None:
        """대화 히스토리 초기화."""
        self.conversation.clear()
