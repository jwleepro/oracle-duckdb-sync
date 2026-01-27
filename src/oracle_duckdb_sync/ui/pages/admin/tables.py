"""
테이블 설정 관리 페이지

관리자가 동기화 테이블 설정을 관리하는 페이지입니다.
"""

import streamlit as st

from oracle_duckdb_sync.config import load_config
from oracle_duckdb_sync.log.logger import setup_logger
from oracle_duckdb_sync.table_config import TableConfig, TableConfigService
from oracle_duckdb_sync.ui.pages.login import require_auth

# Logger 설정
logger = setup_logger('AdminTablesPage')


@require_auth(required_permission="config:write")
def render_admin_tables_page():
    """테이블 설정 관리 페이지 렌더링"""
    st.title("🗄️ 테이블 설정 관리")

    # 설정 및 서비스 초기화
    config = load_config()
    table_service = TableConfigService(config=config)

    # 탭 구성
    tab1, tab2, tab3 = st.tabs(["📋 테이블 목록", "➕ 테이블 추가", "⚙️ 환경변수 가져오기"])

    with tab1:
        render_table_list(table_service)

    with tab2:
        render_create_table_form(table_service)

    with tab3:
        render_import_from_env(table_service, config)


def render_table_list(table_service: TableConfigService):
    """테이블 목록 렌더링"""
    st.subheader("동기화 테이블 목록")

    # 필터 옵션
    show_disabled = st.checkbox("비활성 테이블 표시", value=False)

    # 테이블 목록 조회
    tables = table_service.get_all_configs(enabled_only=not show_disabled)

    if not tables:
        st.info("등록된 테이블 설정이 없습니다.")
        return

    # 테이블 목록 표시
    for table in tables:
        status_icon = '🟢' if table.sync_enabled else '🔴'

        with st.expander(f"{status_icon} {table.get_oracle_full_name()} → {table.duckdb_table}"):
            col1, col2 = st.columns(2)

            with col1:
                st.markdown(f"**테이블 ID**: {table.id}")
                st.markdown(f"**Oracle 스키마**: {table.oracle_schema}")
                st.markdown(f"**Oracle 테이블**: {table.oracle_table}")
                st.markdown(f"**DuckDB 테이블**: {table.duckdb_table}")

            with col2:
                st.markdown(f"**기본 키**: {table.primary_key}")
                st.markdown(f"**시간 컬럼**: {table.time_column or '없음'}")
                st.markdown(f"**배치 크기**: {table.batch_size:,}")
                st.markdown(f"**동기화 상태**: {'활성' if table.sync_enabled else '비활성'}")

            if table.description:
                st.markdown(f"**설명**: {table.description}")

            # 수정 폼
            st.markdown("---")
            st.markdown("##### 테이블 설정 수정")

            with st.form(f"edit_table_{table.id}"):
                col1, col2 = st.columns(2)

                with col1:
                    new_oracle_schema = st.text_input(
                        "Oracle 스키마",
                        value=table.oracle_schema,
                        key=f"edit_schema_{table.id}"
                    )
                    new_oracle_table = st.text_input(
                        "Oracle 테이블",
                        value=table.oracle_table,
                        key=f"edit_oracle_{table.id}"
                    )
                    new_duckdb_table = st.text_input(
                        "DuckDB 테이블",
                        value=table.duckdb_table,
                        key=f"edit_duckdb_{table.id}"
                    )

                with col2:
                    new_primary_key = st.text_input(
                        "기본 키",
                        value=table.primary_key,
                        key=f"edit_pk_{table.id}"
                    )
                    new_time_column = st.text_input(
                        "시간 컬럼",
                        value=table.time_column,
                        key=f"edit_time_{table.id}"
                    )
                    new_batch_size = st.number_input(
                        "배치 크기",
                        value=table.batch_size,
                        min_value=100,
                        max_value=100000,
                        key=f"edit_batch_{table.id}"
                    )

                new_description = st.text_area(
                    "설명",
                    value=table.description or "",
                    key=f"edit_desc_{table.id}"
                )

                new_sync_enabled = st.checkbox(
                    "동기화 활성화",
                    value=table.sync_enabled,
                    key=f"edit_enabled_{table.id}"
                )

                col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
                with col1:
                    update = st.form_submit_button("수정", use_container_width=True)
                with col2:
                    toggle = st.form_submit_button("토글", use_container_width=True)
                with col3:
                    delete = st.form_submit_button("삭제", type="secondary", use_container_width=True)

                if update:
                    handle_update_table(
                        table_service,
                        table.id,
                        new_oracle_schema,
                        new_oracle_table,
                        new_duckdb_table,
                        new_primary_key,
                        new_time_column,
                        new_batch_size,
                        new_sync_enabled,
                        new_description
                    )

                if toggle:
                    handle_toggle_sync(table_service, table.id, not table.sync_enabled)

                if delete:
                    handle_delete_table(table_service, table.id, table.get_oracle_full_name())


def render_create_table_form(table_service: TableConfigService):
    """테이블 추가 폼 렌더링"""
    st.subheader("새 테이블 설정 추가")

    with st.form("create_table_form"):
        col1, col2 = st.columns(2)

        with col1:
            oracle_schema = st.text_input("Oracle 스키마", placeholder="SCOTT")
            oracle_table = st.text_input("Oracle 테이블", placeholder="EMP")
            duckdb_table = st.text_input("DuckDB 테이블", placeholder="emp")

        with col2:
            primary_key = st.text_input("기본 키", placeholder="EMPNO")
            time_column = st.text_input("시간 컬럼 (선택)", placeholder="MODIFIED_DATE")
            batch_size = st.number_input("배치 크기", value=10000, min_value=100, max_value=100000)

        description = st.text_area("설명 (선택)", placeholder="사원 정보 테이블")

        submit = st.form_submit_button("추가", use_container_width=True)

        if submit:
            handle_create_table(
                table_service,
                oracle_schema,
                oracle_table,
                duckdb_table,
                primary_key,
                time_column,
                batch_size,
                description
            )


def render_import_from_env(table_service: TableConfigService, config: Config):
    """환경변수에서 가져오기"""
    st.subheader("환경변수에서 설정 가져오기")

    st.info("""
    .env 파일에 설정된 테이블 정보를 가져옵니다:
    - SYNC_ORACLE_SCHEMA
    - SYNC_ORACLE_TABLE
    - SYNC_DUCKDB_TABLE
    - SYNC_PRIMARY_KEY
    - SYNC_TIME_COLUMN
    """)

    # 현재 환경변수 표시
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Oracle 스키마**: {config.sync_oracle_schema or '없음'}")
        st.markdown(f"**Oracle 테이블**: {config.sync_oracle_table or '없음'}")
        st.markdown(f"**DuckDB 테이블**: {config.sync_duckdb_table or '없음'}")

    with col2:
        st.markdown(f"**기본 키**: {config.sync_primary_key or '없음'}")
        st.markdown(f"**시간 컬럼**: {config.sync_time_column or '없음'}")

    if st.button("환경변수에서 가져오기", type="primary", use_container_width=True):
        handle_import_from_env(table_service, config)


def handle_create_table(
    table_service: TableConfigService,
    oracle_schema: str,
    oracle_table: str,
    duckdb_table: str,
    primary_key: str,
    time_column: str,
    batch_size: int,
    description: str
):
    """테이블 생성 처리"""
    if not oracle_schema or not oracle_table or not duckdb_table or not primary_key:
        st.error("Oracle 스키마, 테이블, DuckDB 테이블, 기본 키는 필수입니다.")
        return

    success, message, table = table_service.create_table_config(
        oracle_schema=oracle_schema,
        oracle_table=oracle_table,
        duckdb_table=duckdb_table,
        primary_key=primary_key,
        time_column=time_column,
        batch_size=batch_size,
        description=description
    )

    if success:
        st.success(f"✅ {message}")
        logger.info(f"Table config created: {table.get_oracle_full_name()}")
        st.rerun()
    else:
        st.error(f"❌ {message}")


def handle_update_table(
    table_service: TableConfigService,
    table_id: int,
    oracle_schema: str,
    oracle_table: str,
    duckdb_table: str,
    primary_key: str,
    time_column: str,
    batch_size: int,
    sync_enabled: bool,
    description: str
):
    """테이블 수정 처리"""
    if not oracle_schema or not oracle_table or not duckdb_table or not primary_key:
        st.error("Oracle 스키마, 테이블, DuckDB 테이블, 기본 키는 필수입니다.")
        return

    table = TableConfig(
        id=table_id,
        oracle_schema=oracle_schema,
        oracle_table=oracle_table,
        duckdb_table=duckdb_table,
        primary_key=primary_key,
        time_column=time_column,
        batch_size=batch_size,
        sync_enabled=sync_enabled,
        description=description
    )

    success, message = table_service.update_table_config(table)

    if success:
        st.success(f"✅ {message}")
        logger.info(f"Table config updated: {table.get_oracle_full_name()}")
        st.rerun()
    else:
        st.error(f"❌ {message}")


def handle_toggle_sync(table_service: TableConfigService, table_id: int, enabled: bool):
    """동기화 토글 처리"""
    success, message = table_service.toggle_sync(table_id, enabled)

    if success:
        st.success(f"✅ {message}")
        st.rerun()
    else:
        st.error(f"❌ {message}")


def handle_delete_table(table_service: TableConfigService, table_id: int, table_name: str):
    """테이블 삭제 처리"""
    st.warning(f"⚠️ 정말로 테이블 설정 '{table_name}'를 삭제하시겠습니까?")

    success, message = table_service.delete_table_config(table_id)

    if success:
        st.success(f"✅ {message}")
        logger.info(f"Table config deleted: {table_name}")
        st.rerun()
    else:
        st.error(f"❌ {message}")


def handle_import_from_env(table_service: TableConfigService, config: Config):
    """환경변수 가져오기 처리"""
    success, message, table = table_service.import_from_env(config)

    if success:
        st.success(f"✅ {message}")
        logger.info(f"Imported table config from env: {table.get_oracle_full_name()}")
        st.rerun()
    else:
        st.error(f"❌ {message}")


# 페이지 메인
if __name__ == "__main__":
    render_admin_tables_page()
