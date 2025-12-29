"""
Data visualization module for Oracle-DuckDB Sync Dashboard.

This module provides functions for rendering interactive data visualizations
using Plotly and Streamlit.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from oracle_duckdb_sync.logger import setup_logger

# Set up logger
viz_logger = setup_logger('Visualization')


def calculate_y_axis_range(y_values: np.ndarray, padding_percent: float = 0.05) -> tuple:
    """
    Calculate optimal Y-axis range with padding for better visualization.
    
    Args:
        y_values: Array of Y-axis values
        padding_percent: Percentage of padding to add (default: 5%)
    
    Returns:
        Tuple of (y_min, y_max) for Y-axis range, or (None, None) if no valid data
    """
    # Remove NaN values
    y_values = y_values[~np.isnan(y_values)]
    
    if len(y_values) == 0:
        return None, None
    
    y_min = np.min(y_values)
    y_max = np.max(y_values)
    
    # Add padding for better visualization
    y_range = y_max - y_min
    if y_range > 0:
        padding = y_range * padding_percent
        y_axis_min = y_min - padding
        y_axis_max = y_max + padding
    else:
        # If all values are the same, show a small range around the value
        y_axis_min = y_min - abs(y_min) * 0.01 if y_min != 0 else -0.01
        y_axis_max = y_max + abs(y_max) * 0.01 if y_max != 0 else 0.01
    
    return y_axis_min, y_axis_max


def _detect_datetime_columns(df: pd.DataFrame) -> list:
    """
    Detect datetime columns in DataFrame.
    
    Args:
        df: DataFrame to analyze
        
    Returns:
        List of datetime column names
    """
    return df.select_dtypes(include=['datetime64']).columns.tolist()


def _detect_numeric_columns(df: pd.DataFrame) -> list:
    """
    Detect numeric columns in DataFrame.
    
    Args:
        df: DataFrame to analyze
        
    Returns:
        List of numeric column names
    """
    return df.select_dtypes(include=['number']).columns.tolist()


def filter_dataframe_by_range(df: pd.DataFrame, column: str, min_value: float, max_value: float) -> pd.DataFrame:
    """
    Filter DataFrame to keep only rows where column value is within min and max range (inclusive).
    
    This function is useful for removing outliers and measurement errors from data.
    For example, if a column typically contains values between 0.12 and 0.13,
    but has outliers like 5.0 or 7.0, this function can filter those out.
    
    Args:
        df: DataFrame to filter
        column: Column name to filter by
        min_value: Minimum allowed value (inclusive)
        max_value: Maximum allowed value (inclusive)
        
    Returns:
        Filtered DataFrame with only rows where column values are within range
        
    Example:
        >>> df = pd.DataFrame({'measurement': [0.12, 0.13, 0.5, 5.0, 0.125]})
        >>> filtered = filter_dataframe_by_range(df, 'measurement', 0.12, 0.13)
        >>> len(filtered)  # Returns 4, excluding 5.0
    """
    if column not in df.columns:
        viz_logger.warning(f"Column '{column}' not found in DataFrame. Returning original DataFrame.")
        return df
    
    # Filter rows where column value is within [min_value, max_value]
    filtered_df = df[(df[column] >= min_value) & (df[column] <= max_value)].copy()
    
    original_count = len(df)
    filtered_count = len(filtered_df)
    excluded_count = original_count - filtered_count
    
    if excluded_count > 0:
        viz_logger.info(f"Filtered column '{column}': excluded {excluded_count} rows (kept {filtered_count}/{original_count})")
    
    return filtered_df


def render_data_visualization(df: pd.DataFrame, table_name: str):
    """
    Render interactive data visualization with Plotly charts.
    
    Args:
        df: DataFrame to visualize
        table_name: Name of the table being visualized
    """
    if df.empty:
        return
    
    # Detect visualizable columns
    numeric_cols = _detect_numeric_columns(df)
    datetime_cols = _detect_datetime_columns(df)
    
    if not numeric_cols and not datetime_cols:
        st.info("시각화할 숫자형 또는 날짜형 컬럼이 없습니다. VARCHAR2 컬럼의 내용이 숫자나 날짜 형식이 아닐 수 있습니다.")
        return
    
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
    if not y_cols:
        st.info("💡 차트에 표시할 Y축 컬럼을 선택하세요.")
        return
    
    # Data range filtering UI
    st.markdown("**데이터 범위 필터**")
    st.caption("선택한 컬럼의 데이터를 허용 범위 내로 필터링합니다. (예: 이상치 제거)")
    
    # Filter column selection
    filter_col = st.selectbox(
        "필터링할 컬럼",
        options=y_cols,
        help="허용 범위 필터를 적용할 컬럼을 선택하세요"
    )
    
    # Get min/max values for the selected column
    col_min = df[filter_col].min()
    col_max = df[filter_col].max()
    col_mean = df[filter_col].mean()
    col_std = df[filter_col].std()
    
    # Create columns for min/max input
    filter_col1, filter_col2 = st.columns(2)
    
    with filter_col1:
        min_value = st.number_input(
            "최소값",
            value=col_min,
            min_value=col_min,
            max_value=col_max,
            format="%.6f",
            help=f"현재 최소값: {col_min:.6f}"
        )
    
    with filter_col2:
        max_value = st.number_input(
            "최대값",
            value=col_max,
            min_value=col_min,
            max_value=col_max,
            format="%.6f",
            help=f"현재 최대값: {col_max:.6f}"
        )
    
    # Display statistics
    st.caption(f"📊 통계 - 평균: {col_mean:.6f}, 표준편차: {col_std:.6f}")
    
    # Apply filter if range is different from original
    filtered_df = df
    filter_applied = False
    if min_value > col_min or max_value < col_max:
        filtered_df = filter_dataframe_by_range(df, filter_col, min_value, max_value)
        excluded_count = len(df) - len(filtered_df)
        st.info(f"✂️ {excluded_count}개의 범위 외 데이터가 제외되었습니다. (전체: {len(df)}, 필터링 후: {len(filtered_df)})")
        filter_applied = True

    # Prepare and display chart
    # Pass filter_col to calculate Y-axis range based on filtered column only
    _create_and_display_chart(
        filtered_df,
        x_col,
        y_cols,
        numeric_cols,
        table_name,
        filtered_column=filter_col if filter_applied else None
    )


def _prepare_plot_dataframe(df: pd.DataFrame, numeric_cols: list, x_col: str = None) -> pd.DataFrame:
    """
    Prepare DataFrame for plotting by converting numeric columns to float64.

    Args:
        df: Original DataFrame
        numeric_cols: List of numeric column names
        x_col: X-axis column (typically datetime). If provided, will sort by this column.

    Returns:
        Copy of DataFrame with numeric columns as float64, sorted by x_col if provided
    """
    df_plot = df.copy()
    for col in numeric_cols:
        df_plot[col] = df_plot[col].astype('float64')

    # Sort by x_col to ensure lines are drawn correctly
    if x_col and x_col in df_plot.columns:
        df_plot = df_plot.sort_values(by=x_col).reset_index(drop=True)
        viz_logger.info(f"DataFrame sorted by '{x_col}' for proper line plotting")

    return df_plot


def _create_and_display_chart(
    df: pd.DataFrame,
    x_col: str,
    y_cols: list,
    numeric_cols: list,
    table_name: str,
    filtered_column: str = None
):
    """
    Create and display Plotly chart.

    Args:
        df: DataFrame to visualize
        x_col: X-axis column name (can be None for index-based x-axis)
        y_cols: List of Y-axis column names
        numeric_cols: List of all numeric column names
        table_name: Name of the table being visualized
        filtered_column: If filter is applied, the column that was filtered.
                        Y-axis range will be calculated based on this column only,
                        not all Y columns. This prevents filtered data from being
                        invisible when other Y columns have different value ranges.
    """
    # Prepare data - filter numeric_cols to only include those present in df
    # This is important because df might be a filtered dataframe
    available_numeric_cols = [col for col in numeric_cols if col in df.columns]
    df_plot = _prepare_plot_dataframe(df, available_numeric_cols, x_col=x_col)

    try:
        # Calculate Y-axis range based on filtered column or all Y columns
        # When filter is applied: use ONLY the filtered column for Y-axis range
        # This prevents other Y columns with different value ranges from distorting the view
        # Example: If VALUE_1 is filtered to 0.1746-0.1748, Y-axis should match this range
        #          even if other columns have values like 0.01-0.02 or 0.3-0.4
        if filtered_column and filtered_column in df_plot.columns:
            # Use only the filtered column for Y-axis range calculation
            y_values = df_plot[filtered_column].values.flatten()
            viz_logger.info(f"Y-axis range calculated from filtered column '{filtered_column}' only")
            st.caption(f"🔍 Y축 범위: '{filtered_column}' 컬럼 기준 (다른 Y 컬럼은 이 범위를 벗어날 수 있음)")
        else:
            # No filter applied, use all Y columns
            y_values = df_plot[y_cols].values.flatten()
            viz_logger.info(f"Y-axis range calculated from all Y columns: {y_cols}")

        y_axis_min, y_axis_max = calculate_y_axis_range(y_values)

        # Debug info: Show what columns are being plotted and their value ranges
        viz_logger.info(f"Plotting columns: {y_cols}")
        viz_logger.info(f"Y-axis range: [{y_axis_min:.6f}, {y_axis_max:.6f}]")
        for col in y_cols:
            col_min = df_plot[col].min()
            col_max = df_plot[col].max()
            viz_logger.info(f"  Column '{col}' data range: [{col_min:.6f}, {col_max:.6f}]")

        # Create the chart
        if x_col:
            # Use datetime column as x-axis
            fig = px.line(df_plot, x=x_col, y=y_cols, title=f"{table_name} 트렌드")
        else:
            # No datetime column, use index as x-axis
            fig = px.line(df_plot, y=y_cols, title=f"{table_name} 트렌드")
        
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
            viz_logger.info(f"Y-axis range set to [{y_axis_min:.6f}, {y_axis_max:.6f}]")
        
        # Disable range slider for cleaner view
        fig.update_xaxes(rangeslider_visible=False)
        
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        viz_logger.error(f"차트 생성 오류: {e}")
        import traceback
        viz_logger.error(f"Traceback: {traceback.format_exc()}")
        st.warning(f"⚠️ 차트 생성 중 오류가 발생했습니다: {e}")
