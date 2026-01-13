# AI Agent Streaming 응답 구현 계획

## 목표
AI Agent의 응답 방식을 동기식(blocking)에서 **streaming** 방식으로 변경하여 사용자 경험 개선

## 현재 vs 목표

| 항목 | 현재 | 목표 |
|------|------|------|
| 응답 방식 | 전체 완료 후 한번에 표시 | 실시간 토큰 단위 표시 |
| UI 피드백 | `st.spinner("🤔 생각 중...")` | 타이핑 효과 + 도구 상태 표시 |
| 도구 호출 | 완료까지 무응답 | 실행 중 상태 실시간 표시 |

### 사용자 경험 비교

**Before (현재)**
```
[사용자 입력] -> [🤔 생각 중... (10초 대기)] -> [전체 응답 한번에 표시]
```

**After (구현 후)**
```
[사용자 입력] -> [실시간 텍스트 표시▌]
              -> [🔧 도구 호출 중: get_table_stats]
              -> [🔧 실행 중: get_table_stats]
              -> [실시간 결과 해석 표시▌]
              -> [완료]
```

---

## 구현 단계

### 1단계: LLMClient Streaming 메서드 추가
**파일**: `src/oracle_duckdb_sync/agent/core/llm_client.py`

- `StreamChunk` dataclass 추가 (type: content/tool_call_start/tool_call_delta/done)
- `chat_completion_stream()` 메서드 추가 (`stream=True` 옵션 사용)
- 기존 `chat_completion()` 유지 (하위 호환성)

### 2단계: SyncAgent Streaming 처리
**파일**: `src/oracle_duckdb_sync/agent/core/agent.py`

- `StreamingAgentChunk` dataclass 추가 (type: text/tool_status/tool_result/error/done)
- `process_message_stream()` 메서드 추가 (Generator 반환)
- `_stream_llm_response()` 헬퍼 메서드 (도구 호출 시 재귀 처리)
- 기존 `process_message()` 유지 (하위 호환성)

### 3단계: Streamlit UI 수정
**파일**: `src/oracle_duckdb_sync/ui/pages/agent_chat.py`

- `stream_agent_response()` 함수 추가
- `st.empty()` placeholder로 실시간 텍스트 업데이트
- 도구 실행 상태 별도 표시 영역
- `main()` 함수 응답 처리 부분 수정

### 4단계: Export 업데이트
**파일**: `src/oracle_duckdb_sync/agent/__init__.py`

- 새 클래스들 export 추가

---

## 수정 파일 목록

| 파일 | 수정 내용 |
|------|----------|
| `agent/core/llm_client.py` | `StreamChunk`, `chat_completion_stream()` 추가 |
| `agent/core/agent.py` | `StreamingAgentChunk`, `process_message_stream()` 추가 |
| `ui/pages/agent_chat.py` | `stream_agent_response()` 추가, UI 렌더링 수정 |
| `agent/__init__.py` | 새 클래스 export |

---

## 구현 순서 (의존성)

```
llm_client.py (StreamChunk, chat_completion_stream)
    ↓
agent.py (StreamingAgentChunk, process_message_stream)
    ↓
agent/__init__.py (export)
    ↓
agent_chat.py (UI 수정)
```

---

## OpenAI Streaming Tool Calls 주의사항

OpenAI의 streaming 응답에서 tool_calls는 일반 텍스트와 다르게 처리됩니다:

- `delta.tool_calls[i].id` - 최초 청크에만 존재
- `delta.tool_calls[i].function.name` - 최초 청크에만 존재
- `delta.tool_calls[i].function.arguments` - 점진적 누적 (JSON 문자열이 조각나서 옴)
- 여러 tool_calls가 동시에 streaming될 수 있음 (index로 구분)

따라서 버퍼를 사용해 각 tool_call의 arguments를 누적해야 합니다.

---

## 검증 방법

1. **단위 테스트**: streaming 응답 청크 확인
   ```bash
   pytest test/agent/test_llm_client.py -v
   ```

2. **통합 테스트**: 도구 호출 포함 시나리오
   ```bash
   pytest test/agent/test_agent.py -v
   ```

3. **수동 테스트**: Streamlit UI에서 실시간 표시 확인
   ```bash
   streamlit run src/oracle_duckdb_sync/ui/pages/agent_chat.py
   ```

4. **하위 호환성**: 기존 `process_message()` 정상 동작 확인

---

## 아키텍처 다이어그램

### 현재 흐름
```
User Input -> agent_chat.py -> SyncAgent.process_message()
           -> LLMClient.chat_completion() -> OpenAI API (동기)
           -> 전체 응답 반환 -> UI 렌더링
```

### 새로운 흐름
```
User Input -> agent_chat.py -> SyncAgent.process_message_stream()
           -> LLMClient.chat_completion_stream() -> OpenAI API (stream=True)
           -> Generator[StreamChunk] -> st.empty() 실시간 렌더링
           -> tool_calls 감지 시 도구 실행 -> 재귀적 streaming
```

---

## 참고 자료

- [OpenAI Streaming API Documentation](https://platform.openai.com/docs/api-reference/streaming)
- [Streamlit st.write_stream](https://docs.streamlit.io/develop/api-reference/write-magic/st.write_stream)
