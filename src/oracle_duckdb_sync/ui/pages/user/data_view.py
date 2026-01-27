"""
데이터 조회 페이지

DuckDB 테이블 데이터를 조회하고 표시합니다.
"""

import streamlit as st

from oracle_duckdb_sync.application import QueryService
from oracle_duckdb_sync.config import load_config
from oracle_duckdb_sync.database import DuckDBSource
from oracle_duckdb_sync.log.logger import setup_logger
from oracle_duckdb_sync.adapters import MessageContext, StreamlitAdapter
# query_duckdb_table_cached is not needed - using QueryService directly
from oracle_duckdb_sync.ui.pages.login import require_auth

logger = setup_logger('DataViewPage')


@require_auth()
def render_data_view():
    """데이터 조회 페이지 렌더링"""
    st.title("📊 데이터 조회")

    try:
        config = load_config()

        if not config.sync_oracle_table:
            st.error("❌ SYNC_ORACLE_TABLE이 .env 파일에 설정되지 않았습니다.")
            return

        duckdb = DuckDBSource(config)
        query_service = QueryService(duckdb)
        ui_adapter = StreamlitAdapter()

        # 테이블 선택
        render_table_selection(query_service, config)

        st.markdown("---")

        # 조회 옵션
        render_query_options(query_service, config, duckdb, ui_adapter)

        st.markdown("---")

        # 조회 결과 표시
        render_query_results(query_service, ui_adapter)

    except Exception as e:
        logger.error(f"데이터 조회 페이지 렌더링 실패: {e}", exc_info=True)
        st.error(f"❌ 페이지를 로드할 수 없습니다: {e}")


def render_table_selection(query_service: QueryService, config):
    """테이블 선택 UI"""
    st.subheader("🗄️ 테이블 선택")

    # 사용 가능한 테이블 목록
    table_list = query_service.get_available_tables()

    if not table_list:
        st.warning("⚠️ 사용 가능한 테이블이 없습니다.")
        return None

    # 기본 테이블 결정
    default_table = query_service.determine_default_table_name(config, table_list)

    # 테이블 선택
    selected_table = st.selectbox(
        "조회할 테이블",
        options=table_list,
        index=table_list.index(default_table) if default_table in table_list else 0,
        help="조회할 DuckDB 테이블을 선택하세요"
    )

    # 세션에 저장
    st.session_state.selected_table = selected_table

    # 테이블 정보 표시
    row_count = query_service.get_table_row_count(selected_table)
    st.info(f"📊 선택된 테이블: **{selected_table}** ({row_count:,}행)")

    return selected_table


def render_query_options(query_service: QueryService, config, duckdb: DuckDBSource, ui_adapter: StreamlitAdapter):
    """조회 옵션 UI"""
    st.subheader("⚙️ 조회 옵션")

    if 'selected_table' not in st.session_state:
        st.warning("⚠️ 테이블을 먼저 선택하세요.")
        return

    duckdb_table_name = st.session_state.selected_table
    time_column = config.duckdb_time_column
    row_count = query_service.get_table_row_count(duckdb_table_name)

    col1, col2 = st.columns([2, 1])

    with col1:
        query_mode = st.radio(
            "조회 모드",
            options=["집계 뷰 (빠름)", "상세 뷰 (전체 데이터 + LTTB)"],
            index=0,
            help="집계 뷰: 빠른 초기 로딩, 트렌드 확인용 | 상세 뷰: 이상치 포함 전체 데이터"
        )

    with col2:
        if query_mode == "집계 뷰 (빠름)":
            resolution = st.selectbox(
                "시간 해상도",
                options=["1 minute", "10 minutes", "1 hour"],
                index=1,
                help="데이터 집계 간격 (작을수록 상세하지만 느림)"
            )
        else:
            resolution = None
            st.info("💡 LTTB 샘플링 적용됨")

    # 조회 버튼
    if st.button("🔍 조회", type="primary", use_container_width=True):
        handle_query(
            query_service,
            duckdb,
            ui_adapter,
            duckdb_table_name,
            time_column,
            query_mode,
            resolution,
            row_count
        )


def handle_query(
    query_service: QueryService,
    duckdb: DuckDBSource,
    ui_adapter: StreamlitAdapter,
    table_name: str,
    time_column: str,
    query_mode: str,
    resolution: str,
    row_count: int
):
    """조회 처리"""
    if query_mode == "집계 뷰 (빠름)":
        # 집계 조회
        with st.spinner(f"집계 데이터 조회 중... (해상도: {resolution})"):
            agg_result = query_service.query_table_aggregated_legacy(
                table_name=table_name,
                time_column=time_column,
                interval=resolution
            )

        if agg_result['success']:
            st.session_state.query_result = {
                'df_converted': agg_result['df_aggregated'],
                'table_name': agg_result['table_name'],
                'success': True,
                'query_mode': 'aggregated',
                'interval': agg_result['interval'],
                'numeric_cols': agg_result.get('numeric_cols', []),
                'row_count': row_count
            }
            ui_adapter.presenter.show_message(MessageContext(
                level='success',
                message=f"✅ 집계 완료: {len(agg_result['df_aggregated'])} 시간 구간"
            ))
        else:
            ui_adapter.presenter.show_message(MessageContext(
                level='error',
                message=f"집계 쿼리 오류: {agg_result['error']}"
            ))
            st.session_state.query_result = None

    else:
        # 상세 조회
        with st.spinner(f"전체 데이터 조회 중... ({row_count:,}행)"):
            result = query_service.query_table(
                table_name,
                convert_types=True
            )

        if result.success:
            st.session_state.query_result = {
                'df_converted': result.data,
                'table_name': table_name,
                'success': True,
                'query_mode': 'detailed',
                'row_count': row_count
            }
        else:
            ui_adapter.presenter.show_message(MessageContext(
                level='error',
                message=f"상세 조회 오류: {result.error or 'Unknown error'}"
            ))
            st.session_state.query_result = None


def render_query_results(query_service: QueryService, ui_adapter: StreamlitAdapter):
    """조회 결과 표시"""
    st.subheader("📋 조회 결과")

    if not st.session_state.get('query_result') or not st.session_state.query_result.get('success'):
        st.info("💡 조회 버튼을 클릭하여 데이터를 조회하세요.")
        return

    query_result = st.session_state.query_result
    df_converted = query_result.get('df_converted')
    query_mode = query_result.get('query_mode', 'detailed')
    table_name_for_grid = query_result.get('table_name')
    total_rows = query_result.get('row_count')

    if df_converted is None:
        st.warning("⚠️ 조회 결과가 없습니다.")
        return

    # 조회 모드 정보
    if query_mode == 'aggregated':
        interval = query_result.get('interval', 'unknown')
        ui_adapter.presenter.show_message(MessageContext(
            level='info',
            message=f"📊 집계 뷰 표시 중 (해상도: {interval}, 총 {len(df_converted)} 시간 구간)"
        ))
    else:
        ui_adapter.presenter.show_message(MessageContext(
            level='info',
            message=f"📊 상세 뷰 표시 중 (총 {len(df_converted):,}행)"
        ))

    # 표시 행 수 제한
    max_display_rows = st.number_input(
        "표시할 최대 행 수",
        min_value=100,
        max_value=1000,
        value=100,
        step=100,
        help="브라우저 성능을 위해 표시되는 행 수를 제한합니다."
    )

    # 데이터 표시
    grid_df = None
    if query_mode == 'aggregated' and table_name_for_grid:
        # 원본 데이터 가져오기
        raw_result = query_service.query_table(
            table_name_for_grid,
            limit=max_display_rows,
            convert_types=True
        )

        if raw_result.success:
            grid_df = raw_result.data
        else:
            ui_adapter.presenter.show_message(MessageContext(
                level='error',
                message=f"원본 데이터 조회 오류: {raw_result.error or 'Unknown error'}"
            ))
    else:
        grid_df = df_converted

    if grid_df is not None:
        display_rows = min(total_rows, max_display_rows) if total_rows is not None else min(len(grid_df), max_display_rows)

        with st.spinner(f"데이터 테이블 렌더링 중... ({display_rows:,}행)"):
            if total_rows is not None and total_rows > max_display_rows:
                ui_adapter.presenter.show_message(MessageContext(
                    level='warning',
                    message=f"⚠️ 성능을 위해 {max_display_rows:,}행만 표시합니다. (전체: {total_rows:,}행)"
                ))
                st.dataframe(grid_df.head(max_display_rows), use_container_width=True)
            else:
                st.dataframe(grid_df, use_container_width=True)


if __name__ == "__main__":
    render_data_view()
