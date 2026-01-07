def test_002_oracledb_import():
    """TEST-002: python-oracledb 라이브러리 임포트 확인"""
    import oracledb
    assert oracledb.__version__


def test_003_duckdb_import():
    """TEST-003: duckdb 라이브러리 임포트 확인"""
    import duckdb
    assert duckdb.__version__


def test_004_ui_libraries_import():
    """TEST-004: Streamlit 및 Plotly 라이브러리 임포트 확인"""
    import streamlit
    import plotly
    assert streamlit.__version__
    assert plotly.__version__
