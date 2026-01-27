# Oracle-DuckDB 데이터 동기화 및 웹 시각화 시스템

## 1. 개요

Oracle 11g 데이터베이스의 대량 시계열/이력 데이터를 **DuckDB**로 고속 동기화하고, **Streamlit** 기반 웹 대시보드로 시각화/분석하는 시스템입니다. Oracle의 느린 조회 성능을 해결하고, AI 에이전트를 통한 자연어 인터페이스를 제공합니다.

### 주요 기능

| 기능 | 설명 | 기술 스택 |
|------|------|----------|
| **고속 데이터 동기화** | Oracle → DuckDB 전체/증분 동기화 (병렬 처리) | cx_Oracle, DuckDB |
| **역할 기반 대시보드** | 사용자/관리자 메뉴 자동 분리 (RBAC) | Streamlit, Python |
| **AI 에이전트** | 자연어로 동기화/조회 작업 자동화 (ReAct 패턴) | OpenAI GPT-4o-mini |
| **사용자 관리** | 계정 생성, 역할 관리 (ADMIN/USER/VIEWER) | SQLite, bcrypt |
| **향상된 UX** | 즐겨찾기, 최근 방문, 메뉴 검색, 키보드 단축키 | JavaScript, CSS |
| **데이터 시각화** | 인터랙티브 차트, 다운샘플링 (LTTB) | Plotly, Pandas |

### 시스템 특징

- 🚀 **고성능**: DuckDB의 컬럼 기반 저장으로 Oracle 대비 10배 빠른 조회
- 🤖 **AI 기반**: 자연어 명령으로 복잡한 데이터 작업 자동화
- 🔐 **보안**: 역할 기반 접근 제어 및 비밀번호 해싱 (bcrypt)
- 🎨 **직관적 UI**: 역할별 맞춤 메뉴 및 키보드 단축키
- 📊 **확장 가능**: Tool 기반 아키텍처로 새 기능 추가 용이

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
│   ├── config.py                     # 설정 로더
│   └── query_constants.py            # 쿼리 상수
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
│   ├── enhanced_query_service.py     # 향상된 쿼리 서비스
│   ├── query_cache_manager.py        # 쿼리 캐시 관리
│   ├── sync_service.py               # 동기화 서비스
│   └── ui_presenter.py               # UI 표시 추상 인터페이스
│
├── adapters/                         # Framework Adapters
│   ├── streamlit_adapter.py          # Streamlit UI 구현
│   ├── streamlit_cache.py            # Streamlit 캐싱 구현
│   ├── query_message_formatter.py    # 쿼리 메시지 포맷터
│   └── streamlit_query_presenter.py  # Streamlit 쿼리 프레젠터
│
├── auth/                             # 인증 및 권한
│   ├── models.py                     # User, UserRole 모델
│   ├── password.py                   # 비밀번호 해싱
│   ├── repository.py                 # 사용자 데이터 저장소
│   └── service.py                    # 인증 서비스
│
├── menu/                             # 메뉴 관리
│   ├── models.py                     # Menu 모델
│   ├── repository.py                 # 메뉴 데이터 저장소
│   └── service.py                    # 메뉴 서비스
│
├── table_config/                     # 테이블 설정
│   ├── models.py                     # TableConfig 모델
│   ├── repository.py                 # 테이블 설정 저장소
│   └── service.py                    # 테이블 설정 서비스
│
├── models/                           # 도메인 모델
│   └── sync_log.py                   # 동기화 로그 모델
│
├── repository/                       # 데이터 저장소
│   └── sync_log_repo.py              # 동기화 로그 저장소
│
├── ui/                               # Presentation Layer
│   ├── main.py                       # 메인 진입점 (역할 기반 메뉴)
│   ├── app.py                        # 레거시 앱 (하위 호환)
│   ├── router.py                     # 페이지 라우팅
│   ├── navigation.py                 # 네비게이션 컴포넌트
│   ├── components/                   # 재사용 가능한 UI 컴포넌트
│   │   ├── __init__.py
│   │   ├── breadcrumb.py             # 브레드크럼 네비게이션
│   │   ├── favorites.py              # 즐겨찾기 메뉴
│   │   ├── recent_pages.py           # 최근 방문 페이지
│   │   ├── search.py                 # 메뉴 검색
│   │   └── shortcuts.py              # 키보드 단축키
│   ├── pages/
│   │   ├── __init__.py
│   │   ├── login.py                  # 로그인 페이지
│   │   ├── user/                     # 사용자 페이지
│   │   │   ├── __init__.py
│   │   │   ├── dashboard.py          # 대시보드
│   │   │   ├── data_view.py          # 데이터 조회
│   │   │   ├── visualization.py      # 시각화
│   │   │   └── agent_chat.py         # AI 에이전트
│   │   └── admin/                    # 관리자 페이지
│   │       ├── __init__.py
│   │       ├── sync.py               # 동기화 관리
│   │       ├── users.py              # 사용자 관리
│   │       ├── menus.py              # 메뉴 관리
│   │       └── tables.py             # 테이블 설정
│   ├── handlers.py                   # UI 이벤트 핸들러
│   ├── session_state.py              # 세션 상태 관리
│   ├── ui_helpers.py                 # UI 헬퍼 함수
│   └── visualization.py              # 데이터 시각화 (공통)
│
├── database/                         # Data Access Layer
│   ├── oracle_source.py              # Oracle 연결
│   ├── duckdb_source.py              # DuckDB 연결
│   └── sync_engine.py                # 동기화 엔진
│
├── data/                             # Data Processing
│   ├── query.py                      # 쿼리 인터페이스
│   ├── query_builder.py              # 쿼리 빌더
│   ├── query_executor.py             # 쿼리 실행기
│   ├── query_core.py                 # UI 독립적 쿼리 함수
│   ├── converter.py                  # 데이터 변환 유틸리티
│   ├── type_converter_service.py     # 타입 변환 서비스
│   ├── incremental_loader.py         # 증분 데이터 로더
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
│   ├── check_versions.py             # 버전 확인
│   └── serialization.py              # 직렬화 유틸리티
│
└── log/
    ├── logger.py                     # 로깅 유틸리티
    └── log_stream.py                 # 로그 스트리밍
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

### 4.1 메인 애플리케이션

**권장 실행 방법** (Phase 04 완료 버전):
```bash
streamlit run src/oracle_duckdb_sync/ui/main.py
```

**레거시 버전** (하위 호환):
```bash
streamlit run src/oracle_duckdb_sync/ui/app.py
```

**주요 기능:**
- ✅ **역할 기반 메뉴**: ADMIN, USER, VIEWER 역할별 다른 메뉴
- ✅ **동적 라우팅**: 페이지 간 유연한 네비게이션
- ✅ **사용자 페이지**: 대시보드, 데이터 조회, 시각화, AI 에이전트
- ✅ **관리자 페이지**: 동기화 관리, 사용자 관리, 메뉴 관리, 테이블 설정

**향상된 UX (Phase 04):**
- 🔍 **메뉴 검색**: 키워드로 빠른 페이지 찾기 (사이드바)
- ⭐ **즐겨찾기**: 자주 사용하는 페이지 저장 및 빠른 접근
- 🕒 **최근 방문**: 최근 5개 페이지 히스토리 (타임스탬프 포함)
- ⌨️ **키보드 단축키**: 모든 주요 페이지에 단축키 지원 (아래 표 참조)
- 📍 **브레드크럼**: 현재 페이지 경로 시각적 표시
- 🎨 **반응형 UI**: 역할에 따른 메뉴 자동 조정

### 4.1.1 키보드 단축키 목록

| 단축키 | 기능 |
|--------|------|
| `Ctrl/Cmd + H` | 대시보드 |
| `Ctrl/Cmd + D` | 데이터 조회 |
| `Ctrl/Cmd + V` | 시각화 |
| `Ctrl/Cmd + A` | AI 에이전트 |
| `Ctrl/Cmd + S` | 동기화 관리 (관리자) |
| `Ctrl/Cmd + U` | 사용자 관리 (관리자) |
| `Ctrl/Cmd + M` | 메뉴 관리 (관리자) |
| `Ctrl/Cmd + T` | 테이블 설정 (관리자) |
| `Ctrl/Cmd + /` | 단축키 도움말 |

### 4.2 메뉴 구조

**📱 사용자 메뉴** (모든 로그인 사용자)

| 아이콘 | 메뉴 | 경로 | 설명 |
|--------|------|------|------|
| 🏠 | 대시보드 | `/dashboard` | 시스템 상태 요약, 최근 동기화 현황, 빠른 액션 |
| 📊 | 데이터 조회 | `/data` | 테이블 조회, 필터링, 정렬, 페이징 |
| 📈 | 시각화 | `/visualization` | 차트 및 그래프, 다운샘플링, 인터랙티브 분석 |
| 🤖 | AI 에이전트 | `/agent` | 자연어 명령 처리, 동기화/조회 자동화 |

**⚙️ 관리자 메뉴** (ADMIN 역할만)

| 아이콘 | 메뉴 | 경로 | 설명 |
|--------|------|------|------|
| 🔄 | 동기화 관리 | `/admin/sync` | 테스트/전체 동기화 실행, 로그 조회 |
| 👥 | 사용자 관리 | `/admin/users` | 계정 생성/수정/삭제, 역할 관리 |
| 📑 | 메뉴 관리 | `/admin/menus` | 메뉴 구조 편집, 순서 조정 |
| 🗄️ | 테이블 설정 | `/admin/tables` | 동기화 테이블 설정, 컬럼 매핑 |

**🔐 권한 시스템**

| 역할 | 사용자 메뉴 | 관리자 메뉴 | 동기화 실행 | 설정 변경 |
|------|------------|------------|------------|-----------|
| ADMIN | ✅ | ✅ | ✅ | ✅ |
| USER | ✅ | ❌ | ❌ | ❌ |
| VIEWER | ✅ (읽기 전용) | ❌ | ❌ | ❌ |

### 4.3 AI Agent 사용법

**메인 앱에서 접근** (권장):
```bash
streamlit run src/oracle_duckdb_sync/ui/main.py
# 로그인 후 사이드바에서 "🤖 AI 에이전트" 클릭
```

**직접 실행** (개발/테스트용):
```bash
streamlit run src/oracle_duckdb_sync/ui/pages/user/agent_chat.py
```

**지원 기능 (자연어):**

| 기능 분류 | 질문 예시 | 실행 Tool |
|-----------|-----------|-----------|
| **상태 조회** | "현재 동기화 상태 알려줘" | `get_sync_status` |
| **동기화 실행** | "USERS 테이블 동기화 해줘" | `start_sync` |
| **테이블 목록** | "어떤 테이블이 있어?" | `list_tables` |
| **통계 조회** | "IV 테이블 몇 건이야?" | `get_table_stats` |
| **데이터 조회** | "IV 테이블 최근 10건 보여줘" | `query_table` |

**AI Agent 아키텍처:**

```
┌──────────────┐
│  사용자 질문  │
└──────┬───────┘
       │
       ▼
┌──────────────┐     ┌─────────────┐
│ LLM 추론     │◄────│  대화 히스토리 │
│ (GPT-4o-mini)│     └─────────────┘
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Tool 선택    │
│ & 실행       │◄─── Tool Registry
└──────┬───────┘       (5개 도구)
       │
       ▼
┌──────────────┐
│ 결과 해석    │
│ & 응답 생성  │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ 자연어 응답  │
└──────────────┘
```

**ReAct 패턴**: 관찰(Observation) → 추론(Reasoning) → 행동(Action) → 반복

### 4.4 테스트

**단위 테스트**:
```bash
# 전체 테스트 실행
pytest -v

# 특정 모듈 테스트
pytest tests/agent/ -v                    # AI Agent 테스트
pytest tests/ui/ -v                       # UI 라우팅 테스트
pytest tests/auth/ -v                     # 인증 테스트

# 커버리지 리포트 (pytest-cov 필요)
pytest --cov=src/oracle_duckdb_sync --cov-report=html
```

**E2E 테스트** (실제 DB 연결 필요):
```bash
pytest tests/database/test_e2e.py -v
```

**UI 라우팅 테스트** (Phase 04):
```bash
python tests/test_ui_routing.py
# 11/11 테스트 통과 확인
```

### 4.5 코드 품질

**린팅** (Ruff):
```bash
# 검사만 실행
ruff check src/

# 자동 수정
ruff check src/ --fix

# 특정 파일만 검사
ruff check src/oracle_duckdb_sync/ui/
```

**타입 체킹** (Mypy):
```bash
# 전체 타입 검사
mypy src/oracle_duckdb_sync/

# 엄격 모드
mypy src/oracle_duckdb_sync/ --strict

# 특정 모듈만
mypy src/oracle_duckdb_sync/agent/
```

**코드 포맷팅** (Ruff format):
```bash
# 포맷팅 적용
ruff format src/

# 변경사항 미리보기
ruff format src/ --check
```

## 5. 주요 설계 원칙

### 5.1 아키텍처 원칙

1. **레이어드 아키텍처**: Presentation → Application → Domain 계층 분리
   - UI 레이어는 비즈니스 로직을 몰라도 됨
   - Application 레이어는 프레임워크 독립적
   - Domain 레이어는 순수 비즈니스 로직만 포함

2. **의존성 주입 (DI)**: AgentFactory를 통한 느슨한 결합
   - 서비스 간 의존성을 Factory가 관리
   - 테스트 시 Mock 객체로 쉽게 교체 가능
   - 설정 기반 서비스 생성

3. **역할 기반 접근 제어 (RBAC)**: 3단계 권한 시스템
   - ADMIN: 모든 기능 접근 및 관리
   - USER: 데이터 조회 및 AI 에이전트 사용
   - VIEWER: 읽기 전용 데이터 조회

4. **Tool 기반 확장성**: AI Agent는 Tool 추가로 기능 확장
   - BaseTool 상속으로 새로운 도구 구현
   - ToolRegistry에 등록하면 즉시 사용 가능
   - LLM이 적절한 도구를 자동 선택

### 5.2 코드 품질 원칙

1. **타입 힌팅**: 모든 함수/메서드에 타입 명시 (mypy 검사)
2. **린팅**: Ruff를 통한 코드 스타일 일관성 유지
3. **테스트**: 주요 비즈니스 로직에 대한 단위 테스트
4. **문서화**: docstring으로 모든 공개 API 문서화

### 5.3 UX 원칙

1. **직관적 네비게이션**: 브레드크럼, 즐겨찾기, 최근 방문
2. **키보드 우선**: 모든 주요 기능에 단축키 제공
3. **검색 우선**: 키워드로 빠르게 원하는 페이지 찾기
4. **역할 기반 UI**: 사용자에게 필요한 메뉴만 노출

## 6. 문서

### 구현 현황
| Phase | 설명 | 상태 | 문서 |
|-------|------|------|------|
| Phase 01 | 기본 동기화 엔진 | ✅ 완료 | [완료 보고서](docs/archive/IMPLEMENTATION_PHASE1_COMPLETE.md) |
| Phase 02 | UI 분리 및 서비스 레이어 | ✅ 완료 | [완료 보고서](docs/archive/IMPLEMENTATION_PHASE2_COMPLETE.md), [아키텍처](docs/archive/Phase%2002/architecture.md) |
| Phase 03 | AI Agent (OpenAI gpt-4o-mini) | ✅ 완료 | [계획서](docs/archive/Phase%2003/plan03.md) |
| Phase 04 | 역할 기반 메뉴 분리 및 UX 개선 | ✅ 완료 | [완료 보고서](docs/archive/PHASE_04_COMPLETION.md), [UI 아키텍처](docs/archive/UI_ARCHITECTURE.md) |

### 상세 문서
- **아키텍처**: [UI 아키텍처](docs/archive/UI_ARCHITECTURE.md), [UI 분리 전략](docs/archive/ui_separation_architecture.md)
- **API 레퍼런스**: [Phase 02 API](docs/archive/Phase%2002/api_reference.md)
- **프로젝트 관리**: [프로젝트 가이드](plan.md)
