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
- `SYNC_PRIMARY_KEY`: Primary Key 컬럼명 (기본값: ID)
- `SYNC_TIME_COLUMN`: 증분 동기화용 시간 컬럼명 (기본값: TRAN_TIME)

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
pytest test/test_e2e.py::test_130_full_sync_e2e -v

# 전체 테스트 실행
pytest -v
```

## 3. 배경 및 문제 정의

Oracle 11g에 대량의 시계열 데이터가 축적되면서 웹 애플리케이션에서 기간별 데이터 조회 시 응답 속도가 현저히 저하되는 문제가 발생했습니다. 이는 사용자 경험 저하뿐만 아니라 효율적인 데이터 분석 및 의사결정을 어렵게 만들었습니다.

## 4. 목표

*   **비즈니스 목표**: 데이터 조회 응답 시간을 기존 대비 10배 이상 향상시키고, 직관적인 웹 기반 데이터 시각화 환경을 제공하여 통계 분석 기반 의사결정을 지원합니다.
*   **기술 목표**: Oracle 데이터를 고속 분석 DB인 DuckDB로 마이그레이션하는 파이프라인을 구축하고, 일별 증분 데이터를 자동으로 동기화하는 시스템을 구현합니다.
