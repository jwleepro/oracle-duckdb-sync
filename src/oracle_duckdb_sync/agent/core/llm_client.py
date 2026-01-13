"""
OpenAI LLM Client - Wrapper for OpenAI API with function calling support.
"""
from dataclasses import dataclass, field
from typing import Optional

from openai import APIConnectionError, APIError, OpenAI, RateLimitError

from oracle_duckdb_sync.log.logger import get_logger

logger = get_logger(__name__)


@dataclass
class LLMConfig:
    """LLM 클라이언트 설정."""
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int = 2048
    api_key: Optional[str] = None  # None이면 환경변수에서 읽음


@dataclass
class LLMResponse:
    """LLM 응답 결과."""
    content: Optional[str]
    tool_calls: Optional[list[dict]]
    finish_reason: str
    usage: dict[str, int] = field(default_factory=dict)


class AgentError(Exception):
    """Agent 관련 에러."""
    pass


class LLMClient:
    """OpenAI API client with function calling support."""

    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig()
        self._client: Optional[OpenAI] = None

    def _get_client(self) -> OpenAI:
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            self._client = OpenAI(api_key=self.config.api_key)
        return self._client

    def chat_completion(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        tool_choice: str = "auto"
    ) -> LLMResponse:
        """
        Send chat completion request with optional function calling.

        Args:
            messages: OpenAI 포맷의 메시지 리스트
            tools: 사용 가능한 도구 스키마 리스트
            tool_choice: 도구 선택 방식 ("auto", "none", 또는 특정 도구명)

        Returns:
            LLMResponse: 응답 내용과 도구 호출 정보
        """
        try:
            client = self._get_client()

            kwargs = {
                "model": self.config.model,
                "messages": messages,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
            }

            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = tool_choice

            response = client.chat.completions.create(**kwargs)

            return self._parse_response(response)

        except RateLimitError as e:
            logger.warning(f"Rate limit hit: {e}")
            raise AgentError("API 요청 한도에 도달했습니다. 잠시 후 다시 시도해주세요.") from e
        except APIConnectionError as e:
            logger.error(f"Connection error: {e}")
            raise AgentError("API 연결에 실패했습니다. 네트워크를 확인해주세요.") from e
        except APIError as e:
            logger.error(f"API error: {e}")
            raise AgentError(f"API 오류가 발생했습니다: {e.message}") from e

    def _parse_response(self, response) -> LLMResponse:
        """OpenAI 응답을 LLMResponse로 변환."""
        choice = response.choices[0]
        message = choice.message

        tool_calls = None
        if message.tool_calls:
            tool_calls = [
                {
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": tc.function.arguments
                }
                for tc in message.tool_calls
            ]

        return LLMResponse(
            content=message.content,
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        )
