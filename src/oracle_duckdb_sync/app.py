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
    
    # Test sync button with row limit
    st.sidebar.markdown("---")
    st.sidebar.subheader("🧪 테스트 동기화")
    test_row_limit = st.sidebar.number_input(
        "테스트 행 수", 
        min_value=1000, 
        max_value=10000, 
        value=10000, 
        step=1000,
        help="테스트로 가져올 최대 행 수 (기본: 1만)"
    )
    
    if st.sidebar.button("🧪 테스트 동기화 실행 (제한된 행)"):
        if not table_name:
            st.sidebar.warning("테이블명을 입력하세요. .env 파일의 SYNC_ORACLE_TABLE을 설정하거나 '수동 설정 사용'을 체크하세요.")
        else:
            st.sidebar.info(f"🧪 테스트 동기화 중... ({table_name}, 최대 {test_row_limit:,} 행)")
            try:
                from oracle_duckdb_sync.sync_engine import SyncEngine
                
                # Initialize sync engine
                sync_engine = SyncEngine(config)
                
                # Use duckdb table name from config or convert to lowercase
                if config.sync_duckdb_table:
                    duckdb_table = config.sync_duckdb_table
                else:
                    table_parts = table_name.split('.')
                    duckdb_table = table_parts[-1].lower()
                
                # Add _test suffix to avoid overwriting production table
                test_table = f"{duckdb_table}_test"
                
                # Perform test sync with limited rows
                st.sidebar.info(f"📥 {test_row_limit:,} 행으로 제한된 테스트 동기화 시작...")
                total_rows = sync_engine.test_sync(
                    oracle_table=table_name,
                    duckdb_table=test_table,
                    primary_key=primary_key,
                    row_limit=test_row_limit
                )
                st.sidebar.success(f"✅ 테스트 동기화 완료! {total_rows:,} 행이 '{test_table}' 테이블에 동기화되었습니다.")
                st.sidebar.info(f"💡 테스트 테이블: '{test_table}'")
                st.sidebar.info(f"💡 정상 동작 확인 후 '전체 동기화 실행' 버튼을 사용하세요.")
                
            except Exception as e:
                import traceback
                error_detail = traceback.format_exc()
                st.sidebar.error(f"❌ 테스트 동기화 실패: {e}")
                with st.sidebar.expander("상세 에러 정보"):
                    st.code(error_detail)
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("🚀 전체 동기화")
    
    if st.sidebar.button("🚀 전체 동기화 실행"):
        if not table_name:
            st.sidebar.warning("테이블명을 입력하세요. .env 파일의 SYNC_ORACLE_TABLE을 설정하거나 '수동 설정 사용'을 체크하세요.")
        else:
            st.sidebar.info(f"🚀 전체 동기화 중... ({table_name})")
            try:
                from oracle_duckdb_sync.sync_engine import SyncEngine
                from oracle_duckdb_sync.oracle_source import OracleSource
                
                # Initialize sync engine
                sync_engine = SyncEngine(config)
                
                # Use duckdb table name from config or convert to lowercase
                # Remove schema prefix if present (e.g., "SCHEMA.TABLE" → "table")
                if config.sync_duckdb_table:
                    duckdb_table = config.sync_duckdb_table
                else:
                    table_parts = table_name.split('.')
                    duckdb_table = table_parts[-1].lower()
                
                # Check if table exists in DuckDB
                if not duckdb.table_exists(duckdb_table):
                    # First time sync - perform full sync
                    st.sidebar.info(f"📥 초기 전체 동기화 시작... (시간이 걸릴 수 있습니다)")
                    total_rows = sync_engine.full_sync(
                        oracle_table=table_name,
                        duckdb_table=duckdb_table,
                        primary_key=primary_key
                    )
                    st.sidebar.success(f"✅ 초기 동기화 완료! {total_rows} 행이 동기화되었습니다.")
                    
                    # Save initial sync state
                    import datetime
                    sync_engine.save_state(table_name, datetime.datetime.now().isoformat())
                else:
                    # Incremental sync
                    st.sidebar.info(f"🔄 증분 동기화 시작...")
                    
                    # Load last sync time
                    last_sync_time = sync_engine.load_state(table_name)
                    if not last_sync_time:
                        # No state found, use a default old date
                        last_sync_time = "2020-01-01 00:00:00"
                    
                    # Get first column from time_column (could be composite)
                    time_col = time_column.split(',')[0].strip() if time_column else "TIMESTAMP_COL"
                    
                    total_rows = sync_engine.incremental_sync(
                        oracle_table=table_name,
                        duckdb_table=duckdb_table,
                        column=time_col,
                        last_value=last_sync_time
                    )
                    st.sidebar.success(f"✅ 증분 동기화 완료! {total_rows} 행이 동기화되었습니다.")
                    
                    # Update sync state
                    import datetime
                    sync_engine.save_state(table_name, datetime.datetime.now().isoformat())
                    
            except Exception as e:
                import traceback
                error_detail = traceback.format_exc()
                st.sidebar.error(f"❌ 동기화 실패: {e}")
                with st.sidebar.expander("상세 에러 정보"):
                    st.code(error_detail)

    st.subheader("데이터 조회")
    
    # Show available tables in DuckDB
    try:
        available_tables = duckdb.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'main'
            ORDER BY table_name
        """)
        table_list = [row[0] for row in available_tables] if available_tables else []
        
        if table_list:
            st.info(f"📊 사용 가능한 테이블: {', '.join(table_list)}")
        else:
            st.warning("⚠️ DuckDB에 테이블이 없습니다. 먼저 '지금 동기화 실행'을 클릭하세요.")
    except Exception as e:
        st.warning(f"테이블 목록 조회 실패: {e}")
        table_list = []
    
    # DuckDB 데이터 조회
    # Extract table name without schema for DuckDB
    if config.sync_duckdb_table:
        default_table = config.sync_duckdb_table
    elif config.sync_oracle_table:
        # Remove schema prefix and convert to lowercase
        oracle_table_parts = config.sync_oracle_table.split('.')
        default_table = oracle_table_parts[-1].lower()  # Get last part (table name) and lowercase
    else:
        default_table = table_list[0] if table_list else "sync_table"
    
    query_table_name = st.text_input("조회할 테이블명", value=default_table, help="DuckDB 테이블명 (소문자, 스키마 없이)")
    
    if st.button("조회"):
        try:
            # Show query being executed
            st.info(f"실행 쿼리: SELECT * FROM {query_table_name} LIMIT 100")
            
            data = duckdb.execute(f"SELECT * FROM {query_table_name} LIMIT 100")

            if not data:
                st.warning("조회 결과가 없습니다.")
            else:
                # Get column names from DuckDB
                result = duckdb.conn.execute(f"SELECT * FROM {query_table_name} LIMIT 0")
                columns = [desc[0] for desc in result.description]
                df = pd.DataFrame(data, columns=columns)

                st.success(f"✅ {len(df)} 행 조회 완료")
                st.dataframe(df)

                # Visualization only if data exists and has numeric columns
                if not df.empty:
                    st.subheader("시각화")
                    
                    # Select only numeric and datetime columns for visualization
                    numeric_cols = df.select_dtypes(include=['number', 'datetime64']).columns.tolist()
                    
                    if numeric_cols:
                        # If there's a datetime column, use it as x-axis
                        datetime_cols = df.select_dtypes(include=['datetime64']).columns.tolist()
                        if datetime_cols:
                            x_col = datetime_cols[0]
                            y_cols = [col for col in numeric_cols if col != x_col]
                            if y_cols:
                                fig = px.line(df, x=x_col, y=y_cols, title=f"{query_table_name} 트렌드")
                                st.plotly_chart(fig, use_container_width=True)
                            else:
                                st.info("시각화할 숫자형 컬럼이 없습니다.")
                        else:
                            # No datetime column, just plot numeric columns
                            fig = px.line(df, y=numeric_cols, title=f"{query_table_name} 트렌드")
                            st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("시각화할 숫자형 또는 날짜형 컬럼이 없습니다.")
        except Exception as e:
            st.error(f"데이터 조회 오류: {e}")


if __name__ == "__main__":
    main()
