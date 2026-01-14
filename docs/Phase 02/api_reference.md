## API Reference - Phase 02

Phase 02에서 추가된 주요 모듈의 API 문서입니다.

---

## Auth Module

사용자 인증 및 권한 관리 모듈입니다.

### AuthService

사용자 인증, 계정 관리의 비즈니스 로직을 담당합니다.

#### `__init__(config: Config = None, duckdb_source: DuckDBSource = None)`

**Parameters**:
- `config`: 애플리케이션 설정 객체
- `duckdb_source`: DuckDB 소스 객체 (테스트용)

**Example**:
```python
from oracle_duckdb_sync.auth import AuthService
from oracle_duckdb_sync.config import Config

config = Config()
auth_service = AuthService(config=config)
```

#### `create_user(username: str, password: str, role: UserRole = UserRole.USER, enforce_strong_password: bool = True) -> Tuple[bool, str, Optional[User]]`

새 사용자를 생성합니다.

**Parameters**:
- `username`: 사용자명 (고유해야 함)
- `password`: 평문 비밀번호
- `role`: 사용자 역할 (기본값: USER)
- `enforce_strong_password`: 강한 비밀번호 강제 여부

**Returns**:
- `(성공 여부, 메시지, User 객체 또는 None)`

**Example**:
```python
success, message, user = auth_service.create_user(
    username="john_doe",
    password="SecurePass123",
    role=UserRole.USER
)

if success:
    print(f"User created: {user.username}")
else:
    print(f"Error: {message}")
```

#### `authenticate(username: str, password: str) -> Tuple[bool, str, Optional[User]]`

사용자 인증을 수행합니다.

**Parameters**:
- `username`: 사용자명
- `password`: 평문 비밀번호

**Returns**:
- `(인증 성공 여부, 메시지, User 객체 또는 None)`

**Example**:
```python
success, message, user = auth_service.authenticate("john_doe", "SecurePass123")

if success:
    print(f"Welcome, {user.username}!")
    print(f"Role: {user.role.value}")
else:
    print(f"Login failed: {message}")
```

#### `change_password(user_id: int, old_password: str, new_password: str, enforce_strong_password: bool = True) -> Tuple[bool, str]`

사용자 비밀번호를 변경합니다.

**Parameters**:
- `user_id`: 사용자 ID
- `old_password`: 기존 비밀번호
- `new_password`: 새 비밀번호
- `enforce_strong_password`: 강한 비밀번호 강제 여부

**Returns**:
- `(성공 여부, 메시지)`

#### `has_permission(user: User, permission: str) -> bool`

사용자의 권한을 확인합니다.

**Parameters**:
- `user`: 사용자 객체
- `permission`: 확인할 권한 (예: "sync:write", "user:read")

**Returns**:
- 권한 보유 여부

**Example**:
```python
if auth_service.has_permission(user, "sync:write"):
    # 동기화 실행 권한 있음
    start_sync()
else:
    print("권한이 없습니다")
```

### User Model

사용자 계정 데이터 클래스입니다.

**Attributes**:
- `id`: 사용자 고유 ID
- `username`: 로그인 ID
- `password_hash`: 해시된 비밀번호
- `role`: 사용자 역할 (UserRole enum)
- `is_active`: 활성화 여부
- `created_at`: 생성 시각
- `last_login`: 마지막 로그인 시각

**Methods**:
- `is_admin() -> bool`: 관리자 여부
- `can_manage_users() -> bool`: 사용자 관리 권한
- `can_sync() -> bool`: 동기화 실행 권한
- `to_dict() -> dict`: 딕셔너리로 변환 (비밀번호 제외)

### UserRole Enum

사용자 역할 열거형입니다.

**Values**:
- `ADMIN`: 관리자 (모든 권한)
- `USER`: 일반 사용자 (동기화 실행, 조회)
- `VIEWER`: 조회 전용

### Permission Constants

권한 상수입니다.

```python
# 동기화 관련
Permission.SYNC_READ = "sync:read"
Permission.SYNC_WRITE = "sync:write"
Permission.SYNC_DELETE = "sync:delete"

# 사용자 관리
Permission.USER_READ = "user:read"
Permission.USER_WRITE = "user:write"
Permission.USER_DELETE = "user:delete"

# 설정 관리
Permission.CONFIG_READ = "config:read"
Permission.CONFIG_WRITE = "config:write"

# 로그 조회
Permission.LOG_READ = "log:read"

# 관리자 전체 권한
Permission.ADMIN_ALL = "admin:*"
```

---

## Menu Module

권한 기반 메뉴 시스템 모듈입니다.

### MenuService

메뉴 필터링 및 관리 로직을 담당합니다.

#### `get_menus_for_user(user: User) -> List[Menu]`

사용자 권한에 맞는 메뉴를 조회합니다.

**Parameters**:
- `user`: 사용자 객체

**Returns**:
- 접근 가능한 Menu 리스트

**Example**:
```python
from oracle_duckdb_sync.menu import MenuService

menu_service = MenuService(config=config)
accessible_menus = menu_service.get_menus_for_user(user)

for menu in accessible_menus:
    print(f"{menu.icon} {menu.name} -> {menu.path}")
```

#### `get_menu_tree_for_user(user: User) -> List[dict]`

사용자 권한에 맞는 계층 구조의 메뉴 트리를 생성합니다.

**Returns**:
- 계층 구조의 메뉴 트리 (딕셔너리 리스트)

**Example**:
```python
menu_tree = menu_service.get_menu_tree_for_user(user)

# 예시 출력:
# [
#     {
#         "name": "관리자",
#         "path": "/admin",
#         "children": [
#             {"name": "사용자 관리", "path": "/admin/users", "children": []},
#             {"name": "메뉴 관리", "path": "/admin/menus", "children": []}
#         ]
#     }
# ]
```

#### `initialize_default_menus() -> int`

기본 메뉴를 초기화합니다.

**Returns**:
- 생성된 메뉴 수

**Example**:
```python
created_count = menu_service.initialize_default_menus()
print(f"{created_count}개의 기본 메뉴가 생성되었습니다")
```

### Menu Model

메뉴 데이터 클래스입니다.

**Attributes**:
- `id`: 메뉴 고유 ID
- `name`: 메뉴 표시 이름
- `path`: 메뉴 경로
- `icon`: 메뉴 아이콘
- `parent_id`: 상위 메뉴 ID
- `required_permission`: 필요한 권한
- `order`: 메뉴 정렬 순서
- `is_active`: 활성화 여부

**Methods**:
- `has_parent() -> bool`: 상위 메뉴 존재 여부
- `requires_permission() -> bool`: 권한이 필요한지 여부

---

## Table Config Module

멀티 테이블 동기화 설정 모듈입니다.

### TableConfigService

테이블 설정 관리 비즈니스 로직을 담당합니다.

#### `create_table_config(...) -> Tuple[bool, str, Optional[TableConfig]]`

새 테이블 설정을 생성합니다.

**Parameters**:
- `oracle_schema`: Oracle 스키마명
- `oracle_table`: Oracle 테이블명
- `duckdb_table`: DuckDB 테이블명
- `primary_key`: 기본 키 컬럼명
- `time_column`: 시간 컬럼명 (선택)
- `batch_size`: 배치 크기 (기본값: 10000)
- `description`: 설명 (선택)

**Returns**:
- `(성공 여부, 메시지, TableConfig 객체 또는 None)`

**Example**:
```python
from oracle_duckdb_sync.table_config import TableConfigService

table_service = TableConfigService(config=config)

success, message, table_config = table_service.create_table_config(
    oracle_schema="SCOTT",
    oracle_table="EMP",
    duckdb_table="emp",
    primary_key="EMPNO",
    time_column="MODIFIED_DATE",
    batch_size=5000
)

if success:
    print(f"설정 생성됨: {table_config.get_oracle_full_name()}")
```

#### `get_sync_targets() -> List[TableConfig]`

동기화가 활성화된 테이블 목록을 조회합니다.

**Returns**:
- 활성화된 TableConfig 리스트

**Example**:
```python
targets = table_service.get_sync_targets()

for table in targets:
    print(f"동기화 대상: {table.get_oracle_full_name()}")
    print(f"  → {table.duckdb_table} (배치 크기: {table.batch_size})")
```

#### `toggle_sync(config_id: int, enabled: bool) -> Tuple[bool, str]`

테이블 동기화를 활성화/비활성화합니다.

**Parameters**:
- `config_id`: 설정 ID
- `enabled`: 활성화 여부

**Returns**:
- `(성공 여부, 메시지)`

### TableConfig Model

테이블 동기화 설정 데이터 클래스입니다.

**Attributes**:
- `id`: 설정 고유 ID
- `oracle_schema`: Oracle 스키마명
- `oracle_table`: Oracle 테이블명
- `duckdb_table`: DuckDB 테이블명
- `primary_key`: 기본 키 컬럼명
- `time_column`: 증분 동기화용 시간 컬럼명
- `sync_enabled`: 동기화 활성화 여부
- `batch_size`: 배치 크기
- `description`: 테이블 설명

**Methods**:
- `get_oracle_full_name() -> str`: 스키마.테이블 형식 반환
- `has_time_column() -> bool`: 시간 컬럼 존재 여부
- `validate() -> Tuple[bool, str]`: 설정 유효성 검증

---

## Log Module

실시간 로그 스트리밍 모듈입니다.

### LogStreamHandler

Queue 기반 실시간 로그 핸들러입니다.

#### `__init__(max_size: int = 100, level: int = logging.INFO)`

**Parameters**:
- `max_size`: 저장할 최대 로그 수
- `level`: 최소 로그 레벨

**Example**:
```python
from oracle_duckdb_sync.log import get_log_stream_handler, attach_stream_handler_to_logger
import logging

# 전역 핸들러 가져오기
handler = get_log_stream_handler(max_size=200)

# 로거에 연결
logger = logging.getLogger('SyncEngine')
attach_stream_handler_to_logger('SyncEngine', max_size=200)
```

#### `get_logs(count: Optional[int] = None, level: Optional[str] = None) -> List[LogEntry]`

저장된 로그를 조회합니다.

**Parameters**:
- `count`: 조회할 로그 수
- `level`: 필터링할 로그 레벨

**Returns**:
- LogEntry 리스트

**Example**:
```python
# 최근 50개 로그 조회
logs = handler.get_logs(count=50)

# ERROR 레벨만 조회
errors = handler.get_logs(level="ERROR")

for log in logs:
    print(f"[{log.timestamp}] {log.level}: {log.message}")
```

### LogEntry Model

로그 엔트리 데이터 클래스입니다.

**Attributes**:
- `timestamp`: 로그 발생 시각
- `level`: 로그 레벨 (INFO, WARNING, ERROR, DEBUG)
- `source`: 로그 소스 (SyncEngine, SyncWorker 등)
- `message`: 로그 메시지
- `details`: 추가 상세 정보 (선택)

---

## Repository Module

동기화 이력 저장 모듈입니다.

### SyncLogRepository

동기화 로그 CRUD를 담당합니다.

#### `create(sync_log: SyncLog) -> SyncLog`

새 동기화 로그를 생성합니다.

**Example**:
```python
from oracle_duckdb_sync.repository import SyncLogRepository
from oracle_duckdb_sync.models import SyncLog, SyncStatus, SyncType
from datetime import datetime
import uuid

sync_log_repo = SyncLogRepository(config=config)

log = SyncLog(
    sync_id=str(uuid.uuid4()),
    table_name="SCOTT.EMP",
    sync_type=SyncType.FULL,
    status=SyncStatus.RUNNING,
    start_time=datetime.now()
)

created_log = sync_log_repo.create(log)
print(f"Log created with ID: {created_log.id}")
```

#### `get_recent_logs(limit: int = 50, table_name: Optional[str] = None) -> List[SyncLog]`

최근 로그를 조회합니다.

**Example**:
```python
# 최근 30개 로그
recent_logs = sync_log_repo.get_recent_logs(limit=30)

# 특정 테이블의 로그
emp_logs = sync_log_repo.get_recent_logs(limit=20, table_name="SCOTT.EMP")
```

#### `get_statistics(table_name: Optional[str] = None) -> dict`

동기화 통계를 조회합니다.

**Returns**:
- 통계 딕셔너리 (total, completed, failed, running, avg_rows, total_rows_synced)

**Example**:
```python
stats = sync_log_repo.get_statistics()
print(f"총 동기화 횟수: {stats['total']}")
print(f"성공: {stats['completed']}, 실패: {stats['failed']}")
print(f"평균 행 수: {stats['avg_rows']:.0f}")
```

### SyncLog Model

동기화 로그 데이터 클래스입니다.

**Attributes**:
- `id`: 로그 고유 ID
- `sync_id`: 동기화 작업 고유 ID (UUID)
- `table_name`: Oracle 테이블명
- `sync_type`: 동기화 유형 (test, full, incremental)
- `status`: 동기화 상태 (running, completed, failed, paused, stopped)
- `start_time`: 시작 시각
- `end_time`: 종료 시각
- `total_rows`: 처리된 총 행 수
- `error_message`: 에러 메시지

**Methods**:
- `get_duration_seconds() -> Optional[float]`: 소요 시간(초)
- `is_completed() -> bool`: 완료 여부
- `is_failed() -> bool`: 실패 여부
- `is_running() -> bool`: 실행 중 여부

---

## Usage Examples

### 완전한 인증 플로우

```python
from oracle_duckdb_sync.auth import AuthService, UserRole
from oracle_duckdb_sync.config import Config

# 1. 서비스 초기화
config = Config()
auth_service = AuthService(config=config)

# 2. 관리자 계정 생성
success, msg, admin = auth_service.create_user(
    username="admin",
    password="Admin123!",
    role=UserRole.ADMIN
)

# 3. 일반 사용자 로그인
success, msg, user = auth_service.authenticate("john_doe", "SecurePass123")

if success:
    # 4. 권한 확인
    if auth_service.has_permission(user, "sync:write"):
        print("동기화 권한 있음")

    # 5. 비밀번호 변경
    success, msg = auth_service.change_password(
        user.id,
        "SecurePass123",
        "NewSecurePass456"
    )
```

### 메뉴 시스템 통합

```python
from oracle_duckdb_sync.menu import MenuService

# 메뉴 서비스 초기화
menu_service = MenuService(config=config)

# 기본 메뉴 초기화
menu_service.initialize_default_menus()

# 사용자 권한에 맞는 메뉴 트리 가져오기
menu_tree = menu_service.get_menu_tree_for_user(user)

# Streamlit에서 메뉴 렌더링
for menu in menu_tree:
    st.sidebar.write(f"{menu['icon']} {menu['name']}")
    for child in menu['children']:
        st.sidebar.write(f"  - {child['name']}")
```

### 멀티 테이블 동기화

```python
from oracle_duckdb_sync.table_config import TableConfigService
from oracle_duckdb_sync.scheduler.sync_worker import SyncWorker

# 테이블 설정 서비스 초기화
table_service = TableConfigService(config=config)

# 활성화된 동기화 대상 가져오기
targets = table_service.get_sync_targets()

# 각 테이블에 대해 동기화 실행
for table in targets:
    sync_params = {
        'sync_type': 'full',
        'oracle_table': table.get_oracle_full_name(),
        'duckdb_table': table.duckdb_table,
        'primary_key': table.primary_key
    }

    worker = SyncWorker(config, sync_params, progress_queue)
    worker.start()
```
