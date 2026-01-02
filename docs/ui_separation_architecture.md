# UI 분리 아키텍처

## 목표

UI 프레임워크(Streamlit)에 대한 의존성을 제거하여 다른 프레임워크로 쉽게 교체할 수 있도록 함.

## 레이어 구조

```
┌─────────────────────────────────────┐
│   Presentation Layer (UI)           │
│   - Streamlit App (현재)            │
│   - Flask App (미래)                │
│   - CLI (미래)                       │
└─────────────────────────────────────┘
           ↓ (uses)
┌─────────────────────────────────────┐
│   Adapters                          │
│   - StreamlitAdapter                │
│   - FlaskAdapter (미래)             │
└─────────────────────────────────────┘
           ↓ (implements)
┌─────────────────────────────────────┐
│   Application Service Layer         │
│   - QueryService                    │
│   - SyncService                     │
│   - UI Presenter Interface          │
└─────────────────────────────────────┘
           ↓ (uses)
┌─────────────────────────────────────┐
│   Domain/Data Layer                 │
│   - DuckDBSource                    │
│   - OracleSource                    │
│   - DataConverter                   │
│   - SyncEngine                      │
└─────────────────────────────────────┘
```

## 주요 컴포넌트

### 1. Application Layer
- **query_service.py**: 데이터 조회 비즈니스 로직
- **sync_service.py**: 동기화 비즈니스 로직
- **ui_presenter.py**: UI 인터페이스 정의 (추상)

### 2. Adapters
- **streamlit_adapter.py**: Streamlit 구현체
- UI Presenter, SessionStateManager, LayoutManager 구현

### 3. Data Layer (기존)
- **query_core.py**: UI 독립적 쿼리 함수
- 기존 data/query.py는 deprecated (backward compatibility)

## 마이그레이션 전략

### Phase 1: 새 레이어 추가 (완료)
- ✅ Application Service Layer 생성
- ✅ UI Presenter 인터페이스 정의
- ✅ Streamlit Adapter 구현
- ✅ query_core.py 생성 (UI 독립적)

### Phase 2: 점진적 마이그레이션 (현재)
1. query_core.py 사용으로 전환
2. handlers.py를 SyncService 사용으로 전환
3. app.py에서 adapter 사용

### Phase 3: 레거시 제거 (미래)
- 기존 query.py deprecated 표시
- 모든 UI 코드를 adapter 통해 접근
- 직접 st.* 호출 제거

## 사용 예시

### Before (기존)
```python
# handlers.py
import streamlit as st
from oracle_duckdb_sync.data.query import query_duckdb_table

def handle_query():
    result = query_duckdb_table(duckdb, table)
    st.dataframe(result['df'])
```

### After (새 방식)
```python
# handlers.py
from oracle_duckdb_sync.application.query_service import QueryService
from oracle_duckdb_sync.adapters.streamlit_adapter import StreamlitAdapter

def handle_query():
    adapter = StreamlitAdapter()
    service = QueryService(duckdb_source)
    
    result = service.query_table(table)
    if result.success:
        adapter.presenter.show_dataframe(result.data)
```

## 장점

1. **프레임워크 독립성**: Streamlit 외 다른 UI로 쉽게 교체
2. **테스트 용이성**: UI 없이 비즈니스 로직 테스트 가능
3. **유지보수성**: 관심사 분리로 코드 이해 쉬움
4. **확장성**: 새 기능 추가 시 레이어별 독립 작업

## 다음 단계

1. app.py에서 query_core 사용
2. handlers.py에서 SyncService 사용
3. 점진적으로 st.* 직접 호출 제거
4. 테스트 작성
