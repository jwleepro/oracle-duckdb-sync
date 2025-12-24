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


def render_data_visualization(df: pd.DataFrame, table_name: str):
    """
    Render interactive data visualization with Plotly charts.
    
    Args:
        df: DataFrame to visualize
        table_name: Name of the table being visualized
    """
    if df.empty:
        return
    
    st.subheader("시각화")
    
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
    
    # Prepare and display chart
    _create_and_display_chart(df, x_col, y_cols, numeric_cols, table_name)


def _prepare_plot_dataframe(df: pd.DataFrame, numeric_cols: list) -> pd.DataFrame:
    """
    Prepare DataFrame for plotting by converting numeric columns to float64.
    
    Args:
        df: Original DataFrame
        numeric_cols: List of numeric column names
        
    Returns:
        Copy of DataFrame with numeric columns as float64
    """
    df_plot = df.copy()
    for col in numeric_cols:
        df_plot[col] = df_plot[col].astype('float64')
    return df_plot


def _create_and_display_chart(
    df: pd.DataFrame,
    x_col: str,
    y_cols: list,
    numeric_cols: list,
    table_name: str
):
    """
    Create and display Plotly chart.
    
    Args:
        df: DataFrame to visualize
        x_col: X-axis column name (can be None for index-based x-axis)
        y_cols: List of Y-axis column names
        numeric_cols: List of all numeric column names
        table_name: Name of the table being visualized
    """
    # Prepare data
    df_plot = _prepare_plot_dataframe(df, numeric_cols)
    
    try:
        # Calculate Y-axis range based on actual data BEFORE creating the chart
        # This ensures small variations are visible (e.g., 0.1746 vs 0.1747)
        y_values = df_plot[y_cols].values.flatten()
        y_axis_min, y_axis_max = calculate_y_axis_range(y_values)
        
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
