"""
스키마명 포함하여 Oracle 테이블 접근
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from oracle_duckdb_sync.config.config import load_config
from oracle_duckdb_sync.database.oracle_source import OracleSource
from oracle_duckdb_sync.log.logger import setup_logger

logger = setup_logger(__name__)

def main():
    config = load_config()

    try:
        oracle = OracleSource(config)
        oracle.connect()
        cursor = oracle.conn.cursor()

        # MESMGR 스키마로 접근
        logger.info("=== MESMGR.CRASIVTTST 접근 시도 ===")
        cursor.execute("SELECT COUNT(*) FROM MESMGR.CRASIVTTST")
        count = cursor.fetchone()[0]
        logger.info(f"MESMGR.CRASIVTTST 총 행 수: {count:,}")

        # 최근 데이터 확인
        cursor.execute("""
            SELECT MAX(TRAN_TIME) FROM MESMGR.CRASIVTTST
        """)
        max_time = cursor.fetchone()[0]
        logger.info(f"Oracle 최대 TRAN_TIME: {max_time}")

        # DuckDB 최대 시간과 비교
        logger.info("\n=== DuckDB와 비교 ===")
        logger.info("DuckDB 최대 TRAN_TIME: 20251231161436")

        # Oracle에서 DuckDB 이후 데이터 확인
        cursor.execute("""
            SELECT COUNT(*) FROM MESMGR.CRASIVTTST
            WHERE TRAN_TIME > '20251231161436'
        """)
        new_count = cursor.fetchone()[0]
        logger.info(f"DuckDB 이후 신규 데이터: {new_count:,} rows")

        cursor.close()
        oracle.disconnect()

    except Exception as e:
        logger.error(f"에러: {e}", exc_info=True)
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
