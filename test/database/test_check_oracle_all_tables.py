"""
Oracle 전체 테이블 확인 - 다른 스키마 포함
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

        # 1. 현재 사용자 확인
        cursor.execute("SELECT USER FROM DUAL")
        current_user = cursor.fetchone()[0]
        logger.info(f"현재 Oracle 사용자: {current_user}")

        # 2. user_tables (현재 스키마)
        logger.info("\n=== user_tables (현재 스키마) ===")
        cursor.execute("SELECT COUNT(*) FROM user_tables")
        count = cursor.fetchone()[0]
        logger.info(f"user_tables 테이블 수: {count}")

        if count > 0:
            cursor.execute("SELECT table_name FROM user_tables ORDER BY table_name")
            for row in cursor.fetchall():
                logger.info(f"  - {row[0]}")

        # 3. all_tables에서 CRASIVTTST 검색
        logger.info("\n=== all_tables에서 CRASIVTTST 검색 ===")
        cursor.execute("""
            SELECT owner, table_name
            FROM all_tables
            WHERE table_name LIKE '%CRASIV%' OR table_name LIKE '%IV%TST%'
            ORDER BY owner, table_name
        """)
        results = cursor.fetchall()
        logger.info(f"검색 결과: {len(results)}")
        for row in results:
            logger.info(f"  - {row[0]}.{row[1]}")

        # 4. 권한 확인
        logger.info("\n=== 테이블 SELECT 권한 ===")
        cursor.execute("""
            SELECT table_name, privilege
            FROM user_tab_privs
            WHERE privilege = 'SELECT'
        """)
        privs = cursor.fetchall()
        logger.info(f"SELECT 권한 테이블 수: {len(privs)}")
        for row in privs[:10]:
            logger.info(f"  - {row[0]}: {row[1]}")

        # 5. CRASIVTTST 직접 쿼리 시도 (다른 스키마 포함)
        logger.info("\n=== CRASIVTTST 직접 접근 시도 ===")
        try:
            cursor.execute("SELECT COUNT(*) FROM CRASIVTTST")
            count = cursor.fetchone()[0]
            logger.info(f"CRASIVTTST 행 수: {count}")
        except Exception as e:
            logger.error(f"CRASIVTTST 접근 실패: {e}")

        # 다른 스키마로 시도
        schemas = ['CRAS', 'MES', 'MESDB', 'SYS']
        for schema in schemas:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {schema}.CRASIVTTST")
                count = cursor.fetchone()[0]
                logger.info(f"{schema}.CRASIVTTST 행 수: {count}")
            except Exception:
                pass  # 스키마가 없으면 무시

        cursor.close()
        oracle.disconnect()

    except Exception as e:
        logger.error(f"에러: {e}", exc_info=True)
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
