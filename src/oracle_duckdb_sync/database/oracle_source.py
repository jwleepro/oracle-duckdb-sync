"""
Oracle 데이터베이스 연결 관리 모듈
"""
import oracledb
import datetime
import os
from oracle_duckdb_sync.config import Config

# Thick 모드 초기화 (Oracle Client 라이브러리 사용)
# Oracle 11.2 이상 버전 지원
# TNS_ADMIN 환경 변수가 설정되어 있으면 해당 디렉토리의 sqlnet.ora를 사용
_oracle_client_initialized = False

def _ensure_oracle_client(config=None):
    """Oracle Client를 초기화합니다. 이미 초기화되었으면 무시합니다."""
    global _oracle_client_initialized
    if not _oracle_client_initialized:
        try:
            # Oracle Home 경로 확인
            oracle_home = os.environ.get('ORACLE_HOME')
            if not oracle_home:
                # config에서 경로 확인
                default_paths = []
                if config and config.oracle_client_directories:
                    default_paths = config.oracle_client_directories
                
                # Fallback defaults if config not provided
                if not default_paths:
                    default_paths = [
                        r'D:\instantclient_23_0',
                        r'C:\instantclient_23_0',
                        r'D:\oracle\instantclient',
                        r'C:\oracle\instantclient'
                    ]

                for path in default_paths:
                    if os.path.exists(path):
                        oracle_home = path
                        import logging
                        logger = logging.getLogger("OracleSource")
                        logger.info(f"ORACLE_HOME not set, using detected path: {oracle_home}")
                        break

                if not oracle_home:
                    raise ValueError(
                        "ORACLE_HOME environment variable not set and no Oracle Instant Client found. "
                        "Please set ORACLE_HOME or install Oracle Instant Client."
                    )

            lib_dir = os.path.join(oracle_home, 'bin') if os.path.exists(os.path.join(oracle_home, 'bin')) else oracle_home

            # TNS_ADMIN이 설정되어 있으면 해당 디렉토리를 사용
            config_dir = os.environ.get('TNS_ADMIN')

            if config_dir:
                oracledb.init_oracle_client(lib_dir=lib_dir, config_dir=config_dir)
            else:
                oracledb.init_oracle_client(lib_dir=lib_dir)
            _oracle_client_initialized = True

            import logging
            logger = logging.getLogger("OracleSource")
            logger.info(f"Oracle thick client initialized successfully (lib_dir: {lib_dir})")
        except Exception as e:
            # 이미 초기화되었거나 Oracle Client가 없는 경우
            # Thin 모드로 폴백 (Oracle 12.1 이상만 지원)
            import logging
            logger = logging.getLogger("OracleSource")
            logger.warning(f"Failed to initialize Oracle thick client: {e}")
            logger.warning("Falling back to thin mode (Oracle 12.1+ only)")
            logger.error(
                "ERROR: Your Oracle database version may not support thin mode. "
                "Please set ORACLE_HOME environment variable to use thick mode for Oracle 11g/11.2 compatibility."
            )

def datetime_handler(value):
    if isinstance(value, datetime.datetime):
        return value.isoformat()
    return value

class OracleSource:
    """Oracle 데이터베이스 연결 클래스"""

    def __init__(self, config: Config):
        """Oracle 연결 초기화

        Args:
            config (Config): Oracle 연결 정보
        """
        from oracle_duckdb_sync.log.logger import setup_logger
        
        self.config = config
        self.conn = None
        self.pool = None
        self.cursor = None
        self.current_query = None
        self.logger = setup_logger("OracleSource")

    def connect(self):
        """Oracle 데이터베이스에 연결

        Returns:
            oracledb.Connection: Oracle 연결 객체
        """
        try:
            # Oracle 11.2를 위해 Thick 모드 초기화
            _ensure_oracle_client(self.config)
            
            # DSN 연결 문자열 생성
            dsn = f"{self.config.oracle_host}:{self.config.oracle_port}/{self.config.oracle_service_name}"
            
            self.logger.info(f"Attempting connection to Oracle (Thick mode): {dsn}")
            self.logger.info(f"User: {self.config.oracle_user}")
            
            # Thick 모드로 연결 (Oracle 11.2 지원)
            # sqlnet.ora 파일 수정으로 ORA-12638 오류 해결됨
            self.conn = oracledb.connect(
                user=self.config.oracle_user,
                password=self.config.oracle_password,
                dsn=dsn
            )
            
            self.logger.info("Successfully connected to Oracle database")
            return self.conn
                
        except oracledb.DatabaseError as e:
            error_obj, = e.args
            self.logger.error(f"Oracle Database Error: {error_obj.code} - {error_obj.message}")
            self.logger.error(f"Connection details - DSN: {dsn}, User: {self.config.oracle_user}")
            
            # ORA-12638 특정 오류에 대한 추가 정보 제공
            if error_obj.code == 12638:
                self.logger.error("ORA-12638: Credential retrieval failed")
                self.logger.error("가능한 해결 방법:")
                self.logger.error("1. sqlnet.ora 파일에서 SQLNET.AUTHENTICATION_SERVICES 설정 확인")
                self.logger.error("2. SQLNET.AUTHENTICATION_SERVICES=(NONE) 또는 제거")
                self.logger.error("3. Oracle 서버의 인증 설정 확인")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during Oracle connection: {e}")
            raise

    def init_pool(self, min_conn=2, max_conn=10):
        dsn = f"{self.config.oracle_host}:{self.config.oracle_port}/{self.config.oracle_service_name}"
        self.pool = oracledb.create_pool(
            user=self.config.oracle_user,
            password=self.config.oracle_password,
            dsn=dsn,
            min=min_conn,
            max=max_conn,
            increment=1
        )
        return self.pool

    def disconnect(self):
        if self.cursor:
            self.cursor.close()
            self.cursor = None
        if self.conn:
            self.conn.close()
            self.conn = None
        if self.pool:
            self.pool.close()
            self.pool = None


    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False

    def fetch_all(self, query: str):
        if not self.conn:
            self.connect()
        with self.conn.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
            return [tuple(datetime_handler(v) for v in row) for row in rows]

    def fetch_batch(self, query: str, batch_size: int = 1000):
        """Fetch next batch from the query. Maintains cursor state for pagination."""
        if not self.conn:
            self.connect()

        # If this is a new query or different query, create new cursor
        if self.current_query != query:
            if self.cursor:
                self.cursor.close()
            self.cursor = self.conn.cursor()
            try:
                self.cursor.execute(query)
                self.current_query = query
            except Exception as e:
                # If execute fails, clean up cursor to prevent leak
                self.logger.error(f"Query execution failed: {e}")
                self.cursor.close()
                self.cursor = None
                self.current_query = None
                raise

        # Fetch next batch from existing cursor
        rows = self.cursor.fetchmany(batch_size)

        # If no more rows, close cursor and reset state
        if not rows:
            if self.cursor:
                self.cursor.close()
                self.cursor = None
            self.current_query = None

        return [tuple(datetime_handler(v) for v in row) for row in rows]

    def build_incremental_query(self, table_name: str, column_name: str, last_value: str):
        return f"SELECT * FROM {table_name} WHERE {column_name} > '{last_value}' ORDER BY {column_name} ASC"

    def get_table_schema(self, table_name: str):
        """Get table schema from Oracle data dictionary
        
        Args:
            table_name: Table name, can be "SCHEMA.TABLE" or just "TABLE"
        
        Returns:
            list: List of tuples (column_name, data_type)
        """
        # Ensure connection is established
        if not self.conn:
            self.connect()
        
        # Parse schema and table name
        if '.' in table_name:
            schema_name, table_only = table_name.split('.', 1)
            schema_name = schema_name.upper()
            table_only = table_only.upper()
        else:
            schema_name = None
            table_only = table_name.upper()
        
        # Build query based on whether schema is specified
        if schema_name:
            query = """
            SELECT column_name, data_type
            FROM all_tab_columns
            WHERE owner = :schema_name AND table_name = :table_name
            ORDER BY column_id
            """
            params = {"schema_name": schema_name, "table_name": table_only}
        else:
            query = """
            SELECT column_name, data_type
            FROM user_tab_columns
            WHERE table_name = :table_name
            ORDER BY column_id
            """
            params = {"table_name": table_only}
        
        cursor = self.conn.cursor()
        try:
            cursor.execute(query, params)
            return cursor.fetchall()
        finally:
            cursor.close()
