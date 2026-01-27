# 관리자/사용자 메뉴 분리 TODO

## 상태 표시
- [ ] 미완료
- [x] 완료
- [~] 진행 중

---

## Phase 1: 기반 구조 생성

### 1.1 라우터 시스템
- [x] `src/oracle_duckdb_sync/ui/router.py` 생성
  - [x] PageRouter 클래스 구현
  - [x] 라우트 등록 시스템
  - [x] 동적 페이지 로딩

### 1.2 네비게이션 컴포넌트
- [x] `src/oracle_duckdb_sync/ui/navigation.py` 생성
  - [x] render_sidebar_navigation() 함수
  - [x] 역할 기반 메뉴 필터링
  - [x] 현재 페이지 하이라이트
  - [x] 메뉴 확장/축소 상태 관리

### 1.3 세션 상태 확장
- [x] `src/oracle_duckdb_sync/ui/session_state.py` 수정
  - [x] current_page 상태 추가
  - [x] menu_expanded 상태 추가
  - [x] initialize_navigation_state() 함수 추가

---

## Phase 2: 사용자 페이지 분리

### 2.1 디렉토리 구조
- [x] `src/oracle_duckdb_sync/ui/pages/user/` 디렉토리 생성
- [x] `src/oracle_duckdb_sync/ui/pages/user/__init__.py` 생성

### 2.2 대시보드 페이지
- [x] `pages/user/dashboard.py` 생성
  - [x] 기본 대시보드 레이아웃
  - [x] 시스템 상태 요약
  - [x] 빠른 액션 버튼

### 2.3 데이터 조회 페이지
- [x] `pages/user/data_view.py` 생성
  - [x] app.py에서 데이터 조회 로직 분리
  - [x] 테이블 선택 UI
  - [x] 조회 모드 선택 (집계/상세)
  - [x] 데이터 그리드 표시

### 2.4 시각화 페이지
- [x] `pages/user/visualization.py` 생성
  - [x] app.py에서 시각화 로직 분리
  - [x] 차트 타입 선택
  - [x] 컬럼 선택 UI
  - [x] Plotly 차트 렌더링

### 2.5 AI 에이전트 페이지
- [x] `pages/user/agent_chat.py` 생성 (기존 파일 이동)
  - [x] 기존 agent_chat.py 내용 이동
  - [x] 경로 수정

---

## Phase 3: 관리자 페이지 재구성

### 3.1 디렉토리 구조
- [x] `src/oracle_duckdb_sync/ui/pages/admin/` 디렉토리 생성
- [x] `src/oracle_duckdb_sync/ui/pages/admin/__init__.py` 생성

### 3.2 동기화 관리 페이지
- [x] `pages/admin/sync.py` 생성
  - [x] app.py에서 동기화 관련 UI 분리
  - [x] 테스트 동기화 설정
  - [x] 전체 동기화 설정
  - [x] 동기화 상태 모니터링

### 3.3 기존 관리 페이지 이동
- [x] `admin_users.py` → `admin/users.py`
  - [x] 파일 이동
  - [x] import 경로 수정
- [x] `admin_menus.py` → `admin/menus.py`
  - [x] 파일 이동
  - [x] import 경로 수정
- [x] `admin_tables.py` → `admin/tables.py`
  - [x] 파일 이동
  - [x] import 경로 수정
- [ ] `admin_menus.py` → `admin/menus.py`
  - [ ] 파일 이동
  - [ ] import 경로 수정
- [ ] `admin_tables.py` → `admin/tables.py`
  - [ ] 파일 이동
  - [ ] import 경로 수정

---

## Phase 4: 통합 및 테스트

### 4.1 메인 진입점
- [x] `src/oracle_duckdb_sync/ui/main.py` 생성
  - [x] 페이지 설정 (set_page_config)
  - [x] 인증 체크
  - [x] 네비게이션 렌더링
  - [x] 라우터로 페이지 렌더링

### 4.2 기존 코드 정리
- [x] `app.py` 레거시 코드 제거 (이미 없음)
- [x] 사용하지 않는 import 제거
- [x] 기존 페이지 파일 삭제 (백업 후)

### 4.3 테스트
- [x] 로그인/로그아웃 테스트
- [x] 사용자 메뉴 접근 테스트
- [x] 관리자 메뉴 접근 테스트
- [x] 권한 없는 페이지 접근 시 차단 확인
- [x] 세션 상태 유지 확인

### 4.4 문서화
- [x] README 업데이트
- [x] 새 구조 다이어그램 추가 (UI_ARCHITECTURE.md)

---

## 추가 개선 사항

- [x] 브레드크럼 네비게이션 추가
- [x] 즐겨찾기 메뉴 기능
- [x] 최근 방문 페이지 표시
- [x] 메뉴 검색 기능
- [x] 키보드 단축키 지원

---

## 진행 로그

| 날짜 | 작업 내용 | 상태 |
|------|----------|------|
| 2026-01-27 | 계획 수립 및 문서 작성 | 완료 |
| 2026-01-27 | Phase 1: 기반 구조 생성 | 완료 |
| 2026-01-27 | Phase 2: 사용자 페이지 분리 | 완료 |
| 2026-01-27 | Phase 3: 관리자 페이지 재구성 | 완료 |
| 2026-01-27 | Phase 4.1: 메인 진입점 생성 | 완료 |
| 2026-01-27 | Phase 4.2: 기존 코드 정리 | 완료 |
| 2026-01-27 | Phase 4.3: 테스트 | 완료 |
| 2026-01-27 | Phase 4.4: 문서화 | 완료 |
| 2026-01-27 | 추가 개선 사항 구현 | 완료 |
