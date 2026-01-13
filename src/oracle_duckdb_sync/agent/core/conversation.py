"""
Conversation history management for multi-turn dialogues.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class Message:
    """단일 대화 메시지."""
    role: str  # 'user', 'assistant', 'system', 'tool'
    content: Optional[str]
    tool_calls: Optional[list[dict]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


class ConversationHistory:
    """
    Manages conversation history with token-aware truncation.

    멀티턴 대화를 관리하고 OpenAI API 포맷으로 변환합니다.
    """

    def __init__(self, system_prompt: str, max_messages: int = 50):
        self.system_prompt = system_prompt
        self.max_messages = max_messages
        self._messages: list[Message] = []

    def add_user_message(self, content: str) -> None:
        """사용자 메시지 추가."""
        self._messages.append(Message(role="user", content=content))
        self._truncate_if_needed()

    def add_assistant_message(
        self,
        content: Optional[str] = None,
        tool_calls: Optional[list[dict]] = None
    ) -> None:
        """어시스턴트 메시지 추가."""
        self._messages.append(Message(
            role="assistant",
            content=content,
            tool_calls=tool_calls
        ))
        self._truncate_if_needed()

    def add_tool_result(
        self,
        tool_call_id: str,
        name: str,
        result: str
    ) -> None:
        """도구 실행 결과 추가."""
        self._messages.append(Message(
            role="tool",
            content=result,
            tool_call_id=tool_call_id,
            name=name
        ))
        self._truncate_if_needed()

    def to_openai_format(self) -> list[dict]:
        """OpenAI API 포맷으로 변환."""
        messages = [{"role": "system", "content": self.system_prompt}]

        for msg in self._messages:
            formatted: dict[str, Any] = {"role": msg.role}

            if msg.content is not None:
                formatted["content"] = msg.content

            if msg.tool_calls:
                formatted["tool_calls"] = [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": tc["arguments"]
                        }
                    }
                    for tc in msg.tool_calls
                ]

            if msg.tool_call_id:
                formatted["tool_call_id"] = msg.tool_call_id

            if msg.name:
                formatted["name"] = msg.name

            messages.append(formatted)

        return messages

    def clear(self) -> None:
        """대화 히스토리 초기화."""
        self._messages.clear()

    def _truncate_if_needed(self) -> None:
        """최대 메시지 수 초과 시 오래된 메시지 제거."""
        if len(self._messages) > self.max_messages:
            # 가장 오래된 메시지부터 제거 (시스템 프롬프트는 유지)
            self._messages = self._messages[-self.max_messages:]
