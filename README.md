# Oracle-DuckDB 데이터 동기화 및 웹 시각화 시스템

## 1. 개요

본 프로젝트는 Oracle 11g 데이터베이스에 저장된 대량의 시계열/이력 데이터를 DuckDB로 고속 동기화하고, 웹 기반으로 데이터를 시각화 및 분석하는 시스템입니다. 기존 Oracle의 느린 조회 성능 문제를 해결하고, 사용자에게 직관적인 데이터 분석 환경을 제공하는 것을 목표로 합니다.

### 주요 기능

| 기능 | 설명 |
|------|------|
| **데이터 동기화** | Oracle → DuckDB 전체/증분 동기화 |
| **웹 시각화** | Streamlit 기반 대시보드 |
| **AI Agent** | 자연어로 동기화/조회 작업 수행 (GPT-4o-mini) |

## 2. 프로젝트 구조

### 2-1. 아키텍처 레이어

```
┌─────────────────────────────────────┐
│   Presentation Layer                │
│   - Streamlit Dashboard (ui/)       │
│   - AI Agent Chat (ui/pages/)       │
└─────────────────────────────────────┘
           ↓ uses
┌─────────────────────────────────────┐
│   AI Agent Layer                    │
│   - SyncAgent (ReAct 패턴)          │
│   - Tool Registry                   │
│   - LLM Client (OpenAI)             │
└─────────────────────────────────────┘
           ↓ uses
┌─────────────────────────────────────┐
│   Application Services              │
│   - QueryService                    │
│   - SyncService                     │
└─────────────────────────────────────┘
           ↓ uses
┌─────────────────────────────────────┐
│   Domain/Data Layer                 │
│   - DuckDBSource / OracleSource     │
│   - SyncEngine                      │
└─────────────────────────────────────┘
```

### 2-2. 디렉토리 구조

```
src/oracle_duckdb_sync/
├── config/                           # 환경 설정
│   └── config.py                     # 설정 로더
│
├── agent/                            # AI Agent Layer
│   ├── __init__.py
│   ├── factory.py                    # AgentFactory (의존성 주입)
│   ├── core/
│   │   ├── agent.py                  # SyncAgent (ReAct 패턴)
│   │   ├── llm_client.py             # OpenAI API 클라이언트
│   │   └── conversation.py           # 대화 히스토리 관리
│   └── tools/
│       ├── base.py                   # BaseTool, ToolResult
│       ├── registry.py               # ToolRegistry
│       ├── sync_tools.py             # StartSyncTool, GetSyncStatusTool
│       └── query_tools.py            # ListTablesTool, GetTableStatsTool, QueryTableTool
│
├── application/                      # Application Service Layer
│   ├── cache_provider.py             # 캐싱 추상 인터페이스
│   ├── query_service.py              # 데이터 조회 서비스
│   ├── sync_service.py               # 동기화 서비스
│   └── ui_presenter.py               # UI 표시 추상 인터페이스
│
├── adapters/                         # Framework Adapters
│   ├── streamlit_adapter.py          # Streamlit UI 구현
│   └── streamlit_cache.py            # Streamlit 캐싱 구현
│
├── ui/                               # Presentation Layer
│   ├── app.py                        # 메인 대시보드
│   ├── pages/
│   │   └── agent_chat.py             # AI Agent 채팅 UI
│   ├── handlers.py                   # UI 이벤트 핸들러
│   ├── session_state.py              # 세션 상태 관리
│   ├── ui_helpers.py                 # UI 헬퍼 함수
│   └── visualization.py              # 데이터 시각화
│
├── database/                         # Data Access Layer
│   ├── oracle_source.py              # Oracle 연결
│   ├── duckdb_source.py              # DuckDB 연결
│   └── sync_engine.py                # 동기화 엔진
│
├── data/                             # Data Processing
│   ├── query_core.py                 # UI 독립적 쿼리 함수
│   ├── converter.py                  # 데이터 변환 유틸리티
│   └── lttb.py                       # LTTB 다운샘플링
│
├── state/                            # 상태 관리
│   ├── sync_state.py                 # 동기화 상태 관리
│   └── file_manager.py               # 파일 기반 상태 저장
│
├── scheduler/                        # 스케줄러
│   ├── scheduler.py                  # APScheduler 래퍼
│   └── sync_worker.py                # 백그라운드 동기화 워커
│
├── util/                             # 유틸리티
│   └── check_versions.py             # 버전 확인
│
└── log/
    └── logger.py                     # 로깅 유틸리티
```

### 2-3. Import 방법

```python
# AI Agent
from oracle_duckdb_sync.agent import SyncAgent, AgentFactory, LLMConfig
from oracle_duckdb_sync.agent.tools import (
    StartSyncTool, GetSyncStatusTool,
    ListTablesTool, GetTableStatsTool, QueryTableTool
)

# Application Services
from oracle_duckdb_sync.application.query_service import QueryService
from oracle_duckdb_sync.application.sync_service import SyncService

# Data Layer
from oracle_duckdb_sync.database.duckdb_source import DuckDBSource
from oracle_duckdb_sync.database.sync_engine import SyncEngine
```

**Agent 사용 예시**:

```python
from oracle_duckdb_sync.agent import AgentFactory
from oracle_duckdb_sync.agent.core.llm_client import LLMConfig
from oracle_duckdb_sync.config import load_config

# Agent 생성
config = load_config()
llm_config = LLMConfig(model="gpt-4o-mini")
agent = AgentFactory.create_agent(config, llm_config)

# 자연어로 작업 수행
response = agent.process_message("USERS 테이블 동기화 해줘")
print(response.message)
```

## 3. 환경 설정

### 3.1 설치

```bash
# 의존성 설치
pip install -e .

# 개발 도구 포함 설치 (ruff, mypy, pytest-cov)
pip install -e ".[dev]"

# 환경 변수 파일 생성
copy .env.example .env  # Windows
cp .env.example .env    # Linux/Mac
```

### 3.2 환경 변수 설정

`.env` 파일을 편집하여 실제 값을 입력하세요:

**Oracle 연결:**
```env
ORACLE_HOST=your-oracle-host
ORACLE_PORT=1521
ORACLE_SERVICE_NAME=PROD
ORACLE_USER=sync_user
ORACLE_PASSWORD=your-password
```

**DuckDB 설정:**
```env
DUCKDB_PATH=./data/sync.duckdb
DUCKDB_LOCK_FILE=./data/sync.lock
DUCKDB_DATABASE=main
```

**동기화 대상 테이블:**
```env
SYNC_ORACLE_SCHEMA=SCHEMA_NAME
SYNC_ORACLE_TABLE=TABLE_NAME
SYNC_DUCKDB_TABLE=table_name
SYNC_PRIMARY_KEY=ID
# 증분 동기화용 Oracle 시간 컬럼 (복합 인덱스인 경우 쉼표로 구분)
SYNC_TIME_COLUMN=FACTORY, TRAN_TIME
# DuckDB 쿼리용 시간 컬럼 (설정하지 않으면 SYNC_TIME_COLUMN의 첫 번째 컬럼 사용)
DUCKDB_TIME_COLUMN=TRAN_TIME
```

**OpenAI (AI Agent 사용 시):**
```env
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL=gpt-4o-mini
```

### 3.3 보안 주의사항

- `.env` 파일은 `.gitignore`에 포함되어 있습니다
- API 키나 비밀번호를 코드에 하드코딩하지 마세요
- 화면 공유 시 `.env` 파일 노출에 주의하세요

## 4. 실행 방법

### 4.1 메인 대시보드

```bash
streamlit run src/oracle_duckdb_sync/ui/app.py
```

**기능:**
- 동기화 실행 및 상태 확인
- 데이터 조회 및 시각화
- CSV/Excel 다운로드

### 4.2 AI Agent 채팅

```bash
streamlit run src/oracle_duckdb_sync/ui/pages/agent_chat.py
```

**지원 명령 (자연어):**

| 질문 예시 | 실행 Tool |
|-----------|-----------|
| "현재 상태 알려줘" | `get_sync_status` |
| "USERS 테이블 동기화 해줘" | `start_sync` |
| "어떤 테이블이 있어?" | `list_tables` |
| "IV 테이블 몇 건이야?" | `get_table_stats` |
| "IV 테이블 보여줘" | `query_table` |

**AI Agent 아키텍처:**

```
사용자 질문 → LLM 추론 → Tool 선택 → 실행 → 결과 해석 → 자연어 응답
              ↑                              |
              └──────── ReAct Loop ──────────┘
```

### 4.3 테스트 실행

```bash
# 전체 테스트
pytest -v

# Agent 테스트만
pytest test/agent/ -v

# E2E 테스트 제외
pytest -v --ignore=test/database/test_e2e.py
```

### 4.4 코드 품질 검사

```bash
# Ruff 린트 검사
ruff check src/

# Ruff 자동 수정
ruff check src/ --fix

# Mypy 타입 검사
mypy src/oracle_duckdb_sync/
```

## 5. 주요 설계 원칙

1. **관심사 분리**: UI, 비즈니스 로직, 데이터 접근 레이어 분리
2. **의존성 주입**: AgentFactory를 통한 서비스 주입으로 테스트 용이성 확보
3. **프레임워크 독립성**: Application Layer는 UI 프레임워크에 의존하지 않음
4. **Tool 기반 확장**: 새로운 기능은 BaseTool 구현으로 쉽게 추가 가능

## 6. 문서

### 구현 현황
| Phase | 설명 | 상태 |
|-------|------|------|
| [Phase 01](docs/Phase%2001/plan01.md) | 기본 동기화 엔진 | ✅ 완료 |
| [Phase 02](docs/Phase%2002/plan02.md) | UI 분리 및 서비스 레이어 | ✅ 완료 |
| [Phase 03](docs/Phase%2003/plan03.md) | AI Agent (OpenAI gpt-4o-mini) | ✅ 완료 |

### 상세 문서
- [Phase 01 구현 완료 보고서](docs/archive/IMPLEMENTATION_PHASE1_COMPLETE.md)
- [Phase 02 구현 완료 보고서](docs/archive/IMPLEMENTATION_PHASE2_COMPLETE.md)
- [UI 분리 아키텍처](docs/archive/ui_separation_architecture.md)
- [프로젝트 전체 PRD](docs/prd_main.md)
