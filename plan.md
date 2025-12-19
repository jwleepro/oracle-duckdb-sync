# Phase 01 개발 계획: Oracle-DuckDB 데이터 동기화/분석 대시보드
TDD(Test-Driven Development) 방식으로 Phase 01을 구현하기 위한 테스트 계획입니다. 각 테스트는 체크박스로 관리하며, 순차적으로 진행합니다.

## 기술 스택
- **언어/런타임**: Python 3.9+
- **데이터 소스**: Oracle 11g (python-oracledb)
- **분석 DB**: DuckDB (duckdb>=1.0.0)
- **스케줄러**: APScheduler
- **UI/시각화**: Streamlit, Plotly
- **테스트 러너**: pytest

---

## 1. 로컬 환경/기본 설정

### 1.1 개발 환경 점검
- [x] **TEST-001**: pytest 기본 실행 확인
- [x] **TEST-002**: python-oracledb import 가능
- [x] **TEST-003**: duckdb import 가능
- [x] **TEST-004**: Streamlit/Plotly import 가능

---

## 2. 환경 설정(Config)

### 2.1 설정 로드
- [x] **TEST-010**: .env에서 Oracle 연결 정보(host, port, service_name, user, password) 로드
- [x] **TEST-011**: .env에서 DuckDB 연결 정보(path, database) 로드
- [x] **TEST-012**: 필수 설정 누락 시 명확한 오류 메시지 반환
- [x] **TEST-013**: 기본 옵션(DuckDB 기본 database명 등) 적용 검증

---

## 3. Oracle 데이터 소스

### 3.1 연결/풀
- [x] **TEST-020**: Oracle DB 연결 객체 생성
- [x] **TEST-021**: 연결 실패 시 예외/로그 처리
- [x] **TEST-022**: 커넥션 풀 초기화·획득·반환 동작

### 3.2 데이터 조회
- [x] **TEST-030**: 지정 테이블 전체 조회(fetchall/fetchmany)
- [x] **TEST-031**: 배치 단위 조회(fetchmany) 동작 확인
- [x] **TEST-032**: TRAN_TIME 기준 증분 조회
- [x] **TEST-033**: NULL/DATE 컬럼 ISO 문자열 변환 처리

---

## 4. DuckDB 분석 DB

### 4.1 연결/스키마
- [x] **TEST-040**: DuckDB health check/ping
- [x] **TEST-041**: 데이터베이스·테이블 없을 경우 생성
- [x] **TEST-042**: 컬럼 타입 매핑 검증(수치/문자/날짜 등)

### 4.2 적재/검증
- [x] **TEST-050**: 배치 INSERT 성공 및 행 수 검증
- [x] **TEST-051**: 증분 시 중복 키에 대한 upsert/중복 방지 처리

---

## 5. 동기화 엔진

### 5.1 Full Sync
- [x] **TEST-070**: Oracle 전체 추출 → DuckDB 적재 파이프라인
- [x] **TEST-071**: 진행률·로그 기록 검증
- [x] **TEST-072**: 대량 데이터 배치/청크 처리 동작

### 5.2 Incremental Sync
- [x] **TEST-080**: 마지막 동기화 시각 이후 데이터 조회
- [x] **TEST-081**: 증분 데이터 upsert 처리(중복 방지)
- [x] **TEST-082**: 실패 시 재시도·백오프(최소 3회)
- [x] **TEST-083**: 재시작 시 마지막 성공 지점부터 이어서 처리

---

## 6. 모니터링/로그
- [x] **TEST-100**: 동기화 실행/완료/실패 로그 기록
- [x] **TEST-101**: 처리 건수·지연 시간 통계 기록
- [x] **TEST-102**: 로그 레벨 설정(예: DEBUG/INFO/WARN/ERROR)

---

## 7. 스케줄러
- [x] **TEST-110**: APScheduler로 매일 02:00 증분 동기화 트리거
- [x] **TEST-111**: 중복 실행 방지(락/플래그) 동작
- [x] **TEST-112**: 스케줄 재등록/중단 시 안전 처리

---

## 8. UI/조회(Streamlit)
- [x] **TEST-120**: 기간/조건 필터 적용 후 DuckDB 조회
- [x] **TEST-121**: 테이블 뷰 정렬·필터·컬럼 토글·CSV/Excel 다운로드
- [x] **TEST-122**: 차트 렌더링(라인/바/에어리어/파이·도넛/산점도/히스토그램/박스플롯)
- [x] **TEST-123**: 기준선(상/하한, 평균, 중앙값, ±σ 밴드, 목표선, 추세선) 표시
- [x] **TEST-124**: 동기화 상태·로그 UI 노출

---

## 9. End-to-End 및 성능 검증
- [x] **TEST-130**: 초기 Full Sync E2E(Oracle → DuckDB → UI 조회)
- [x] **TEST-131**: 일일 증분 동기화 E2E 및 상태 업데이트
- [x] **TEST-132**: 10만 행 차트 렌더링 성능 < 1초(목표)
- [x] **TEST-133**: 1만 건 증분 동기화 < 1분(목표)

---

## 10. 상태/메타데이터 관리
- [ ] **TEST-140**: sync_state 저장·로드
- [ ] **TEST-141**: 스키마/매핑 설정 버전 관리
- [ ] **TEST-142**: 실패 시 상태 롤백·재시작 가능
