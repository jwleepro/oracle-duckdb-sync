# Oracle-DuckDB Sync 프로젝트 가이드

## 📋 프로젝트 현황

### 완료된 단계
- ✅ **Phase 01**: 기본 동기화 엔진 구축
- ✅ **Phase 02**: UI 분리 및 서비스 레이어 아키텍처
- ✅ **Phase 03**: AI Agent (OpenAI GPT-4o-mini) 통합
- ✅ **Phase 04**: 역할 기반 메뉴 분리 및 UX 개선

### 현재 시스템 특징

**🏗️ 아키텍처**
- 레이어드 아키텍처 (Presentation → Application → Domain)
- 역할 기반 접근 제어 (RBAC): ADMIN, USER, VIEWER
- 의존성 주입 패턴 (AgentFactory)
- 프레임워크 독립적인 비즈니스 로직

**🎨 사용자 인터페이스**
- 역할별 동적 메뉴 시스템
- 향상된 UX: 즐겨찾기, 최근 방문, 검색, 키보드 단축키
- Streamlit 기반 웹 대시보드
- 브레드크럼 네비게이션

**🤖 AI 기능**
- 자연어 기반 데이터 조회 및 동기화
- ReAct 패턴 기반 에이전트
- 도구 기반 확장 가능 아키텍처

---

## 🔧 유지보수 가이드

### 1. 새로운 사용자 페이지 추가

```python
# 1. 페이지 파일 생성
# src/oracle_duckdb_sync/ui/pages/user/new_page.py

import streamlit as st
from oracle_duckdb_sync.auth import require_auth, User

@require_auth
def render_new_page(user: User):
    \"\"\"새로운 페이지 렌더링\"\"\"
    st.title("🆕 새로운 페이지")
    # 페이지 로직 구현
```

```python
# 2. 라우터에 등록
# src/oracle_duckdb_sync/ui/router.py

def _register_default_routes(self):
    # 기존 라우트...
    self.register('/new-page', 'pages.user.new_page', 'render_new_page')
```

```python
# 3. 네비게이션에 추가
# src/oracle_duckdb_sync/ui/navigation.py

def _render_user_menus(self):
    self._render_menu_items([
        # 기존 메뉴...
        {'icon': '🆕', 'name': '새로운 페이지', 'path': '/new-page'},
    ])
```

### 2. 새로운 관리자 페이지 추가

동일한 프로세스를 `pages/admin/` 디렉토리와 `_render_admin_menus()`에서 수행합니다.

### 3. 권한 시스템 확장

```python
# src/oracle_duckdb_sync/auth/models.py

class User:
    def can_do_something(self) -> bool:
        \"\"\"새로운 권한 체크\"\"\"
        return self.role in [UserRole.ADMIN, UserRole.USER]
```

### 4. AI Agent 도구 추가

```python
# src/oracle_duckdb_sync/agent/tools/my_tools.py

from oracle_duckdb_sync.agent.tools.base import BaseTool, ToolResult

class MyNewTool(BaseTool):
    @property
    def name(self) -> str:
        return "my_new_tool"

    @property
    def description(self) -> str:
        return "새로운 도구 설명"

    def execute(self, **kwargs) -> ToolResult:
        # 도구 로직 구현
        return ToolResult(success=True, message="완료")
```

```python
# src/oracle_duckdb_sync/agent/factory.py

def _register_default_tools(self):
    # 기존 도구...
    self.registry.register(MyNewTool(...))
```

---

## 🚀 향후 개선 사항

### Phase 05: 성능 최적화 (제안)
- [ ] DuckDB 쿼리 최적화 (인덱싱, 파티셔닝)
- [ ] 대용량 데이터 스트리밍 처리
- [ ] 캐싱 전략 고도화 (Redis 통합)
- [ ] 비동기 동기화 작업 큐 (Celery)

### Phase 06: 모니터링 및 알림 (제안)
- [ ] 동기화 실패 알림 (이메일/Slack)
- [ ] 시스템 상태 대시보드 (Prometheus + Grafana)
- [ ] 쿼리 성능 프로파일링
- [ ] 에러 추적 시스템 (Sentry)

### Phase 07: 보안 강화 (제안)
- [ ] 2FA (이중 인증)
- [ ] API 키 관리 시스템
- [ ] 감사 로그 (Audit Trail)
- [ ] 데이터 암호화 (저장/전송)

### Phase 08: 협업 기능 (제안)
- [ ] 쿼리 공유 및 즐겨찾기
- [ ] 대시보드 공유
- [ ] 팀 워크스페이스
- [ ] 댓글 및 주석 기능

---

## 📚 참고 문서

### 아키텍처 문서
- [UI 아키텍처](docs/archive/UI_ARCHITECTURE.md)
- [Phase 02 아키텍처](docs/archive/Phase%2002/architecture.md)
- [UI 분리 전략](docs/archive/ui_separation_architecture.md)

### 완료 보고서
- [Phase 01 완료](docs/archive/IMPLEMENTATION_PHASE1_COMPLETE.md)
- [Phase 02 완료](docs/archive/IMPLEMENTATION_PHASE2_COMPLETE.md)
- [Phase 04 완료](docs/archive/PHASE_04_COMPLETION.md)

### API 레퍼런스
- [Phase 02 API](docs/archive/Phase%2002/api_reference.md)

---

## 🛠️ 트러블슈팅

### 일반적인 문제

**1. 동기화 실패**
```bash
# 로그 확인
tail -f logs/sync.log

# DuckDB 연결 테스트
python -c "from oracle_duckdb_sync.database import DuckDBSource; DuckDBSource().test_connection()"
```

**2. 페이지 라우팅 오류**
- `router.py`의 라우트 등록 확인
- 페이지 함수 시그니처 확인: `def render_xxx(user: User)`
- `@require_auth` 데코레이터 확인

**3. 권한 오류**
- 사용자 역할 확인: `st.session_state.user.role`
- 권한 메서드 확인: `user.is_admin()`, `user.can_sync()`

**4. AI Agent 오류**
- OpenAI API 키 확인: `.env`의 `OPENAI_API_KEY`
- 도구 등록 확인: `ToolRegistry`에 도구가 등록되었는지
- LLM 응답 로그 확인

### 개발 환경 재설정

```bash
# 가상환경 재생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 재설치
pip install -e ".[dev]"

# 환경 변수 확인
cp .env.example .env
# .env 파일 편집

# 테스트 실행
pytest -v

# 애플리케이션 실행
streamlit run src/oracle_duckdb_sync/ui/main.py
```

---

## 📞 지원

- **이슈 리포팅**: GitHub Issues
- **문서**: `docs/` 디렉토리
- **코드 리뷰**: Pull Request 템플릿 사용
