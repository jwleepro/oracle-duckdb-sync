# Oracle-DuckDB 데이터 동기화 및 웹 시각화 시스템

## 1. 개요

본 프로젝트는 Oracle 11g 데이터베이스에 저장된 대량의 시계열/이력 데이터를 DuckDB로 고속 동기화하고, 웹 기반으로 데이터를 시각화 및 분석하는 시스템입니다. 기존 Oracle의 느린 조회 성능 문제를 해결하고, 사용자에게 직관적인 데이터 분석 환경을 제공하는 것을 목표로 합니다.

## 2. 환경 설정 (Configuration)

### 2.1 로컬 개발 환경 설정

**1단계: 환경 변수 파일 생성**

`.env.example` 파일을 `.env`로 복사:

```bash
# Windows PowerShell/CMD
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

**2단계: 실제 데이터베이스 접속 정보 입력**

`.env` 파일을 텍스트 에디터로 열어 실제 값으로 교체:

**Oracle 연결 정보:**
- `ORACLE_HOST`: Oracle 서버 주소
- `ORACLE_PORT`: Oracle 포트 (기본값: 1521)
- `ORACLE_SERVICE_NAME`: Oracle 서비스 이름
- `ORACLE_USER`, `ORACLE_PASSWORD`: Oracle 계정 정보

**DuckDB 설정:**
- `DUCKDB_PATH`: DuckDB 파일 경로 (기본값: ./data/sync.duckdb)
- `DUCKDB_DATABASE`: DuckDB 데이터베이스 이름 (기본값: main)

**동기화 대상 테이블 설정:**
- `SYNC_ORACLE_TABLE`: 동기화할 Oracle 원본 테이블명 (필수)
- `SYNC_DUCKDB_TABLE`: DuckDB 대상 테이블명 (선택, 비워두면 Oracle 테이블명을 소문자로 사용)
- `SYNC_PRIMARY_KEY`: Oracle 원본 테이블의 Primary Key 컬럼명. Primary Key가 Composite Key인 경우 콤마로 표현. ex) FACTORY LOT_ID
- `SYNC_TIME_COLUMN`: 증분 동기화용 Oracle 원본 테이블의 시간 컬럼명. Composite NON UNIQUE INDEX인 경우 콤마로 표현. ex) FACTORY, TRAN_TIME

**예시:**
```env
ORACLE_HOST=mydb.company.com
ORACLE_PORT=1521
ORACLE_SERVICE_NAME=PROD
ORACLE_USER=sync_user
ORACLE_PASSWORD=SecureP@ssw0rd

DUCKDB_PATH=./data/sync.duckdb
DUCKDB_DATABASE=main

SYNC_ORACLE_TABLE=TRANSACTION_LOG
SYNC_DUCKDB_TABLE=transaction_log
SYNC_PRIMARY_KEY=TRANS_ID
SYNC_TIME_COLUMN=TRAN_TIME
```

**3단계: 설정 확인**

```bash
# 설정이 제대로 로드되는지 테스트
pytest test/test_config.py -v
```

### 2.2 보안 주의사항

⚠️ **중요**: `.env` 파일은 절대 git에 커밋하지 마세요!

- `.env` 파일은 이미 `.gitignore`에 포함되어 있습니다
- `git status`로 `.env`가 추적되지 않는지 확인하세요
- 실제 비밀번호나 접속 정보를 코드에 하드코딩하지 마세요
- 화면 공유 시 `.env` 파일이 노출되지 않도록 주의하세요

### 2.3 E2E 테스트 실행

실제 DB 연결로 E2E 테스트 실행:

```bash
# E2E 테스트 (실제 DB 연결 필요)
pytest test/test_e2e.py::test_131_incremental_sync_e2e_real_db -v

# 전체 테스트 실행
pytest -v
```

### 2.4 Streamlit UI 실행

**1단계: Oracle Instant Client 설치 (Windows)**

Oracle 11g 연결을 위해 Oracle Instant Client가 필요합니다:

1. [Oracle Instant Client 다운로드](https://www.oracle.com/database/technologies/instant-client/downloads.html)
2. Windows용 64-bit Basic 패키지 다운로드
3. `D:\instantclient_23_0`에 압축 해제 (또는 원하는 경로)
4. `src/oracle_duckdb_sync/oracle_source.py`에서 경로 확인:
   ```python
   lib_dir = os.environ.get('ORACLE_HOME') or r'D:\instantclient_23_0'
   ```

**2단계: Streamlit 앱 실행**

```bash
# Windows PowerShell/CMD
streamlit run src/oracle_duckdb_sync/ui/app.py

# 브라우저가 자동으로 열리며 http://localhost:8501 에서 확인 가능
```

**프로젝트 구조**:

프로젝트는 2단계 디렉토리 구조로 구성되어 있습니다:

```
src/oracle_duckdb_sync/
├── config.py, logger.py          # 루트: 공통 설정 및 로거
├── ui/                            # UI 및 Streamlit 컴포넌트
│   ├── app.py                     # 메인 Streamlit 앱
│   ├── handlers.py                # UI 이벤트 핸들러
│   ├── session_state.py           # Streamlit 세션 상태 관리
│   └── visualization.py           # 데이터 시각화
├── database/                      # 데이터베이스 연결 및 동기화
│   ├── oracle_source.py           # Oracle 연결
│   ├── duckdb_source.py           # DuckDB 연결
│   └── sync_engine.py             # 동기화 엔진
├── scheduler/                     # 스케줄링 및 백그라운드 작업
│   ├── scheduler.py               # 작업 스케줄러
│   └── sync_worker.py             # 백그라운드 워커
├── data/                          # 데이터 처리 및 쿼리
│   ├── converter.py               # 타입 변환
│   ├── query.py                   # DuckDB 쿼리
│   └── lttb.py                    # LTTB 다운샘플링
└── state/                         # 상태 관리
    ├── sync_state.py              # 동기화 상태 및 락
    └── file_manager.py            # 파일 I/O 관리
```

**Import 방법**:

새로운 코드 작성 시 다음과 같이 import하세요:

```python
# 권장: 명시적 경로 사용
from oracle_duckdb_sync.database.sync_engine import SyncEngine
from oracle_duckdb_sync.data.query import query_duckdb_table
from oracle_duckdb_sync.ui.handlers import handle_test_sync

# 하위 호환성: 기존 코드도 동작
from oracle_duckdb_sync import SyncEngine, query_duckdb_table
```

**3단계: UI 사용법**

1. **동기화 실행**:
   - 좌측 사이드바에서 "지금 동기화 실행" 버튼 클릭
   - `.env`에 설정된 테이블이 자동으로 사용됨
   - 또는 "수동 설정 사용" 체크박스로 테이블명 직접 입력

2. **데이터 조회 및 시각화**:
   - 동기화된 데이터를 DuckDB에서 조회
   - 기간 필터, 정렬, 차트 렌더링 등 다양한 기능 제공
   - CSV/Excel 다운로드 지원

3. **동기화 상태 확인**:
   - 동기화 로그 및 상태를 UI에서 실시간 확인
   - 마지막 동기화 시간 및 처리된 행 수 표시

**주의사항**:
- 첫 실행 시 Oracle → DuckDB로 전체 데이터 동기화가 필요합니다 (수십 분 소요 가능)
- 이후부터는 증분 동기화로 빠르게 업데이트됩니다
- TEST-131에서 확인된 성능: 약 200만 행 기준 5분, 초당 약 7,000 rows 처리

## 3. 배경 및 문제 정의

Oracle 11g에 대량의 시계열 데이터가 축적되면서 웹 애플리케이션에서 기간별 데이터 조회 시 응답 속도가 현저히 저하되는 문제가 발생했습니다. 이는 사용자 경험 저하뿐만 아니라 효율적인 데이터 분석 및 의사결정을 어렵게 만들었습니다.

## 4. 목표

*   **비즈니스 목표**: 데이터 조회 응답 시간을 기존 대비 10배 이상 향상시키고, 직관적인 웹 기반 데이터 시각화 환경을 제공하여 통계 분석 기반 의사결정을 지원합니다.
*   **기술 목표**: Oracle 데이터를 고속 분석 DB인 DuckDB로 마이그레이션하는 파이프라인을 구축하고, 일별 증분 데이터를 자동으로 동기화하는 시스템을 구현합니다.
