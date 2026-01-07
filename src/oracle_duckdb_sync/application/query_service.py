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
    
    def determine_default_table_name(self, config: 'Config', table_list: Optional[List[str]] = None) -> str:
        """
        Determine default table name for query based on configuration.
        
        Args:
            config: Configuration object
            table_list: List of available tables (optional, will fetch if None)
            
        Returns:
            Default table name
        """
        if config.sync_duckdb_table:
            return config.sync_duckdb_table
        
        if table_list is None:
            table_list = self.get_available_tables()
            
        if table_list:
            return table_list[0]
        else:
            return "sync_table"

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
    
    def query_table_aggregated_legacy(self,
                                      table_name: str,
                                      time_column: str,
                                      interval: str = '10 minutes',
                                      numeric_cols: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Query table with time bucket aggregation (legacy interface compatible).
        
        This method provides backward compatibility with the legacy query.py interface.
        It auto-detects numeric columns and handles VARCHAR conversion.
        
        Args:
            table_name: Name of table to query
            time_column: Name of timestamp column for bucketing
            interval: Time interval for aggregation (e.g., '1 minute', '10 minutes', '1 hour')
            numeric_cols: List of numeric columns to aggregate (if None, auto-detect)
        
        Returns:
            Dictionary containing:
                - df_aggregated: Aggregated DataFrame
                - table_name: Table name
                - interval: Aggregation interval used
                - numeric_cols: List of numeric columns used
                - success: Boolean indicating success
                - error: Error message if failed
        """
        try:
            conn = self.duckdb_source.get_connection()
            
            # Auto-detect numeric columns if not provided
            if numeric_cols is None:
                # Get column names
                result = conn.execute(f"SELECT * FROM {table_name} LIMIT 0")
                all_cols = [desc[0] for desc in result.description]
                
                # Sample data for type detection
                sample = conn.execute(f"SELECT * FROM {table_name} LIMIT 1000").fetchdf()
                
                # First try native numeric columns
                numeric_cols = [
                    col for col in sample.select_dtypes(include=['number']).columns
                    if col != time_column
                ]
                
                # If no numeric columns found, try to detect convertible VARCHAR columns
                if not numeric_cols:
                    logger.info("No native numeric columns found, checking VARCHAR columns...")
                    from ..data.converter import is_numeric_string
                    
                    varchar_cols = [
                        col for col in sample.select_dtypes(include=['object', 'string']).columns
                        if col != time_column
                    ]
                    
                    for col in varchar_cols:
                        if is_numeric_string(sample[col]):
                            numeric_cols.append(col)
                            logger.info(f"Detected numeric VARCHAR column: {col}")
            
            if not numeric_cols:
                return {
                    'df_aggregated': None,
                    'table_name': table_name,
                    'interval': interval,
                    'success': False,
                    'error': 'No numeric columns found for aggregation'
                }
            
            # Build aggregation query with MAX/MIN/AVG for each numeric column
            # Sample to check column types
            sample = conn.execute(f"SELECT * FROM {table_name} LIMIT 100").fetchdf()
            
            agg_exprs = []
            for col in numeric_cols:
                # Check if column needs casting (VARCHAR/string type)
                col_type = str(sample[col].dtype)
                if 'object' in col_type or 'string' in col_type:
                    # Cast VARCHAR to DOUBLE for aggregation
                    cast_expr = f"TRY_CAST({col} AS DOUBLE)"
                    agg_exprs.append(f"AVG({cast_expr}) as {col}_avg")
                    agg_exprs.append(f"MAX({cast_expr}) as {col}_max")
                    agg_exprs.append(f"MIN({cast_expr}) as {col}_min")
                else:
                    # Native numeric column, no casting needed
                    agg_exprs.append(f"AVG({col}) as {col}_avg")
                    agg_exprs.append(f"MAX({col}) as {col}_max")
                    agg_exprs.append(f"MIN({col}) as {col}_min")
            
            agg_clause = ', '.join(agg_exprs)
            
            # Parse time_column with custom format (YYYYMMDDHHmmss)
            query = f"""
            SELECT
                time_bucket(INTERVAL '{interval}', strptime(CAST({time_column} AS VARCHAR), '%Y%m%d%H%M%S')) as time_bucket,
                {agg_clause}
            FROM {table_name}
            GROUP BY time_bucket
            ORDER BY time_bucket
            """
            
            logger.info(f"Executing aggregated query with interval '{interval}'")
            
            # Execute query
            df_aggregated = conn.execute(query).fetchdf()
            
            if df_aggregated.empty:
                return {
                    'df_aggregated': None,
                    'table_name': table_name,
                    'interval': interval,
                    'success': False,
                    'error': 'No data returned from aggregation'
                }
            
            logger.info(f"Aggregation complete: {len(df_aggregated)} time buckets")
            
            return {
                'df_aggregated': df_aggregated,
                'table_name': table_name,
                'interval': interval,
                'numeric_cols': numeric_cols,
                'success': True,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"Aggregation query error: {e}")
            import traceback
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            return {
                'df_aggregated': None,
                'table_name': table_name,
                'interval': interval,
                'success': False,
                'error': str(e)
            }
