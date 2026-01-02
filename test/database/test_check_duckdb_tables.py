"""
DuckDB 테이블 확인 스크립트
"""
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from oracle_duckdb_sync.config.config import load_config
from oracle_duckdb_sync.database.duckdb_source import DuckDBSource
from oracle_duckdb_sync.log.logger import setup_logger

logger = setup_logger(__name__)

def main():
    """DuckDB 테이블 확인"""
    logger.info("=" * 80)
    logger.info("DuckDB 테이블 확인")
    logger.info("=" * 80)
    
    config = load_config()
    logger.info(f"DuckDB 파일: {config.duckdb_path}")
    logger.info(f"확인할 테이블: {config.sync_duckdb_table}")
    
    duckdb = None
    
    try:
        # DuckDB 연결
        logger.info("\nDuckDB 연결 중...")
        duckdb = DuckDBSource(config)
        logger.info("DuckDB 연결 성공")
        
        # 모든 테이블 목록 조회
        logger.info("\n모든 테이블 목록 조회 중...")
        cursor = duckdb.conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        
        logger.info(f"발견된 테이블 수: {len(tables)}")
        for table in tables:
            logger.info(f"  - {table[0]}")
        
        # 특정 테이블이 존재하면 데이터 확인
        if tables:
            target_table = config.sync_duckdb_table
            logger.info(f"\n'{target_table}' 테이블 데이터 확인 중...")
            
            # 테이블 행 수
            cursor.execute(f"SELECT COUNT(*) FROM {target_table}")
            count = cursor.fetchone()[0]
            logger.info(f"총 행 수: {count:,}")
            
            if count > 0:
                # 최근 데이터 샘플 조회
                logger.info(f"\n최근 데이터 샘플 (최대 5행):")
                cursor.execute(f"SELECT * FROM {target_table} LIMIT 5")
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                
                logger.info(f"컬럼: {', '.join(columns)}")
                for row in rows:
                    logger.info(f"  {row}")
                
                # 최근 TRAN_TIME 확인
                if 'TRAN_TIME' in columns or 'tran_time' in columns:
                    time_col = 'TRAN_TIME' if 'TRAN_TIME' in columns else 'tran_time'
                    cursor.execute(f"SELECT MAX({time_col}) FROM {target_table}")
                    max_time = cursor.fetchone()[0]
                    logger.info(f"\n최대 {time_col}: {max_time}")
        
        cursor.close()
        
    except Exception as e:
        logger.error(f"에러 발생: {e}", exc_info=True)
        return 1
        
    finally:
        if duckdb:
            duckdb.disconnect()
            logger.info("\nDuckDB 연결 종료")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
