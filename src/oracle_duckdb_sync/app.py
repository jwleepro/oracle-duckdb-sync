import streamlit as st
import pandas as pd
import plotly.express as px
from oracle_duckdb_sync.config import load_config
from oracle_duckdb_sync.duckdb_source import DuckDBSource


def main():
    st.set_page_config(page_title="Oracle-DuckDB Sync Dashboard", layout="wide")
    st.title("데이터 동기화 및 분석 대시보드")

    try:
        config = load_config()
        duckdb = DuckDBSource(config)
    except Exception as e:
        st.error(f"설정을 로드할 수 없습니다: {e}")
        return

    st.sidebar.header("동기화 설정")
    
    # Display current configuration from .env
    if config.sync_oracle_table:
        st.sidebar.info(f"📋 설정된 테이블: {config.sync_oracle_table}")
        st.sidebar.text(f"Primary Key: {config.sync_primary_key}")
        st.sidebar.text(f"시간 컬럼: {config.sync_time_column}")
    else:
        st.sidebar.warning("⚠️ .env 파일에 SYNC_ORACLE_TABLE이 설정되지 않았습니다.")
    
    # Allow override with manual input
    use_manual_config = st.sidebar.checkbox("수동 설정 사용", value=False)
    
    if use_manual_config:
        table_name = st.sidebar.text_input("테이블명", value=config.sync_oracle_table, help="Oracle 원본 테이블명")
        primary_key = st.sidebar.text_input("Primary Key", value=config.sync_primary_key, help="Primary key 컬럼명")
        time_column = st.sidebar.text_input("시간 컬럼", value=config.sync_time_column, help="증분 동기화용 시간 컬럼명")
    else:
        # Use .env configuration
        table_name = config.sync_oracle_table
        primary_key = config.sync_primary_key
        time_column = config.sync_time_column
    
    if st.sidebar.button("지금 동기화 실행"):
        if not table_name:
            st.sidebar.warning("테이블명을 입력하세요. .env 파일의 SYNC_ORACLE_TABLE을 설정하거나 '수동 설정 사용'을 체크하세요.")
        else:
            st.sidebar.info(f"동기화 중... ({table_name})")
            try:
                from oracle_duckdb_sync.sync_engine import SyncEngine
                from oracle_duckdb_sync.oracle_source import OracleSource
                
                # Initialize sync engine
                oracle = OracleSource(config)
                sync_engine = SyncEngine(config)
                
                # Use duckdb table name from config or convert to lowercase
                duckdb_table = config.sync_duckdb_table if config.sync_duckdb_table else table_name.lower()
                
                # Perform incremental sync
                total_rows = sync_engine.incremental_sync(
                    oracle_table=table_name,
                    duckdb_table=duckdb_table,
                    time_column=time_column,
                    primary_key=primary_key
                )
                st.sidebar.success(f"✅ 동기화 완료! {total_rows} 행이 동기화되었습니다.")
                    
            except Exception as e:
                st.sidebar.error(f"❌ 동기화 실패: {e}")

    st.subheader("데이터 조회")
    # DuckDB 데이터 조회
    default_table = config.sync_duckdb_table if config.sync_duckdb_table else "sync_table"
    query_table_name = st.text_input("조회할 테이블명", value=default_table)
    if st.button("조회"):
        try:
            data = duckdb.execute(f"SELECT * FROM {query_table_name} LIMIT 100")
            df = pd.DataFrame(data)
            st.dataframe(df)

            if not df.empty:
                st.subheader("시각화")
                fig = px.line(df, title=f"{query_table_name} 트렌드")
                st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"데이터 조회 오류: {e}")


if __name__ == "__main__":
    main()
