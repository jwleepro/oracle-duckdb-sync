"""
AI Agent Chat Interface - Streamlit page for conversational AI.
"""
import re
from typing import Optional

import pandas as pd
import streamlit as st

from oracle_duckdb_sync.agent import SyncAgent
from oracle_duckdb_sync.agent.core.llm_client import LLMConfig
from oracle_duckdb_sync.agent.factory import AgentFactory
from oracle_duckdb_sync.config import load_config


def detect_markdown_table(text: str) -> bool:
    """마크다운 테이블 패턴이 있는지 감지합니다."""
    # 파이프(|)로 시작하고 끝나는 줄이 3줄 이상 연속으로 있으면 테이블
    table_pattern = r'(\|[^\n]+\|\n){3,}'
    return bool(re.search(table_pattern, text))


def parse_markdown_table(text: str) -> tuple[str, list[pd.DataFrame]]:
    """
    마크다운 텍스트에서 테이블을 추출하여 DataFrame 리스트로 변환합니다.
    
    Args:
        text: 마크다운 텍스트
        
    Returns:
        tuple: (테이블이 제거된 텍스트, DataFrame 리스트)
    """
    # TODO(human): 마크다운 테이블을 파싱하여 DataFrame으로 변환하는 로직 구현
    # 힌트: 
    # 1. 정규식으로 테이블 블록 추출 (|로 시작/끝나는 연속된 줄)
    # 2. 각 테이블에서 헤더 행, 구분자 행(---|---), 데이터 행 분리
    # 3. 파이프(|)로 split하여 각 셀 값 추출
    # 4. pd.DataFrame(data, columns=headers) 로 변환
    # 반환: (테이블이 제거된 텍스트, [DataFrame1, DataFrame2, ...])
    
    return text, []


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
    """Render a single chat message with table support."""
    with st.chat_message(role):
        if role == "assistant" and detect_markdown_table(content):
            remaining_text, dataframes = parse_markdown_table(content)
            if remaining_text.strip():
                st.markdown(remaining_text)
            for df in dataframes:
                st.dataframe(df, use_container_width=True)
        else:
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
                # 테이블 감지 및 렌더링
                if detect_markdown_table(full_text):
                    remaining_text, dataframes = parse_markdown_table(full_text)
                    text_placeholder.markdown(remaining_text if remaining_text.strip() else "")
                    for df in dataframes:
                        st.dataframe(df, use_container_width=True)
                else:
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


# Alias for router compatibility
render_agent_chat = main


if __name__ == "__main__":
    main()
