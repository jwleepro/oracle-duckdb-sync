# Phase 03: OpenAI AI Agent 구현 계획

## 개요
Oracle-DuckDB 동기화 프로젝트에 **OpenAI gpt-4o-mini** 기반 AI 에이전트를 추가하여, 사용자가 자연어 프롬프트로 동기화/조회/통계 기능을 실행할 수 있게 합니다.

## 요구사항 요약
- **모델**: gpt-4o-mini
- **UI**: 별도 Streamlit 페이지 (채팅 인터페이스)
- **기능**: 전체 Application Layer (동기화, 조회, 통계, 스케줄링)

---

## 1. 아키텍처

### 새로운 모듈 구조
```
src/oracle_duckdb_sync/
├── agent/                          # NEW: AI Agent 모듈
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── agent.py               # SyncAgent 메인 오케스트레이터
│   │   ├── llm_client.py          # OpenAI 클라이언트 래퍼
│   │   └── conversation.py        # 대화 히스토리 관리
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── base.py                # BaseTool 추상 클래스
│   │   ├── registry.py            # 도구 등록/관리
│   │   ├── sync_tools.py          # 동기화 도구들
│   │   ├── query_tools.py         # 쿼리 도구들
│   │   └── scheduler_tools.py     # 스케줄러 도구들
│   └── factory.py                 # 의존성 주입 팩토리
└── ui/
    └── pages/
        └── agent_chat.py          # Streamlit 채팅 페이지
```

---

## 2. 핵심 컴포넌트

### 2.1 LLMClient (`agent/core/llm_client.py`)
- OpenAI API 래퍼
- Function Calling 지원
- 에러 핸들링 (RateLimitError, APIConnectionError)

### 2.2 ConversationHistory (`agent/core/conversation.py`)
- 멀티턴 대화 관리
- OpenAI 메시지 포맷 변환
- 토큰 인식 truncation

### 2.3 SyncAgent (`agent/core/agent.py`)
- ReAct 패턴: Reason → Act → Observe
- Tool 호출 및 결과 처리
- 최종 응답 생성

### 2.4 ToolRegistry (`agent/tools/registry.py`)
- 동적 도구 등록/조회
- OpenAI 스키마 자동 생성

---

## 3. 구현할 도구 (Tools)

| 도구명 | 설명 | 연동 서비스 |
|--------|------|-------------|
| `start_sync` | 테이블 동기화 시작 | SyncService |
| `get_sync_status` | 동기화 상태 확인 | SyncService |
| `list_tables` | 테이블 목록 조회 | QueryService |
| `get_table_stats` | 테이블 통계 조회 | QueryService |
| `query_table` | 테이블 데이터 조회 | QueryService |
| `get_scheduler_status` | 스케줄러 상태 확인 | SyncScheduler |

---

## 4. 의존성 추가

**pyproject.toml**:
```toml
dependencies = [
    "openai>=1.0.0",  # NEW
]
```

**.env**:
```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

---

## 5. TDD 테스트 계획

### Phase: AI Agent Implementation

| 테스트 ID | 설명 | 상태 |
|-----------|------|------|
| TEST-300 | LLMClient 초기화 | |
| TEST-301 | LLMResponse 데이터클래스 | |
| TEST-302 | Conversation 메시지 추가 | |
| TEST-303 | Conversation OpenAI 포맷 변환 | |
| TEST-304 | BaseTool 스키마 생성 | |
| TEST-305 | ToolRegistry 등록 | |
| TEST-306 | ToolRegistry 스키마 수집 | |
| TEST-307 | StartSyncTool 실행 | |
| TEST-308 | GetSyncStatusTool 실행 | |
| TEST-309 | ListTablesTool 실행 | |
| TEST-310 | GetTableStatsTool 실행 | |
| TEST-311 | QueryTableTool 실행 | |
| TEST-312 | SyncAgent 단순 응답 | |
| TEST-313 | SyncAgent 단일 도구 호출 | |
| TEST-314 | SyncAgent 다중 도구 호출 | |
| TEST-315 | SyncAgent 에러 처리 | |

---

## 6. 구현 순서 (TDD)

### 단계 1: Core 인프라
1. `LLMConfig`, `LLMResponse` 데이터클래스
2. `LLMClient` (OpenAI 래퍼)
3. `Message`, `ConversationHistory`

### 단계 2: Tool 시스템
4. `BaseTool` 추상 클래스
5. `ToolRegistry`
6. `StartSyncTool`, `GetSyncStatusTool`
7. `ListTablesTool`, `GetTableStatsTool`, `QueryTableTool`

### 단계 3: Agent 통합
8. `SyncAgent` 메인 클래스
9. 도구 실행 및 응답 생성

### 단계 4: Streamlit UI
10. `agent_chat.py` 채팅 페이지
11. 세션 상태 관리
12. 통합 테스트

---

## 7. 핵심 수정 파일

| 파일 | 작업 |
|------|------|
| `src/oracle_duckdb_sync/agent/__init__.py` | 신규 생성 |
| `src/oracle_duckdb_sync/agent/core/__init__.py` | 신규 생성 |
| `src/oracle_duckdb_sync/agent/core/llm_client.py` | 신규 생성 |
| `src/oracle_duckdb_sync/agent/core/conversation.py` | 신규 생성 |
| `src/oracle_duckdb_sync/agent/core/agent.py` | 신규 생성 |
| `src/oracle_duckdb_sync/agent/tools/__init__.py` | 신규 생성 |
| `src/oracle_duckdb_sync/agent/tools/base.py` | 신규 생성 |
| `src/oracle_duckdb_sync/agent/tools/registry.py` | 신규 생성 |
| `src/oracle_duckdb_sync/agent/tools/sync_tools.py` | 신규 생성 |
| `src/oracle_duckdb_sync/agent/tools/query_tools.py` | 신규 생성 |
| `src/oracle_duckdb_sync/agent/factory.py` | 신규 생성 |
| `src/oracle_duckdb_sync/ui/pages/agent_chat.py` | 신규 생성 |
| `pyproject.toml` | openai 의존성 추가 |
| `.env` | OPENAI_API_KEY 추가 |

---

## 8. 검증 방법

### 단위 테스트
```bash
pytest test/agent/ -v
```

### 통합 테스트 (Streamlit)
```bash
streamlit run src/oracle_duckdb_sync/ui/pages/agent_chat.py
```

**테스트 시나리오:**
1. "현재 상태 알려줘" → `get_sync_status` 호출
2. "USERS 테이블 동기화 해줘" → `start_sync` 호출
3. "어떤 테이블이 있어?" → `list_tables` 호출
4. "ORDERS 테이블 몇 건이야?" → `get_table_stats` 호출

---

## 9. 설계 결정 사항

### Tool Registry 분리
- **테스트 용이성**: 개별 도구를 쉽게 Mock 가능
- **확장성**: Agent 수정 없이 새 도구 추가
- **Clean Architecture**: DIP(의존성 역전 원칙) 준수

### Lazy OpenAI Client
- **리소스 효율성**: 필요할 때만 클라이언트 생성
- **설정 유연성**: 초기화 후 API 키 설정 가능
- **테스트 용이성**: API 호출 없이 Mock 가능

### Message 기반 대화
- **OpenAI 호환**: API 포맷에 직접 매핑
- **유연성**: 도구 호출을 포함한 멀티턴 지원
- **상태 관리**: 세션 직렬화 용이

---

## 10. 예상 사용 흐름

```
User: "USERS 테이블 동기화 해줘"

Agent (Thought): 사용자가 'start_sync' 도구를 원함, 파라미터: {"table_name": "USERS"}

[System] 'USERS' 테이블 동기화 프로세스 시작 중...
[System] 동기화 완료: 150건 처리됨.

Agent: USERS 테이블 동기화를 시작했습니다. 총 150건의 데이터가 처리되었습니다.
```

---

## 참고: 예제 코드
### 기존 agent 예제 코드 : agent_demo.py

프로젝트에 이미 AI 에이전트 프로토타입(`agent_demo.py`)이 존재합니다.
현재는 키워드 매칭(`_simulate_llm_reasoning`)으로 의도를 파악하고 있으며,
이 부분을 **OpenAI API Function Calling**으로 교체하면 자연어 이해가 가능해집니다.

### Plan Mode, Opus에서 검토할 때 사용한 코드 : implement_example.md