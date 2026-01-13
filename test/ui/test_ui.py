from unittest.mock import patch


def test_120_streamlit_page_config():
    """TEST-120: Streamlit 기본 설정 호출 확인"""
    # app.py의 main() 실행 시 st.set_page_config가 호출되는지 확인
    with patch("streamlit.set_page_config") as mock_config, \
         patch("streamlit.title"), \
         patch("streamlit.sidebar"), \
         patch("streamlit.subheader"), \
         patch("streamlit.text_input"), \
         patch("streamlit.button"), \
         patch("oracle_duckdb_sync.ui.app.load_config"), \
         patch("oracle_duckdb_sync.ui.app.DuckDBSource"):

        # Import and run main()
        from oracle_duckdb_sync.ui.app import main
        main()

        # Verify that set_page_config was called
        mock_config.assert_called_once()

        # Verify the page_title parameter was set
        call_kwargs = mock_config.call_args[1]
        assert "page_title" in call_kwargs
        assert call_kwargs["page_title"] == "Oracle-DuckDB Sync Dashboard"

        # Verify layout parameter
        assert "layout" in call_kwargs
        assert call_kwargs["layout"] == "wide"


def test_121_preset_period_selector():
    """TEST-121: UI 컴포넌트 동작 및 사전 설정 기간 선택

    Verify that the UI provides preset period selection functionality:
    1. Preset options are available (최근 7일, 최근 30일, 최근 90일, 전체)
    2. Selecting a preset updates the date range correctly
    3. Preset selection integrates with existing date filter
    4. Custom date selection is still available alongside presets
    """
    from datetime import datetime, timedelta

    from oracle_duckdb_sync.ui.ui_helpers import get_preset_date_range

    # Fix: Use a single datetime.now() call to avoid date boundary issues
    now = datetime.now()
    today = now.date()

    # Test preset date range calculation
    # "최근 7일" should return date range from 7 days ago to today
    start_date, end_date = get_preset_date_range("최근 7일", base_date=now)
    expected_start = today - timedelta(days=7)
    expected_end = today

    assert start_date.date() == expected_start
    assert end_date.date() == expected_end

    # "최근 30일" should return date range from 30 days ago to today
    start_date, end_date = get_preset_date_range("최근 30일", base_date=now)
    expected_start = today - timedelta(days=30)
    expected_end = today

    assert start_date.date() == expected_start
    assert end_date.date() == expected_end

    # "최근 90일" should return date range from 90 days ago to today
    start_date, end_date = get_preset_date_range("최근 90일", base_date=now)
    expected_start = today - timedelta(days=90)
    expected_end = today

    assert start_date.date() == expected_start
    assert end_date.date() == expected_end

    # "전체" should return None (no filtering)
    result = get_preset_date_range("전체", base_date=now)
    assert result is None

