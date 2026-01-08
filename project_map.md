# 프로젝트 맵: oracle-duckdb-sync

## 한눈에 보기
- 목적: Oracle 11g 대용량 시계열/이력 데이터를 DuckDB로 동기화하고 Streamlit UI로 분석/시각화.
- 주요 UI 엔트리: `src/oracle_duckdb_sync/ui/app.py`.
- 아키텍처: UI/Adapter/Application/Data/Database/Scheduler/State 분리.
- 저장소: `data/sync.duckdb` (DuckDB 파일).

## 핵심 엔트리 포인트
- Streamlit 앱: `src/oracle_duckdb_sync/ui/app.py` (`main()`).
- 백그라운드 워커: `src/oracle_duckdb_sync/scheduler/sync_worker.py`.
- 동기화 엔진: `src/oracle_duckdb_sync/database/sync_engine.py`.
- 설정 로더: `src/oracle_duckdb_sync/config/config.py` (`load_config()`).
- 호환 레이어: `src/oracle_duckdb_sync/__init__.py` (대량 re-export).

## 동기화 흐름 (세부 호출 순서)
1) UI 트리거  
   - 버튼 클릭 → `handle_test_sync()` 또는 `handle_full_sync()`  
   - 파일: `src/oracle_duckdb_sync/ui/app.py`, `src/oracle_duckdb_sync/ui/handlers.py`
2) 락 및 파라미터 준비  
   - `_validate_table_name()` → `_acquire_sync_lock_with_ui()`  
   - 파일 락: `SyncLock` (`src/oracle_duckdb_sync/state/sync_state.py`, `data/sync.lock`)
3) 동기화 타입 결정 (full vs incremental)  
   - DuckDB 테이블 존재 여부로 분기  
   - incremental 시 마지막 동기화 시간 조회: `SyncEngine.load_state()`  
   - 파일: `src/oracle_duckdb_sync/ui/handlers.py`, `src/oracle_duckdb_sync/database/sync_engine.py`
4) 워커 시작  
   - `_start_sync_worker()` → `SyncWorker.start()`  
   - 진행률 큐 사용: `st.session_state.progress_queue`  
   - 파일: `src/oracle_duckdb_sync/ui/handlers.py`, `src/oracle_duckdb_sync/scheduler/sync_worker.py`, `src/oracle_duckdb_sync/ui/session_state.py`
5) 실제 동기화 실행  
   - `SyncWorker._run_sync()` → `SyncEngine.test_sync()` / `full_sync()` / `incremental_sync()`  
   - Oracle 스키마 조회: `OracleSource.get_table_schema()`  
   - 타입 매핑: `SyncEngine.map_oracle_type()`  
   - DuckDB 테이블 생성: `DuckDBSource.build_create_table_query()`  
   - 배치 처리: `OracleSource.fetch_batch()` → `DuckDBSource.insert_batch()`  
   - 파일: `src/oracle_duckdb_sync/database/oracle_source.py`, `src/oracle_duckdb_sync/database/duckdb_source.py`, `src/oracle_duckdb_sync/database/sync_engine.py`
6) 진행률 반영  
   - `SyncEngine._log_progress()` 호출 시 워커가 큐로 메시지 전송  
   - UI는 `check_progress()`가 큐를 소비하여 상태 업데이트  
   - 파일: `src/oracle_duckdb_sync/scheduler/sync_worker.py`, `src/oracle_duckdb_sync/ui/app.py`
7) 상태 저장  
   - 동기화 상태/스키마 매핑/부분 진행은 `StateFileManager`로 JSON 저장  
   - 파일: `src/oracle_duckdb_sync/state/file_manager.py`, `src/oracle_duckdb_sync/database/sync_engine.py`

## 조회/시각화 흐름 (세부 호출 순서)
### 공통: 테이블 목록/기본값/행 수
1) `get_available_tables()` → `determine_default_table_name()` → `get_table_row_count()`  
2) 파일: `src/oracle_duckdb_sync/data/query_core.py`, `src/oracle_duckdb_sync/ui/app.py`

### 집계 뷰 (빠른 로딩)
1) UI 선택 → `QueryService.query_table_aggregated_legacy()`  
2) 숫자 컬럼 자동 탐지 → `time_bucket()` 기반 집계 SQL 실행  
3) 결과를 `st.session_state.query_result`에 저장  
4) 시각화 렌더링: `render_data_visualization()` (집계 컬럼 리네임 포함)  
5) 파일: `src/oracle_duckdb_sync/application/query_service.py`, `src/oracle_duckdb_sync/ui/visualization.py`

### 상세 뷰 (레거시, Streamlit 의존)
1) UI 선택 → `query_duckdb_table_cached()`  
2) 세션 캐시 확인 → 증분 조회 가능 시 `_fetch_incremental_data()`  
3) 타입 변환: `detect_and_convert_types()`  
4) 캐시 병합 및 메타데이터 갱신  
5) 시각화: LTTB 다운샘플링 + 시간/값 필터 + Y축 범위 계산  
6) 파일: `src/oracle_duckdb_sync/data/query.py`, `src/oracle_duckdb_sync/data/converter.py`, `src/oracle_duckdb_sync/ui/visualization.py`

## 디렉터리 맵
### 루트
- `README.md`: 개요/설정/실행 가이드.
- `pyproject.toml`: 의존성/pytest 설정.
- `.env.example`: 환경변수 템플릿.
- `data/`: DuckDB 파일 및 상태/락 파일.
- `docs/`: 아키텍처/구현 요약 문서.
- `test/`: 테스트 코드.
- `validate_code.py`: 파이썬 파일 정적 검증 스크립트.

### `src/oracle_duckdb_sync/`
- `application/`: UI 독립 서비스 (`query_service.py`, `sync_service.py`, `cache_provider.py`, `ui_presenter.py`)
- `adapters/`: UI 프레임워크 어댑터 (`streamlit_adapter.py`, `streamlit_cache.py`)
- `ui/`: Streamlit UI (`app.py`, `handlers.py`, `session_state.py`, `visualization.py`, `ui_helpers.py`)
- `database/`: DB 연결 및 동기화 (`oracle_source.py`, `duckdb_source.py`, `sync_engine.py`)
- `data/`: 쿼리/변환/샘플링 (`query_core.py`, `query.py`, `converter.py`, `lttb.py`)
- `scheduler/`: 스케줄러/워커 (`scheduler.py`, `sync_worker.py`)
- `state/`: 락/상태 파일 관리 (`sync_state.py`, `file_manager.py`)
- `config/`: 설정 로더 (`config.py`)
- `log/`: 로거 (`logger.py`)

## 설정/런타임 아티팩트
- `.env` 기반 설정: `ORACLE_*`, `DUCKDB_*`, `SYNC_*`, `DUCKDB_TIME_COLUMN` 등.
- 상태 파일 위치: `data/` (config의 `*_path` 속성 참조).
- 락 파일: `data/sync.lock`.

## 테스트 포커스 맵
- 설정/환경: `test/config/test_config.py`, `test/config/test_imports.py`, `test/config/test_001.py`
- 애플리케이션 서비스: `test/application/test_cache_provider.py`, `test/application/test_query_service.py`
- 데이터 처리: `test/data/test_data_converter.py`, `test/data/test_selective_conversion.py`, `test/data/test_data_query.py`, `test/data/test_cached_query_v2.py`, `test/data/test_lttb.py`
- DB 계층: `test/database/test_duckdb_source.py`, `test/database/test_oracle_source.py`, `test/database/test_sync_engine.py`, `test/database/test_incremental_sync_run.py`
- E2E/실DB: `test/database/test_e2e.py` (실제 DB 연결 필요)
- 스케줄러/워커: `test/scheduler/test_scheduler.py`, `test/scheduler/test_sync_worker.py`
- 상태 관리: `test/state/test_sync_state.py`, `test/state/test_state_file_manager.py`, `test/state/test_schema_version.py`, `test/state/test_state_rollback.py`
- UI/시각화: `test/ui/test_ui.py`, `test/ui/test_streamlit_ui.py`, `test/ui/test_ui_handlers_refactoring.py`, `test/ui/test_visualization.py`
- 로깅/성능/자원 정리: `test/log/test_logger.py`, `test/performance/test_performance.py`, `test/performance/test_resource_cleanup.py`

## 참고/주의
- `src/oracle_duckdb_sync/data/query.py`는 Streamlit 의존(레거시)이며, `data/query_core.py`가 UI 독립 경로.
- `src/oracle_duckdb_sync/__init__.py`는 하위 모듈을 대량 re-export하여 하위 호환성을 제공합니다.
