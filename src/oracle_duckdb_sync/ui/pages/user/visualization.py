"""
시각화 페이지

데이터 시각화 기능을 제공합니다.
"""

import streamlit as st

from oracle_duckdb_sync.log.logger import setup_logger
from oracle_duckdb_sync.ui.pages.login import require_auth
from oracle_duckdb_sync.ui.visualization import render_data_visualization

logger = setup_logger('VisualizationPage')


@require_auth()
def render_visualization():
    """시각화 페이지 렌더링"""
    st.title("📈 데이터 시각화")

    # 조회 결과가 있는지 확인
    if not st.session_state.get('query_result') or not st.session_state.query_result.get('success'):
        st.info("💡 먼저 **데이터 조회** 페이지에서 데이터를 조회하세요.")

        # 데이터 조회 페이지로 이동 버튼
        if st.button("📊 데이터 조회 페이지로 이동", type="primary"):
            st.session_state.current_page = '/data'
            st.rerun()
        return

    # 조회 결과 가져오기
    query_result = st.session_state.query_result
    df_converted = query_result.get('df_converted')
    table_name = query_result.get('table_name')
    query_mode = query_result.get('query_mode', 'detailed')

    if df_converted is None:
        st.warning("⚠️ 시각화할 데이터가 없습니다.")
        return

    # 조회 모드 정보 표시
    if query_mode == 'aggregated':
        interval = query_result.get('interval', 'unknown')
        st.info(f"📊 집계 뷰 데이터 (해상도: {interval}, 총 {len(df_converted)} 시간 구간)")
    else:
        st.info(f"📊 상세 뷰 데이터 (총 {len(df_converted):,}행)")

    st.markdown("---")

    # 시각화 렌더링
    base_numeric_cols = None
    if query_mode == 'aggregated':
        base_numeric_cols = query_result.get('numeric_cols')

    render_data_visualization(
        df_converted,
        table_name,
        query_mode=query_mode,
        base_numeric_cols=base_numeric_cols
    )


if __name__ == "__main__":
    render_visualization()
