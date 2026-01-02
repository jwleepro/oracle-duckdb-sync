"""
Query Service - UI-independent data query orchestration.

This service handles all query-related business logic without
depending on any UI framework.
"""

from typing import Dict, Any, Optional, List
import pandas as pd
from ..data.converter import detect_and_convert_types
from ..database.duckdb_source import DuckDBSource
from ..log.logger import setup_logger

logger = setup_logger(__name__)


class QueryResult:
    """Encapsulates query result with metadata."""
    
    def __init__(self, 
                 success: bool,
                 data: Optional[pd.DataFrame] = None,
                 error: Optional[str] = None,
                 metadata: Optional[Dict[str, Any]] = None):
        self.success = success
        self.data = data
        self.error = error
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'success': self.success,
            'df_converted': self.data,
            'error': self.error,
            **self.metadata
        }


class QueryService:
    """
    Application service for data queries.
    
    This service is UI-agnostic and can be used by any presentation layer.
    """
    
    def __init__(self, duckdb_source: DuckDBSource):
        self.duckdb_source = duckdb_source
        # Using function-based converter from data.converter module
    
    def get_available_tables(self) -> List[str]:
        """Get list of available tables."""
        try:
            conn = self.duckdb_source.get_connection()
            tables = conn.execute("SHOW TABLES").fetchall()
            return [table[0] for table in tables]
        except Exception as e:
            logger.error(f"Failed to get available tables: {e}")
            return []
    
    def get_table_row_count(self, table_name: str) -> int:
        """Get row count for a specific table."""
        try:
            conn = self.duckdb_source.get_connection()
            result = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
            return result[0] if result else 0
        except Exception as e:
            logger.error(f"Failed to get row count for {table_name}: {e}")
            return 0
    
    def query_table(self, 
                    table_name: str, 
                    limit: int = 10000,
                    convert_types: bool = True) -> QueryResult:
        """
        Query table and optionally convert data types.
        
        Args:
            table_name: Name of the table to query
            limit: Maximum number of rows to fetch
            convert_types: Whether to perform automatic type conversion
            
        Returns:
            QueryResult containing the data and metadata
        """
        try:
            # Fetch raw data
            conn = self.duckdb_source.get_connection()
            query = f"SELECT * FROM {table_name} LIMIT {limit}"
            
            logger.info(f"Executing query: {query}")
            df_raw = conn.execute(query).df()
            
            if df_raw is None or len(df_raw) == 0:
                return QueryResult(
                    success=False,
                    error=f"No data found in table '{table_name}'"
                )
            
            # Convert types if requested
            if convert_types:
                df_converted, conversions = detect_and_convert_types(df_raw)
                metadata = {
                    'row_count': len(df_converted),
                    'table_name': table_name,
                    'conversions': conversions
                }
            else:
                df_converted = df_raw
                metadata = {
                    'row_count': len(df_converted),
                    'table_name': table_name
                }
            
            return QueryResult(
                success=True,
                data=df_converted,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Query failed for table {table_name}: {e}")
            return QueryResult(
                success=False,
                error=str(e)
            )
    
    def query_table_aggregated(self,
                               table_name: str,
                               time_column: str,
                               value_columns: List[str],
                               resolution: str = '1h') -> QueryResult:
        """
        Query table with time-based aggregation.
        
        Args:
            table_name: Name of the table
            time_column: Name of the timestamp column
            value_columns: List of columns to aggregate
            resolution: Time resolution (e.g., '1h', '1d')
            
        Returns:
            QueryResult with aggregated data
        """
        try:
            conn = self.duckdb_source.get_connection()
            
            # Build aggregation query
            agg_cols = ", ".join([
                f"AVG({col}) as {col}_avg, "
                f"MIN({col}) as {col}_min, "
                f"MAX({col}) as {col}_max"
                for col in value_columns
            ])
            
            query = f"""
                SELECT 
                    time_bucket(INTERVAL '{resolution}', {time_column}) as time_bucket,
                    COUNT(*) as point_count,
                    {agg_cols}
                FROM {table_name}
                GROUP BY time_bucket
                ORDER BY time_bucket
            """
            
            logger.info(f"Executing aggregation query with resolution {resolution}")
            df_agg = conn.execute(query).df()
            
            if df_agg is None or len(df_agg) == 0:
                return QueryResult(
                    success=False,
                    error=f"No data found for aggregation"
                )
            
            metadata = {
                'row_count': len(df_agg),
                'table_name': table_name,
                'resolution': resolution,
                'query_mode': 'aggregated'
            }
            
            return QueryResult(
                success=True,
                data=df_agg,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Aggregation query failed: {e}")
            return QueryResult(
                success=False,
                error=str(e)
            )
