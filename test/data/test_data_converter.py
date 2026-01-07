"""
Unit tests for data_converter module.
"""

import pytest
import pandas as pd
import numpy as np
from oracle_duckdb_sync.data.converter import (
    is_numeric_string,
    is_datetime_string,
    convert_to_datetime,
    convert_to_numeric,
    detect_and_convert_types,
    detect_column_type,
    convert_column_to_type
)


class TestNumericStringDetection:
    """Tests for numeric string detection."""
    
    def test_pure_numeric_strings(self):
        """Test detection of pure numeric strings."""
        series = pd.Series(['123', '456', '789', '0'])
        assert is_numeric_string(series) is True
    
    def test_float_strings(self):
        """Test detection of float strings."""
        series = pd.Series(['123.45', '67.89', '0.123', '999.999'])
        assert is_numeric_string(series) is True
    
    def test_mixed_with_nulls(self):
        """Test numeric strings with null values."""
        series = pd.Series(['123', None, '456', np.nan, '789'])
        assert is_numeric_string(series) is True
    
    def test_non_numeric_strings(self):
        """Test non-numeric strings."""
        series = pd.Series(['abc', 'def', 'ghi'])
        assert is_numeric_string(series) is False
    
    def test_mostly_numeric(self):
        """Test series with mostly numeric values."""
        series = pd.Series(['123', '456', '789', 'abc', '999'])
        # 80% numeric, but threshold is 90%
        assert is_numeric_string(series) is False
    
    def test_empty_series(self):
        """Test empty series."""
        series = pd.Series([], dtype=object)
        assert is_numeric_string(series) is False


class TestDatetimeStringDetection:
    """Tests for datetime string detection."""
    
    def test_yyyymmddhhmmss_format(self):
        """Test detection of YYYYMMDDHHMMSS format (14 digits)."""
        series = pd.Series(['20231219153045', '20240101120000', '20231231235959'])
        assert is_datetime_string(series) is True
    
    def test_yyyymmdd_format(self):
        """Test detection of YYYYMMDD format (8 digits)."""
        series = pd.Series(['20231219', '20240101', '20231231'])
        assert is_datetime_string(series) is True
    
    def test_iso_format(self):
        """Test detection of ISO date format."""
        series = pd.Series(['2023-12-19', '2024-01-01', '2023-12-31'])
        assert is_datetime_string(series) is True
    
    def test_slash_format(self):
        """Test detection of slash date format."""
        series = pd.Series(['2023/12/19', '2024/01/01', '2023/12/31'])
        assert is_datetime_string(series) is True
    
    def test_non_datetime_strings(self):
        """Test non-datetime strings."""
        series = pd.Series(['abc', 'def', 'ghi'])
        assert is_datetime_string(series) is False
    
    def test_numeric_but_not_datetime(self):
        """Test numeric strings that aren't datetime."""
        series = pd.Series(['123', '456', '789'])
        assert is_datetime_string(series) is False


class TestDatetimeConversion:
    """Tests for datetime conversion."""
    
    def test_convert_yyyymmddhhmmss(self):
        """Test conversion of YYYYMMDDHHMMSS format."""
        series = pd.Series(['20231219153045', '20240101120000'], name='test_col')
        result = convert_to_datetime(series)
        
        assert result is not None
        assert pd.api.types.is_datetime64_any_dtype(result)
        assert result[0] == pd.Timestamp('2023-12-19 15:30:45')
        assert result[1] == pd.Timestamp('2024-01-01 12:00:00')
    
    def test_convert_yyyymmdd(self):
        """Test conversion of YYYYMMDD format."""
        series = pd.Series(['20231219', '20240101'], name='test_col')
        result = convert_to_datetime(series)
        
        assert result is not None
        assert pd.api.types.is_datetime64_any_dtype(result)
        assert result[0] == pd.Timestamp('2023-12-19')
        assert result[1] == pd.Timestamp('2024-01-01')
    
    def test_convert_iso_format(self):
        """Test conversion of ISO format."""
        series = pd.Series(['2023-12-19 15:30:45', '2024-01-01 12:00:00'], name='test_col')
        result = convert_to_datetime(series)
        
        assert result is not None
        assert pd.api.types.is_datetime64_any_dtype(result)
    
    def test_convert_with_nulls(self):
        """Test conversion with null values."""
        series = pd.Series(['20231219153045', None, '20240101120000'], name='test_col')
        result = convert_to_datetime(series)
        
        assert result is not None
        assert pd.api.types.is_datetime64_any_dtype(result)
        assert pd.isna(result[1])


class TestNumericConversion:
    """Tests for numeric conversion."""
    
    def test_convert_integer_strings(self):
        """Test conversion of integer strings."""
        series = pd.Series(['123', '456', '789'], name='test_col')
        result = convert_to_numeric(series)
        
        assert result is not None
        assert pd.api.types.is_numeric_dtype(result)
        assert result[0] == 123
        assert result[1] == 456
    
    def test_convert_float_strings(self):
        """Test conversion of float strings."""
        series = pd.Series(['123.45', '67.89', '0.123'], name='test_col')
        result = convert_to_numeric(series)
        
        assert result is not None
        assert pd.api.types.is_numeric_dtype(result)
        assert abs(result[0] - 123.45) < 0.01
    
    def test_convert_with_nulls(self):
        """Test conversion with null values."""
        series = pd.Series(['123', None, '456'], name='test_col')
        result = convert_to_numeric(series)
        
        assert result is not None
        assert pd.api.types.is_numeric_dtype(result)
        assert pd.isna(result[1])


class TestDetectColumnType:
    """Tests for detect_column_type function."""
    
    def test_detect_numeric_type(self):
        """Test detection of numeric type."""
        from oracle_duckdb_sync.data.converter import detect_column_type
        
        series = pd.Series(['123', '456', '789'])
        result = detect_column_type(series)
        
        assert result == 'numeric'
    
    def test_detect_datetime_type(self):
        """Test detection of datetime type."""
        from oracle_duckdb_sync.data.converter import detect_column_type
        
        series = pd.Series(['20231219153045', '20240101120000', '20231231235959'])
        result = detect_column_type(series)
        
        assert result == 'datetime'
    
    def test_detect_string_type(self):
        """Test detection of string type."""
        from oracle_duckdb_sync.data.converter import detect_column_type
        
        series = pd.Series(['Alice', 'Bob', 'Charlie'])
        result = detect_column_type(series)
        
        assert result == 'string'
    
    def test_datetime_takes_precedence_over_numeric(self):
        """Test that datetime detection takes precedence over numeric."""
        from oracle_duckdb_sync.data.converter import detect_column_type
        
        # 8-digit numbers that could be dates
        series = pd.Series(['20231219', '20240101', '20231231'])
        result = detect_column_type(series)
        
        # Should be detected as datetime, not numeric
        assert result == 'datetime'
    
    def test_custom_threshold(self):
        """Test detection with custom threshold."""
        from oracle_duckdb_sync.data.converter import detect_column_type
        
        # 80% numeric
        series = pd.Series(['123', '456', '789', 'abc', '999'])
        
        # Should fail with default 0.9 threshold
        result_default = detect_column_type(series)
        assert result_default == 'string'
        
        # Should succeed with 0.7 threshold
        result_custom = detect_column_type(series, threshold=0.7)
        assert result_custom == 'numeric'


class TestConvertColumnToType:
    """Tests for convert_column_to_type function."""
    
    def test_convert_to_numeric_type(self):
        """Test conversion to numeric type."""
        from oracle_duckdb_sync.data.converter import convert_column_to_type
        
        series = pd.Series(['123', '456', '789'])
        result = convert_column_to_type(series, 'numeric')
        
        assert pd.api.types.is_numeric_dtype(result)
        assert result[0] == 123
    
    def test_convert_to_datetime_type(self):
        """Test conversion to datetime type."""
        from oracle_duckdb_sync.data.converter import convert_column_to_type
        
        series = pd.Series(['20231219153045', '20240101120000'])
        result = convert_column_to_type(series, 'datetime')
        
        assert pd.api.types.is_datetime64_any_dtype(result)
        assert result[0] == pd.Timestamp('2023-12-19 15:30:45')
    
    def test_convert_to_string_type_unchanged(self):
        """Test that string type returns unchanged."""
        from oracle_duckdb_sync.data.converter import convert_column_to_type
        
        series = pd.Series(['Alice', 'Bob', 'Charlie'])
        result = convert_column_to_type(series, 'string')
        
        assert result.dtype == 'object'
        assert result.equals(series)


class TestDetectAndConvertTypes:
    """Tests for automatic type detection and conversion."""
    
    def test_convert_mixed_dataframe(self):
        """Test conversion of dataframe with mixed types."""
        df = pd.DataFrame({
            'id': ['1', '2', '3'],
            'timestamp': ['20231219153045', '20240101120000', '20231231235959'],
            'value': ['123.45', '67.89', '99.99'],
            'name': ['Alice', 'Bob', 'Charlie']
        })
        
        result, _ = detect_and_convert_types(df)
        
        # Check that numeric columns were converted
        assert pd.api.types.is_numeric_dtype(result['id'])
        assert pd.api.types.is_numeric_dtype(result['value'])
        
        # Check that datetime column was converted
        assert pd.api.types.is_datetime64_any_dtype(result['timestamp'])
        
        # Check that string column remained unchanged
        assert result['name'].dtype == 'object'
    
    def test_preserve_existing_types(self):
        """Test that existing numeric/datetime types are preserved."""
        df = pd.DataFrame({
            'id': [1, 2, 3],
            'timestamp': pd.to_datetime(['2023-12-19', '2024-01-01', '2023-12-31']),
            'value': [123.45, 67.89, 99.99],
            'name': ['Alice', 'Bob', 'Charlie']
        })
        
        result, _ = detect_and_convert_types(df)
        
        # All types should remain the same
        assert pd.api.types.is_numeric_dtype(result['id'])
        assert pd.api.types.is_datetime64_any_dtype(result['timestamp'])
        assert pd.api.types.is_numeric_dtype(result['value'])
        assert result['name'].dtype == 'object'
    
    def test_empty_dataframe(self):
        """Test with empty dataframe."""
        df = pd.DataFrame()
        result, _ = detect_and_convert_types(df)
        
        assert result.empty
    
    def test_oracle_varchar2_scenario(self):
        """Test realistic Oracle VARCHAR2 scenario."""
        # Simulate data from Oracle with VARCHAR2 columns
        df = pd.DataFrame({
            'ORDER_ID': ['1001', '1002', '1003', '1004'],
            'ORDER_DATE': ['20231219153045', '20231220101530', '20231221083015', '20231222143045'],
            'AMOUNT': ['15000.50', '23000.75', '8500.00', '42000.25'],
            'CUSTOMER_NAME': ['김철수', '이영희', '박민수', '정수진'],
            'STATUS': ['COMPLETED', 'PENDING', 'COMPLETED', 'SHIPPED']
        })
        
        result, _ = detect_and_convert_types(df)
        
        # Verify conversions
        assert pd.api.types.is_numeric_dtype(result['ORDER_ID'])
        assert pd.api.types.is_datetime64_any_dtype(result['ORDER_DATE'])
        assert pd.api.types.is_numeric_dtype(result['AMOUNT'])
        assert result['CUSTOMER_NAME'].dtype == 'object'
        assert result['STATUS'].dtype == 'object'
        
        # Verify values
        assert result['ORDER_DATE'][0] == pd.Timestamp('2023-12-19 15:30:45')
        assert abs(result['AMOUNT'][0] - 15000.50) < 0.01


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
