# FastAPI 백엔드 구축 계획

## 개요
기존 Streamlit 기반 Oracle-DuckDB Sync 애플리케이션에 FastAPI 백엔드를 추가합니다.
기존 서비스 레이어(QueryService, SyncService, SyncAgent)를 그대로 재사용하며, REST API와 WebSocket 엔드포인트를 제공합니다.

## 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                   FastAPI Application                    │
├─────────────────────────────────────────────────────────┤
│  REST API (/api/v1)          │  WebSocket               │
│  - /tables                   │  - /ws/agent (채팅)      │
│  - /sync                     │  - /ws/sync/progress     │
│  - /scheduler                │                          │
├─────────────────────────────────────────────────────────┤
│                Dependencies (Depends)                    │
│  QueryService │ SyncService │ SyncAgent │ Scheduler     │
│             (기존 서비스 레이어 재사용)                   │
└─────────────────────────────────────────────────────────┘
```

## 폴더 구조

```
src/oracle_duckdb_sync/api/
├── __init__.py
├── main.py                    # FastAPI 앱 생성
├── dependencies.py            # 의존성 주입 (Depends)
├── schemas/                   # Pydantic 모델
│   ├── __init__.py
│   ├── common.py              # APIResponse, ErrorResponse
│   ├── table.py               # 테이블 스키마
│   ├── sync.py                # 동기화 스키마
│   ├── scheduler.py           # 스케줄러 스키마
│   └── agent.py               # Agent 스키마
├── routers/                   # REST 라우터
│   ├── __init__.py
│   ├── tables.py              # GET/POST /tables
│   ├── sync.py                # POST /sync/start, GET /sync/status
│   └── scheduler.py           # 스케줄 관리
└── websocket/                 # WebSocket 핸들러
    ├── __init__.py
    ├── connection_manager.py  # 연결 관리
    ├── agent_handler.py       # Agent 채팅
    └── sync_handler.py        # 진행상황 브로드캐스트
```

## API 엔드포인트

### REST API

| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/v1/tables` | 테이블 목록 |
| GET | `/api/v1/tables/{name}/stats` | 테이블 통계 |
| POST | `/api/v1/tables/{name}/query` | 테이블 조회 |
| POST | `/api/v1/tables/{name}/aggregate` | 시계열 집계 |
| POST | `/api/v1/sync/start` | 동기화 시작 |
| GET | `/api/v1/sync/status` | 동기화 상태 |
| POST | `/api/v1/sync/reset` | 상태 초기화 |
| GET | `/api/v1/scheduler/status` | 스케줄러 상태 |
| POST | `/api/v1/scheduler/jobs` | 작업 등록 |
| GET | `/health` | 헬스체크 |

### WebSocket

| Path | 설명 |
|------|------|
| `/ws/agent` | AI Agent 채팅 (양방향 스트리밍) |
| `/ws/sync/progress` | 동기화 진행상황 (서버 → 클라이언트) |

## 구현 단계

### Phase 1: 기반 구조 (schemas, dependencies)
- [ ] `api/__init__.py` - 패키지 초기화
- [ ] `api/schemas/common.py` - APIResponse, ErrorResponse
- [ ] `api/schemas/table.py` - 테이블 관련 스키마
- [ ] `api/schemas/sync.py` - 동기화 관련 스키마
- [ ] `api/schemas/scheduler.py` - 스케줄러 스키마
- [ ] `api/schemas/agent.py` - Agent/WebSocket 스키마
- [ ] `api/dependencies.py` - 의존성 주입

### Phase 2: REST API 라우터
- [ ] `api/routers/__init__.py`
- [ ] `api/routers/tables.py` - 테이블 조회 API
- [ ] `api/routers/sync.py` - 동기화 API
- [ ] `api/routers/scheduler.py` - 스케줄러 API

### Phase 3: WebSocket
- [ ] `api/websocket/__init__.py`
- [ ] `api/websocket/connection_manager.py` - 연결 관리
- [ ] `api/websocket/sync_handler.py` - 진행상황 브로드캐스트
- [ ] `api/websocket/agent_handler.py` - Agent 채팅

### Phase 4: 통합 및 설정
- [ ] `api/main.py` - FastAPI 앱 팩토리
- [ ] `pyproject.toml` - fastapi, uvicorn 의존성 추가

## 주요 파일 참조

| 기존 파일 | 용도 |
|----------|------|
| `application/query_service.py` | REST API 구현 시 메서드 참조 |
| `application/sync_service.py` | 동기화 API, Queue→WebSocket 변환 |
| `agent/core/agent.py` | `process_message_stream()` WebSocket 연동 |
| `agent/factory.py` | 의존성 주입 패턴 참조 |
| `scheduler/scheduler.py` | 스케줄러 API 구현 |

## 의존성 추가

```toml
# pyproject.toml
dependencies = [
    # 기존 의존성 유지...
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "websockets>=12.0",
]
```

## 실행 방법

```bash
# 개발 서버
uvicorn oracle_duckdb_sync.api.main:app --reload --port 8000

# API 문서
# http://localhost:8000/docs (Swagger UI)
# http://localhost:8000/redoc (ReDoc)
```

## 검증 방법

1. **REST API 테스트**
   ```bash
   # 헬스체크
   curl http://localhost:8000/health

   # 테이블 목록
   curl http://localhost:8000/api/v1/tables

   # 동기화 시작
   curl -X POST http://localhost:8000/api/v1/sync/start \
     -H "Content-Type: application/json" \
     -d '{"oracle_table": "TEST_TABLE", "sync_type": "test", "row_limit": 100}'
   ```

2. **WebSocket 테스트** (wscat 사용)
   ```bash
   # Agent 채팅
   wscat -c ws://localhost:8000/ws/agent
   > {"type": "chat", "content": "테이블 목록 보여줘"}

   # 동기화 진행상황
   wscat -c ws://localhost:8000/ws/sync/progress
   ```

3. **Swagger UI**
   - http://localhost:8000/docs 에서 모든 API 인터랙티브 테스트

## 기존 Streamlit과 공존

- FastAPI와 Streamlit은 별도 포트에서 동시 실행 가능
- 동일한 서비스 레이어를 공유하므로 상태 일관성 유지
- 점진적으로 Streamlit → 새 프론트엔드로 마이그레이션 가능
