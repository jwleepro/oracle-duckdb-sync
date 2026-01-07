# UI 분리 아키텍처 구현 가이드

## 개요

이 문서는 oracle-duckdb-sync 프로젝트의 UI 프레임워크 독립성을 달성하기 위한 아키텍처 설계와 구현 방법을 설명합니다.

## 핵심 원칙

### 1. 의존성 역전 원칙 (Dependency Inversion Principle)

```
❌ 잘못된 의존성 방향:
Application Layer → UI Framework (Streamlit)

✅ 올바른 의존성 방향:
Application Layer → Abstract Interface ← UI Framework Adapter
```

### 2. 관심사 분리 (Separation of Concerns)

- **Presentation Layer**: UI 렌더링, 사용자 입력 처리
- **Application Layer**: 비즈니스 로직, 데이터 처리
- **Data Layer**: 데이터 접근, 쿼리 실행
- **Adapter Layer**: UI 프레임워크 구체 구현

## 아키텍처 레이어

### Layer 1: Abstract Interfaces (application/)

프레임워크 독립적인 추상 인터페이스를 정의합니다.

#### CacheProvider Interface

```python
# application/cache_provider.py
from abc import ABC, abstractmethod

class CacheProvider(ABC):
    """Framework-independent cache interface"""
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Get cached value"""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set cache value"""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all cache"""
        pass
```

**제공되는 구현체:**
- `InMemoryCacheProvider`: 테스트용 메모리 캐시
- `NoCacheProvider`: 캐싱 비활성화

#### UIPresenter Interface

```python
# application/ui_presenter.py
from abc import ABC, abstractmethod

class UIPresenter(ABC):
    """Framework-independent UI presentation interface"""
    
    @abstractmethod
    def show_message(self, context: MessageContext) -> None:
        """Display message to user"""
        pass
    
    @abstractmethod
    def show_progress(self, percentage: float, message: str) -> None:
        """Display progress indicator"""
        pass
```

### Layer 2: Framework Adapters (adapters/)

특정 UI 프레임워크의 구체적인 구현을 제공합니다.

#### StreamlitCacheProvider

```python
# adapters/streamlit_cache.py
import streamlit as st
from ..application.cache_provider import CacheProvider

class StreamlitCacheProvider(CacheProvider):
    """Streamlit-specific cache implementation"""
    
    def get(self, key: str) -> Optional[Any]:
        cache_key = f"cache_{key}"
        return st.session_state.get(cache_key)
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        cache_key = f"cache_{key}"
        st.session_state[cache_key] = value
    
    def cached_function(self, func: Callable, key_prefix: Optional[str] = None) -> Callable:
        """Use Streamlit's @st.cache_data decorator"""
        return st.cache_data(func)
```

#### StreamlitAdapter

```python
# adapters/streamlit_adapter.py
from ..application.ui_presenter import UIPresenter

class StreamlitPresenter(UIPresenter):
    """Streamlit-specific UI implementation"""
    
    def show_message(self, context: MessageContext) -> None:
        message_func = {
            'info': st.info,
            'warning': st.warning,
            'error': st.error,
            'success': st.success
        }.get(context.level, st.info)
        
        message_func(context.message)
```

### Layer 3: Application Services (application/)

UI 독립적인 비즈니스 로직을 제공합니다.

#### QueryService

```python
# application/query_service.py
class QueryService:
    """UI-independent query service"""
    
    def __init__(self, duckdb_source: DuckDBSource):
        self.duckdb_source = duckdb_source
    
    def query_table(self, table_name: str, limit: int = 10000) -> QueryResult:
        """Query table without UI dependencies"""
        # ... business logic ...
```

#### SyncService

```python
# application/sync_service.py
class SyncService:
    """UI-independent sync service"""
    
    def start_sync(self, sync_params: SyncParameters) -> bool:
        """Start synchronization without UI dependencies"""
        # ... business logic ...
```

### Layer 4: Data Layer (data/)

순수한 데이터 처리 로직을 제공합니다.

#### query_core.py (✅ UI 독립적)

```python
# data/query_core.py
def get_available_tables(duckdb: DuckDBSource) -> List[str]:
    """Get table list - NO UI dependencies"""
    try:
        tables = duckdb.execute("SELECT table_name FROM information_schema.tables")
        return [row[0] for row in tables]
    except Exception as e:
        logger.error(f"Failed to get tables: {e}")
        return []
```

#### query.py (⚠️ 레거시 - Streamlit 의존)

```python
# data/query.py - DEPRECATED
import streamlit as st  # ⛔ Direct dependency

@st.cache_data  # ⛔ Streamlit-specific
def _cached_convert_dataframe(...):
    pass
```

**마이그레이션 전략:**
- 새 코드는 `query_core.py` 사용
- 기존 코드는 `query.py` 유지 (backward compatibility)
- 점진적으로 `query.py` → `query_core.py` 마이그레이션

### Layer 5: UI Layer (ui/)

Streamlit 전용 UI 코드입니다.

```python
# ui/app.py
import streamlit as st
from oracle_duckdb_sync.adapters.streamlit_cache import StreamlitCacheProvider
from oracle_duckdb_sync.data.query_core import get_available_tables

# 🆕 Inject cache provider at startup
cache_provider = StreamlitCacheProvider()

def main():
    st.title("Dashboard")
    
    # Use UI-independent functions
    tables = get_available_tables(duckdb)
    st.info(f"Available tables: {tables}")
```

## 사용 방법

### 1. 새 코드 작성 시

#### ✅ 권장: UI 독립적 함수 사용

```python
# UI Layer (ui/app.py)
from oracle_duckdb_sync.data.query_core import (
    get_available_tables,
    query_table_with_conversion
)

# Use UI-independent functions
tables = get_available_tables(duckdb)
result = query_table_with_conversion(duckdb, "my_table", limit=1000)

# Display using Streamlit
if result['success']:
    st.dataframe(result['df_converted'])
else:
    st.error(result['error'])
```

#### ❌ 피해야 할 패턴

```python
# ❌ Don't import Streamlit in data layer
# data/my_module.py
import streamlit as st  # ⛔ Wrong!

def my_function():
    st.info("Processing...")  # ⛔ UI dependency in data layer
```

### 2. Application Service 사용

```python
# UI Layer
from oracle_duckdb_sync.application.query_service import QueryService

query_service = QueryService(duckdb)
result = query_service.query_table("my_table", limit=1000)

# Display result
if result.success:
    st.dataframe(result.data)
```

### 3. Adapter 사용

```python
# UI Layer
from oracle_duckdb_sync.adapters.streamlit_adapter import StreamlitAdapter

adapter = StreamlitAdapter()

# Use adapter instead of direct Streamlit calls
adapter.presenter.show_message(MessageContext(
    level='info',
    message='Processing complete'
))
```

## 프레임워크 전환 시나리오

### Streamlit → Flask 전환 예시

#### Step 1: Flask Adapter 구현

```python
# adapters/flask_adapter.py
from flask import flash, session
from ..application.cache_provider import CacheProvider

class FlaskCacheProvider(CacheProvider):
    """Flask-specific cache implementation"""
    
    def get(self, key: str) -> Optional[Any]:
        return session.get(f"cache_{key}")
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        session[f"cache_{key}"] = value
```

#### Step 2: Flask UI 작성

```python
# flask_app.py
from flask import Flask, render_template
from oracle_duckdb_sync.adapters.flask_adapter import FlaskCacheProvider
from oracle_duckdb_sync.data.query_core import get_available_tables

app = Flask(__name__)
cache_provider = FlaskCacheProvider()

@app.route('/')
def index():
    # ✅ Same business logic, different UI
    tables = get_available_tables(duckdb)
    return render_template('index.html', tables=tables)
```

**핵심**: `query_core.py`의 비즈니스 로직은 **전혀 수정하지 않고** 재사용!

## 테스트 전략

### 1. UI 독립적 테스트

```python
# test/data/test_query_core.py
from oracle_duckdb_sync.data.query_core import get_available_tables

def test_get_tables_no_ui_dependency():
    """Test without any UI framework"""
    duckdb = DuckDBSource(config)
    tables = get_available_tables(duckdb)
    
    assert isinstance(tables, list)
    # No Streamlit needed!
```

### 2. Adapter 테스트

```python
# test/adapters/test_streamlit_cache.py
from oracle_duckdb_sync.adapters.streamlit_cache import StreamlitCacheProvider

def test_cache_provider():
    provider = StreamlitCacheProvider()
    
    provider.set("key1", "value1")
    assert provider.get("key1") == "value1"
```

## 마이그레이션 체크리스트

### Phase 1: 캐싱 추상화 (완료 ✅)

- [x] `CacheProvider` 인터페이스 생성
- [x] `StreamlitCacheProvider` 구현
- [x] `ui/app.py`에서 캐시 프로바이더 주입
- [x] 문서 작성

### Phase 2: 레거시 코드 마이그레이션 (진행 중)

- [ ] `data/query.py`의 Streamlit 의존성 제거
- [ ] `ui/handlers.py`에서 `query_core` 사용
- [ ] `ui/visualization.py`에서 직접 Streamlit 호출 제거

### Phase 3: Service Layer 활용 강화

- [ ] `QueryService` 완전 구현
- [ ] `SyncService` 완전 구현
- [ ] UI Layer에서 Service 사용

## 참고 자료

- **Clean Architecture**: Robert C. Martin
- **Hexagonal Architecture**: Alistair Cockburn
- **Dependency Inversion Principle**: SOLID 원칙

## 문의

아키텍처 관련 질문이나 제안사항은 프로젝트 이슈에 등록해주세요.
