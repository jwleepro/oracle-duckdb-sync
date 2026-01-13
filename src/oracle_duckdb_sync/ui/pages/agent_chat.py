"""
AI Agent Chat Interface - Streamlit page for conversational AI.
"""
from typing import Optional

import streamlit as st

from oracle_duckdb_sync.agent import SyncAgent
from oracle_duckdb_sync.agent.core.llm_client import LLMConfig
from oracle_duckdb_sync.agent.factory import AgentFactory
from oracle_duckdb_sync.config import load_config


def initialize_agent():
    """Initialize agent with all services and tools."""
    config = load_config()
    llm_config = LLMConfig(model="gpt-4o-mini")
    return AgentFactory.create_agent(config, llm_config)


def initialize_chat_state():
    """Initialize chat session state."""
    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = []
    if 'agent' not in st.session_state:
        st.session_state.agent = initialize_agent()


def render_chat_message(role: str, content: str):
    """Render a single chat message."""
    with st.chat_message(role):
        st.markdown(content)


def stream_agent_response(
    agent: SyncAgent,
    prompt: str
) -> tuple[Optional[str], list[dict]]:
    """
    Agent streaming 응답을 Streamlit에 실시간 렌더링.

    Args:
        agent: SyncAgent 인스턴스
        prompt: 사용자 입력 메시지

    Returns:
        tuple: (응답 텍스트, 도구 실행 결과 리스트)
    """
    tool_results = []

    with st.chat_message("assistant"):
        text_placeholder = st.empty()
        status_placeholder = st.empty()
        full_text = ""

        for chunk in agent.process_message_stream(prompt):
            if chunk.type == "text":
                full_text += chunk.content
                text_placeholder.markdown(full_text + "▌")

            elif chunk.type == "tool_status":
                status_placeholder.info(f"🔧 {chunk.content}")

            elif chunk.type == "tool_result":
                tool_results.append(chunk.tool_result)
                status_placeholder.empty()

            elif chunk.type == "error":
                text_placeholder.error(f"⚠️ {chunk.error}")
                return None, []

            elif chunk.type == "done":
                text_placeholder.markdown(full_text)
                status_placeholder.empty()

    return full_text, tool_results


def main():
    st.set_page_config(
        page_title="Data Sync AI Assistant",
        page_icon="🤖",
        layout="wide"
    )

    st.title("🤖 데이터 동기화 AI 어시스턴트")
    st.caption("데이터 동기화 및 분석을 도와드립니다.")

    initialize_chat_state()

    # Sidebar: Tool information and settings
    with st.sidebar:
        st.header("⚙️ 설정")

        if st.button("🔄 대화 초기화"):
            st.session_state.chat_messages = []
            st.session_state.agent.reset_conversation()
            st.rerun()

        st.divider()

        st.subheader("🔧 사용 가능한 기능")
        st.markdown("""
        - **동기화 시작**: "USERS 테이블 동기화 해줘"
        - **상태 확인**: "현재 상태 알려줘"
        - **테이블 목록**: "어떤 테이블이 있어?"
        - **통계 조회**: "ORDERS 테이블 몇 건이야?"
        - **데이터 조회**: "USERS 테이블 보여줘"
        """)

        st.divider()

        st.subheader("📊 등록된 도구")
        tools = st.session_state.agent.tools.list_tools()
        for tool in tools:
            st.markdown(f"- `{tool}`")

    # Display chat history
    for msg in st.session_state.chat_messages:
        render_chat_message(msg["role"], msg["content"])

    # Chat input
    if prompt := st.chat_input("무엇을 도와드릴까요?"):
        # Display user message
        st.session_state.chat_messages.append({
            "role": "user",
            "content": prompt
        })
        render_chat_message("user", prompt)

        # Streaming 응답 처리
        response_text, tool_results = stream_agent_response(
            st.session_state.agent,
            prompt
        )

        if response_text:
            st.session_state.chat_messages.append({
                "role": "assistant",
                "content": response_text
            })

            # Show tool results if any (expandable)
            if tool_results:
                with st.expander("🔧 도구 실행 상세"):
                    for result in tool_results:
                        st.json(result)

        st.rerun()


if __name__ == "__main__":
    main()
