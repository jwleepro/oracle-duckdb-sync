import pytest
from unittest.mock import patch, MagicMock

def test_120_streamlit_page_config():
    """TEST-120: Streamlit 기본 설정 호출 확인"""
    # app.py의 main() 실행 시 st.set_page_config가 호출되는지 확인
    with patch("streamlit.set_page_config") as mock_config, \
         patch("streamlit.title") as mock_title, \
         patch("streamlit.sidebar") as mock_sidebar, \
         patch("streamlit.subheader") as mock_subheader, \
         patch("streamlit.text_input") as mock_text_input, \
         patch("streamlit.button") as mock_button, \
         patch("oracle_duckdb_sync.ui.app.load_config") as mock_load_config, \
         patch("oracle_duckdb_sync.ui.app.DuckDBSource") as mock_duckdb:
        
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

