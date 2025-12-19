import streamlit as st
import pandas as pd
import plotly.express as px
import queue
import time
from oracle_duckdb_sync.config import load_config
from oracle_duckdb_sync.duckdb_source import DuckDBSource
from oracle_duckdb_sync.sync_worker import SyncWorker
from oracle_duckdb_sync.sync_state import SyncLock
from oracle_duckdb_sync.logger import setup_logger
from oracle_duckdb_sync.data_converter import detect_and_convert_types

# Set up logger for app.py
app_logger = setup_logger('StreamlitApp')


def check_progress():
    """Check for progress updates from worker"""
    try:
        while not st.session_state.progress_queue.empty():
            msg = st.session_state.progress_queue.get_nowait()
            
            if msg['type'] == 'progress':
                st.session_state.sync_progress = msg['data']
            elif msg['type'] == 'complete':
                st.session_state.sync_status = 'completed'
                st.session_state.sync_result = msg['data']
                # Release lock on completion
                if 'sync_lock' in st.session_state and st.session_state.sync_lock:
                    st.session_state.sync_lock.release()
                    st.session_state.sync_lock = None
            elif msg['type'] == 'error':
                st.session_state.sync_status = 'error'
                st.session_state.sync_error = msg['data']
                # Release lock on error
                if 'sync_lock' in st.session_state and st.session_state.sync_lock:
                    st.session_state.sync_lock.release()
                    st.session_state.sync_lock = None
    except queue.Empty:
        pass


def main():
    st.set_page_config(page_title="Oracle-DuckDB Sync Dashboard", layout="wide")
    st.title("데이터 동기화 및 분석 대시보드")
    
    # Initialize session state
    if 'sync_status' not in st.session_state:
        st.session_state.sync_status = 'idle'
    if 'sync_worker' not in st.session_state:
        st.session_state.sync_worker = None
    if 'progress_queue' not in st.session_state:
        st.session_state.progress_queue = queue.Queue()
    if 'sync_progress' not in st.session_state:
        st.session_state.sync_progress = {}
    if 'sync_result' not in st.session_state:
        st.session_state.sync_result = {}
    if 'sync_error' not in st.session_state:
        st.session_state.sync_error = {}
    if 'sync_lock' not in st.session_state:
        st.session_state.sync_lock = None

    try:
        config = load_config()
        duckdb = DuckDBSource(config)
    except Exception as e:
        app_logger.error(f"설정 로드 실패: {e}")
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
    
    # Check if sync is running and update progress
    if st.session_state.sync_status == 'running':
        check_progress()
        
        st.sidebar.markdown("---")
        st.sidebar.subheader("🔄 동기화 진행 중")
        
        if st.session_state.sync_progress:
            progress = st.session_state.sync_progress
            
            # Progress bar (if percentage available)
            if progress.get('percentage', 0) > 0:
                st.sidebar.progress(min(progress['percentage'], 1.0))
            
            # Statistics
            col1, col2 = st.sidebar.columns(2)
            col1.metric("처리된 행", f"{progress.get('total_rows', 0):,}")
            col2.metric("처리 속도", f"{progress.get('rows_per_second', 0):.0f} rows/s")
            
            # Elapsed time
            elapsed = progress.get('elapsed_time', 0)
            st.sidebar.text(f"⏱️ 경과 시간: {elapsed:.0f}초")
            
            # ETA
            if progress.get('eta'):
                st.sidebar.text(f"⏰ 예상 완료: {progress['eta']}")
        else:
            st.sidebar.info("동기화 시작 중...")
        
        # Auto-refresh every 2 seconds
        time.sleep(2)
        st.rerun()
    
    # Display completion status
    elif st.session_state.sync_status == 'completed':
        st.sidebar.success("✅ 동기화 완료!")
        if st.session_state.sync_result:
            result = st.session_state.sync_result
            st.sidebar.info(f"총 {result.get('total_rows', 0):,} 행 처리됨")
        
        # Reset button
        if st.sidebar.button("새 동기화 시작"):
            st.session_state.sync_status = 'idle'
            st.session_state.sync_worker = None
            st.session_state.sync_progress = {}
            st.session_state.sync_result = {}
            st.rerun()
    
    # Display error status
    elif st.session_state.sync_status == 'error':
        st.sidebar.error("❌ 동기화 실패")
        if st.session_state.sync_error:
            error = st.session_state.sync_error
            st.sidebar.text(f"에러: {error.get('exception', 'Unknown error')}")
            
            with st.sidebar.expander("상세 에러 정보"):
                st.code(error.get('traceback', ''))
        
        # Reset button
        if st.sidebar.button("다시 시도"):
            st.session_state.sync_status = 'idle'
            st.session_state.sync_worker = None
            st.session_state.sync_error = {}
            st.rerun()
    
    # Test sync button - only enabled when idle
    if st.sidebar.button("🧪 테스트 동기화 실행 (제한된 행)", 
                         disabled=(st.session_state.sync_status == 'running')):
        if not table_name:
            st.sidebar.warning("테이블명을 입력하세요. .env 파일의 SYNC_ORACLE_TABLE을 설정하거나 '수동 설정 사용'을 체크하세요.")
        else:
            # Check if another sync is running
            sync_lock = SyncLock()
            if sync_lock.is_locked():
                lock_info = sync_lock.get_lock_info()
                st.sidebar.warning(f"⚠️ 다른 동기화 작업이 실행 중입니다. (PID: {lock_info.get('pid', 'unknown')})")
            else:
                # Acquire lock
                if sync_lock.acquire(timeout=1):
                    try:
                        # Use duckdb table name from config or convert to lowercase
                        if config.sync_duckdb_table:
                            duckdb_table = config.sync_duckdb_table
                        else:
                            table_parts = table_name.split('.')
                            duckdb_table = table_parts[-1].lower()
                        
                        # Add _test suffix to avoid overwriting production table
                        test_table = f"{duckdb_table}_test"
                        
                        # Prepare sync parameters
                        sync_params = {
                            'sync_type': 'test',
                            'oracle_table': table_name,
                            'duckdb_table': test_table,
                            'primary_key': primary_key,
                            'row_limit': test_row_limit
                        }
                        
                        # Create and start worker
                        worker = SyncWorker(config, sync_params, st.session_state.progress_queue)
                        worker.expected_rows = test_row_limit  # For ETA calculation
                        worker.start()
                        
                        st.session_state.sync_worker = worker
                        st.session_state.sync_status = 'running'
                        st.session_state.sync_progress = {}
                        st.session_state.sync_lock = sync_lock
                        st.rerun()
                        
                    except Exception as e:
                        import traceback
                        sync_lock.release()
                        st.sidebar.error(f"❌ 동기화 시작 실패: {e}")
                        with st.sidebar.expander("상세 에러 정보"):
                            st.code(traceback.format_exc())
                else:
                    st.sidebar.error("❌ 동기화 잠금을 획득할 수 없습니다.")
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("🚀 전체 동기화")
    
    
    if st.sidebar.button("🚀 전체 동기화 실행", 
                         disabled=(st.session_state.sync_status == 'running')):
        if not table_name:
            st.sidebar.warning("테이블명을 입력하세요. .env 파일의 SYNC_ORACLE_TABLE을 설정하거나 '수동 설정 사용'을 체크하세요.")
        else:
            # Check if another sync is running
            sync_lock = SyncLock()
            if sync_lock.is_locked():
                lock_info = sync_lock.get_lock_info()
                st.sidebar.warning(f"⚠️ 다른 동기화 작업이 실행 중입니다. (PID: {lock_info.get('pid', 'unknown')})")
            else:
                # Acquire lock
                if sync_lock.acquire(timeout=1):
                    try:
                        # Use duckdb table name from config or convert to lowercase
                        if config.sync_duckdb_table:
                            duckdb_table = config.sync_duckdb_table
                        else:
                            table_parts = table_name.split('.')
                            duckdb_table = table_parts[-1].lower()
                        
                        # Check if table exists in DuckDB to determine sync type
                        if not duckdb.table_exists(duckdb_table):
                            # First time sync - perform full sync
                            sync_params = {
                                'sync_type': 'full',
                                'oracle_table': table_name,
                                'duckdb_table': duckdb_table,
                                'primary_key': primary_key
                            }
                        else:
                            # Incremental sync
                            from oracle_duckdb_sync.sync_engine import SyncEngine
                            sync_engine = SyncEngine(config)
                            
                            # Load last sync time
                            last_sync_time = sync_engine.load_state(table_name)
                            if not last_sync_time:
                                last_sync_time = "2020-01-01 00:00:00"
                            
                            # Get first column from time_column (could be composite)
                            time_col = time_column.split(',')[0].strip() if time_column else "TIMESTAMP_COL"
                            
                            sync_params = {
                                'sync_type': 'incremental',
                                'oracle_table': table_name,
                                'duckdb_table': duckdb_table,
                                'time_column': time_col,
                                'last_value': last_sync_time
                            }
                        
                        # Create and start worker
                        worker = SyncWorker(config, sync_params, st.session_state.progress_queue)
                        worker.start()
                        
                        st.session_state.sync_worker = worker
                        st.session_state.sync_status = 'running'
                        st.session_state.sync_progress = {}
                        st.session_state.sync_lock = sync_lock
                        st.rerun()
                        
                    except Exception as e:
                        import traceback
                        sync_lock.release()
                        st.sidebar.error(f"❌ 동기화 시작 실패: {e}")
                        with st.sidebar.expander("상세 에러 정보"):
                            st.code(traceback.format_exc())
                else:
                    st.sidebar.error("❌ 동기화 잠금을 획득할 수 없습니다.")

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
        app_logger.warning(f"테이블 목록 조회 실패: {e}")
        st.warning(f"테이블 목록 조회 실패: {e}")
        table_list = []
    
    # DuckDB 데이터 조회
    # Extract table name without schema for DuckDB
    if config.sync_duckdb_table:
        default_table = config.sync_duckdb_table
    elif config.sync_oracle_table:
        # Remove schema prefix and convert to lowercase
        oracle_table_parts = config.sync_oracle_table.split('.')
        base_table = oracle_table_parts[-1].lower()  # Get last part (table name) and lowercase
        # Add _test suffix for test sync tables
        default_table = f"{base_table}_test"
    else:
        default_table = table_list[0] if table_list else "sync_table"
    
    query_table_name = st.text_input("조회할 테이블명", value=default_table, help="DuckDB 테이블명 (소문자, 스키마 없이)")
    
    
    if st.button("조회"):
        try:
            # Show query being executed
            st.info(f"실행 쿼리: SELECT * FROM {query_table_name} LIMIT 100")
            
            # Execute query
            data = duckdb.execute(f"SELECT * FROM {query_table_name} LIMIT 100")

            if not data or len(data) == 0:
                st.warning(f"조회 결과가 없습니다. 테이블 '{query_table_name}'이(가) 비어있거나 존재하지 않습니다.")
                # Show available tables
                try:
                    tables = duckdb.conn.execute("SHOW TABLES").fetchall()
                    st.info(f"사용 가능한 테이블: {[t[0] for t in tables]}")
                except:
                    pass
                # Clear cached data
                st.session_state.query_result = None
            else:
                # Get column names from DuckDB
                result = duckdb.conn.execute(f"SELECT * FROM {query_table_name} LIMIT 0")
                columns = [desc[0] for desc in result.description]
                df = pd.DataFrame(data, columns=columns)

                st.success(f"✅ {len(df)} 행 조회 완료")
                
                # Apply automatic type conversion for VARCHAR2 columns
                app_logger.info("Applying automatic type conversion to detect numeric and datetime columns")
                df_converted = detect_and_convert_types(df)
                
                # Show conversion results
                original_types = df.dtypes.to_dict()
                converted_types = df_converted.dtypes.to_dict()
                type_changes = {col: (str(original_types[col]), str(converted_types[col])) 
                               for col in df.columns 
                               if str(original_types[col]) != str(converted_types[col])}
                
                if type_changes:
                    with st.expander("🔄 자동 타입 변환 결과"):
                        for col, (old_type, new_type) in type_changes.items():
                            st.text(f"  • {col}: {old_type} → {new_type}")
                    app_logger.info(f"Type conversions applied: {type_changes}")
                
                # Cache the result in session state
                st.session_state.query_result = {
                    'df_converted': df_converted,
                    'table_name': query_table_name,
                    'type_changes': type_changes
                }
        except Exception as e:
            # Log error to file
            app_logger.error(f"데이터 조회 오류: {e}")
            import traceback
            error_traceback = traceback.format_exc()
            app_logger.error(f"Traceback:\n{error_traceback}")
            
            # Display error to user
            st.error(f"데이터 조회 오류: {e}")
            st.code(error_traceback)
            # Clear cached data
            st.session_state.query_result = None
    
    # Display cached query result if available
    if 'query_result' in st.session_state and st.session_state.query_result:
        result = st.session_state.query_result
        df_converted = result['df_converted']
        query_table_name = result['table_name']
        type_changes = result.get('type_changes', {})
        
        # Show data
        st.dataframe(df_converted)

        # Visualization only if data exists and has numeric columns
        if not df_converted.empty:
            st.subheader("시각화")
            
            # Select only numeric and datetime columns for visualization
            numeric_cols = df_converted.select_dtypes(include=['number']).columns.tolist()
            datetime_cols = df_converted.select_dtypes(include=['datetime64']).columns.tolist()
            
            if numeric_cols or datetime_cols:
                # Column selection UI
                st.markdown("**차트 설정**")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # X-axis selection (datetime columns)
                    if datetime_cols:
                        x_col = st.selectbox(
                            "X축 (시간 컬럼)",
                            options=datetime_cols,
                            index=0,
                            help="시간축으로 사용할 날짜/시간 컬럼을 선택하세요"
                        )
                    else:
                        x_col = None
                        st.info("📊 날짜/시간 컬럼이 없습니다. 인덱스를 X축으로 사용합니다.")
                
                with col2:
                    # Y-axis selection (numeric columns)
                    if numeric_cols:
                        # Filter out the selected x_col from numeric options
                        available_y_cols = [col for col in numeric_cols if col != x_col]
                        
                        if available_y_cols:
                            y_cols = st.multiselect(
                                "Y축 (숫자 컬럼)",
                                options=available_y_cols,
                                default=[],  # No columns selected by default
                                help="차트에 표시할 숫자 컬럼을 선택하세요 (복수 선택 가능)"
                            )
                        else:
                            y_cols = []
                            st.warning("시각화할 숫자형 컬럼이 없습니다.")
                    else:
                        y_cols = []
                        st.warning("숫자형 컬럼이 없습니다.")
                
                # Create chart if y columns are selected
                if y_cols:
                    # Create a copy for plotting to avoid modifying original data
                    df_plot = df_converted.copy()
                    
                    # Convert all numeric columns to float64 to avoid Plotly mixed-type error
                    for col in numeric_cols:
                        df_plot[col] = df_plot[col].astype('float64')
                    
                    try:
                        # Calculate Y-axis range based on actual data BEFORE creating the chart
                        # This ensures small variations are visible (e.g., 0.1746 vs 0.1747)
                        import numpy as np
                        y_values = df_plot[y_cols].values.flatten()
                        y_values = y_values[~np.isnan(y_values)]  # Remove NaN values
                        
                        if len(y_values) > 0:
                            y_min = np.min(y_values)
                            y_max = np.max(y_values)
                            
                            # Add 5% padding for better visualization
                            y_range = y_max - y_min
                            if y_range > 0:
                                padding = y_range * 0.05
                                y_axis_min = y_min - padding
                                y_axis_max = y_max + padding
                            else:
                                # If all values are the same, show a small range around the value
                                y_axis_min = y_min - abs(y_min) * 0.01 if y_min != 0 else -0.01
                                y_axis_max = y_max + abs(y_max) * 0.01 if y_max != 0 else 0.01
                        else:
                            y_axis_min = None
                            y_axis_max = None
                        
                        # Create the chart
                        if x_col:
                            # Use datetime column as x-axis
                            fig = px.line(df_plot, x=x_col, y=y_cols, title=f"{query_table_name} 트렌드")
                        else:
                            # No datetime column, use index as x-axis
                            fig = px.line(df_plot, y=y_cols, title=f"{query_table_name} 트렌드")
                        
                        # Apply Y-axis range if calculated
                        if y_axis_min is not None and y_axis_max is not None:
                            # Use update_layout for more reliable Y-axis range setting
                            fig.update_layout(
                                yaxis=dict(
                                    range=[y_axis_min, y_axis_max],
                                    autorange=False,  # Disable autorange
                                    rangemode='normal'  # Don't force zero
                                )
                            )
                            app_logger.info(f"Y-axis range set to [{y_axis_min:.6f}, {y_axis_max:.6f}]")
                        
                        # Disable range slider for cleaner view
                        fig.update_xaxes(rangeslider_visible=False)
                        
                        st.plotly_chart(fig, use_container_width=True)
                    except Exception as e:
                        app_logger.error(f"차트 생성 오류: {e}")
                        import traceback
                        app_logger.error(f"Traceback: {traceback.format_exc()}")
                        st.warning(f"⚠️ 차트 생성 중 오류가 발생했습니다: {e}")
                else:
                    st.info("💡 차트에 표시할 Y축 컬럼을 선택하세요.")
            else:
                st.info("시각화할 숫자형 또는 날짜형 컬럼이 없습니다. VARCHAR2 컬럼의 내용이 숫자나 날짜 형식이 아닐 수 있습니다.")


if __name__ == "__main__":
    main()
