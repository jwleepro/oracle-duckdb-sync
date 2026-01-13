"""
Oracle 테이블 확인 스크립트
"""
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from oracle_duckdb_sync.config.config import load_config
from oracle_duckdb_sync.database.oracle_source import OracleSource
from oracle_duckdb_sync.log.logger import setup_logger

logger = setup_logger(__name__)

def main():
    """Oracle 테이블 확인"""
    logger.info("=" * 80)
    logger.info("Oracle 테이블 확인")
    logger.info("=" * 80)

    config = load_config()
    logger.info(f"확인할 테이블: {config.sync_oracle_table}")

    oracle = None

    try:
        # Oracle 연결
        logger.info("Oracle 연결 중...")
        oracle = OracleSource(config)
        oracle.connect()
        logger.info("Oracle 연결 성공")

        # 테이블 목록 조회
        logger.info("모든 테이블 목록 조회 중...")
        query = """
        SELECT table_name
        FROM user_tables
        ORDER BY table_name
        """

        cursor = oracle.conn.cursor()
        cursor.execute(query)
        tables = cursor.fetchall()
        cursor.close()

        logger.info(f"발견된 테이블 수: {len(tables)}")
        for table in tables:
            logger.info(f"  - {table[0]}")

        # 설정된 테이블 존재 확인
        logger.info(f"\n'{config.sync_oracle_table}' 테이블 존재 확인 중...")
        query = f"""
        SELECT COUNT(*)
        FROM user_tables
        WHERE table_name = '{config.sync_oracle_table.upper()}'
        """

        cursor = oracle.conn.cursor()
        cursor.execute(query)
        count = cursor.fetchone()[0]
        cursor.close()

        if count > 0:
            logger.info(f"'{config.sync_oracle_table}' 테이블 존재함")

            # 테이블 구조 확인
            logger.info("\n테이블 구조:")
            query = f"""
            SELECT column_name, data_type, data_length, nullable
            FROM user_tab_columns
            WHERE table_name = '{config.sync_oracle_table.upper()}'
            ORDER BY column_id
            """

            cursor = oracle.conn.cursor()
            cursor.execute(query)
            columns = cursor.fetchall()
            cursor.close()

            for col in columns:
                logger.info(f"  - {col[0]}: {col[1]}({col[2]}) {'NULL' if col[3] == 'Y' else 'NOT NULL'}")

        else:
            logger.error(f"'{config.sync_oracle_table}' 테이블이 존재하지 않습니다!")

    except Exception as e:
        logger.error(f"에러 발생: {e}", exc_info=True)
        return 1

    finally:
        if oracle:
            oracle.disconnect()
            logger.info("\nOracle 연결 종료")

    return 0

if __name__ == "__main__":
    sys.exit(main())
