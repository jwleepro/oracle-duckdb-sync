# 프로젝트 리뷰 보고서

**작성일**: 2025년 12월 19일
**검토 대상**: Oracle-DuckDB Sync 프로젝트

## 1. 개요
본 문서는 프로젝트의 소스 코드와 테스트 커버리지를 분석하여 서비스 가능한 구현 여부를 진단한 종합 보고서입니다. 1단계 정적 코드 분석과 2단계 테스트 실행 결과를 포함합니다.

## 2. 시스템 아키텍처 (System Architecture)

본 프로젝트는 Streamlit 기반의 UI와 Python 백엔드 로직이 결합된 형태입니다. Oracle 11g에서 데이터를 추출하여 로컬 DuckDB 파일로 적재하고, 이를 시각화합니다.

```mermaid
graph TD
    User([사용자 / 웹 브라우저]) -->|HTTP 요청| App[Streamlit App
(src/app.py)]
    
    subgraph "Application Layer"
        App -->|설정 로드| Config[설정 관리
(src/config.py)]
        App -->|동기화 요청| SyncEngine[동기화 엔진
(src/sync_engine.py)]
        App -->|데이터 조회| DuckSource[DuckDB 핸들러
(src/duckdb_source.py)]
    end
    
    subgraph "Data Layer"
        SyncEngine -->|배치 조회 (Select)| Oracle[(Oracle 11g DB)]
        SyncEngine -->|배치 삽입 (Insert)| DuckDB[(DuckDB 파일
.duckdb)]
        DuckSource -->|조회 (Select)| DuckDB
    end

    Config -.->|.env 파일| EnvFile[환경 변수]
```

## 3. 코드 분석 결과 (1단계: 정적 분석)

### 3.1 구조 및 디자인 패턴
*   **모듈화**: `app.py`(UI), `sync_engine.py`(비즈니스 로직), `oracle_source.py`/`duckdb_source.py`(데이터 접근 계층)로 역할이 잘 분리되어 있습니다.
*   **설정 관리**: `Config` 객체와 `.env` 파일 로딩 방식은 표준적입니다.
*   **리소스 관리**: Context Manager 패턴(`__enter__`, `__exit__`)을 사용하여 DB 연결 누수를 방지하고 있습니다.

### 3.2 치명적인 버그 (Critical Issues)
서비스 구동 시 런타임 에러를 유발하거나 정상적인 서비스를 불가능하게 하는 치명적인 버그들이 발견되었습니다.

**1. `incremental_sync` 함수 시그니처 및 호출 불일치**
*   **문제**: UI(`app.py`)에서 동기화 엔진을 호출하는 방식과 실제 엔진(`sync_engine.py`)의 정의가 다릅니다.
*   **분석**: `sync_engine.py`는 `last_value`(마지막 동기화 시점)를 인자로 요구하지만, `app.py`는 이를 전달하지 않고 `primary_key`를 전달하여 `TypeError`가 발생합니다.

**2. 초기 동기화(Full Sync) 진입 경로 부재**
*   **문제**: UI에는 "지금 동기화 실행" 버튼 하나뿐이며, 이는 무조건 증분 동기화(`incremental_sync`)를 호출합니다.
*   **영향**: 앱을 최초 실행하여 DuckDB 테이블이 없는 상태라면, 증분 동기화 내부의 `table_exists` 검사에서 실패하여 에러가 발생합니다. 초기 데이터 적재를 위한 `full_sync`를 UI에서 실행할 방법이 없습니다.

**3. Oracle 연결 초기화 누락 가능성**
*   **문제**: `SyncEngine.full_sync()`가 스키마 조회를 위해 `OracleSource.get_table_schema`를 호출할 때, 명시적인 `connect()` 호출이 보장되지 않아 연결 객체(`self.conn`)가 `None`일 경우 실패할 수 있습니다. (`fetch_batch` 등은 내부에서 `connect()`를 호출하지만 `get_table_schema`는 확인 필요)

## 4. 테스트 분석 결과 (2단계: 동적 분석)

### 4.1 테스트 실행 요약
*   **전체**: 46개 테스트
*   **결과**: ✅ 43개 통과 / ❌ **2개 실패** / 1개 제외(E2E)
*   **실패 원인**:
    *   `test_config.py`의 테스트들이 로컬 `.env` 파일의 간섭을 받아 환경 격리에 실패했습니다.

### 4.2 테스트 커버리지 및 사각지대
*   **커버리지 상태**:
    *   `OracleSource`, `DuckDBSource`는 단위 테스트가 잘 작성되어 있습니다.
*   **사각지대 (Blind Spots)**:
    *   **UI 통합**: `app.py`의 버튼 클릭 핸들러 로직에 대한 테스트가 전무하여, 위에서 언급한 시그니처 불일치 및 초기 동기화 경로 부재 문제를 사전에 발견하지 못했습니다.
    *   **대용량 E2E**: 200만 건 데이터에 대한 실제 동기화 테스트는 `LIMIT` 기능 부재로 실행하지 못했습니다.

## 5. 종합 평가 및 제안

*   **현재 상태**: 🔴 **서비스 불가 (Not Ready)**
    *   UI를 통한 초기 데이터 적재가 불가능하며, 증분 동기화 버튼 클릭 시 크래시가 발생합니다.
*   **개선 제안 (Action Plan)**:
    1.  **초기 동기화 로직 추가**: `app.py`에서 대상 테이블 존재 여부를 먼저 확인(`DuckDBSource.table_exists`)하고, 없으면 `full_sync`, 있으면 `last_value` 조회 후 `incremental_sync`를 호출하도록 분기 로직을 구현해야 합니다.
    2.  **버그 수정**: `SyncEngine`에 `get_last_sync_time` 추가 및 `app.py` 호출 시그니처 수정.
    3.  **안정성 강화**: `OracleSource.get_table_schema` 내부에 `connect()` 호출 보장 로직 추가.
    4.  **테스트 보완**: `test_config.py` 격리 문제 해결 및 `limit` 파라미터 추가.
