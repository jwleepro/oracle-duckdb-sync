"""
증분 동기화 실행 테스트 스크립트
"""
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from oracle_duckdb_sync.config.config import load_config
from oracle_duckdb_sync.database.sync_engine import SyncEngine
from oracle_duckdb_sync.log.logger import setup_logger

logger = setup_logger(__name__)

def main():
    """증분 동기화 실행"""
    logger.info("=" * 80)
    logger.info("증분 동기화 테스트 시작")
    logger.info("=" * 80)

    # 설정 로드
    config = load_config()

    # Oracle 테이블명 (스키마 포함)
    if config.sync_oracle_schema:
        oracle_table_full = f"{config.sync_oracle_schema}.{config.sync_oracle_table}"
    else:
        oracle_table_full = config.sync_oracle_table

    logger.info(f"Oracle Schema: {config.sync_oracle_schema}")
    logger.info(f"Oracle Table: {config.sync_oracle_table}")
    logger.info(f"Oracle Full Name: {oracle_table_full}")
    logger.info(f"DuckDB Table: {config.sync_duckdb_table}")
    logger.info(f"Primary Key: {config.sync_primary_key}")
    logger.info(f"Time Column: {config.sync_time_column}")

    try:
        # SyncEngine 초기화 (내부에서 Oracle, DuckDB 자동 생성)
        logger.info("SyncEngine 초기화 중...")
        sync_engine = SyncEngine(config)
        logger.info("SyncEngine 초기화 성공")

        # Oracle 연결
        logger.info("Oracle 연결 중...")
        sync_engine.oracle.connect()
        logger.info("Oracle 연결 성공")

        # 현재 상태 확인
        state = sync_engine.load_state(config.sync_duckdb_table)
        if state:
            logger.info(f"현재 상태: last_sync_time={state.get('last_sync_time')}")
        else:
            logger.info("상태 파일 없음 - 첫 동기화 필요")

        # 증분 동기화 실행
        logger.info("=" * 80)
        logger.info("증분 동기화 실행 중...")
        logger.info("=" * 80)

        result = sync_engine.incremental_sync(
            oracle_table_name=oracle_table_full,
            duckdb_table=config.sync_duckdb_table,
            column=config.sync_time_column.split(',')[0].strip(),
            last_value=state.get('last_sync_time', '1900-01-01') if state else '1900-01-01',
            primary_key=config.sync_primary_key
        )

        # 결과 출력
        logger.info("=" * 80)
        logger.info("증분 동기화 완료!")
        logger.info("=" * 80)
        logger.info(f"처리된 행 수: {result.get('rows_synced', 0):,}")
        logger.info(f"배치 수: {result.get('batches', 0)}")
        logger.info(f"소요 시간: {result.get('elapsed_time', 0):.2f}초")

        if result.get('rows_synced', 0) > 0:
            rows_per_sec = result['rows_synced'] / result.get('elapsed_time', 1)
            logger.info(f"처리 속도: {rows_per_sec:,.0f} rows/sec")

        # 최종 상태 확인
        final_state = sync_engine.load_state(config.sync_duckdb_table)
        if final_state:
            logger.info(f"최종 상태: last_sync_time={final_state.get('last_sync_time')}")

    except Exception as e:
        logger.error(f"에러 발생: {e}", exc_info=True)
        return 1

    finally:
        # 연결 종료
        try:
            sync_engine.oracle.disconnect()
            logger.info("Oracle 연결 종료")
        except:
            pass
        try:
            sync_engine.duckdb.disconnect()
            logger.info("DuckDB 연결 종료")
        except:
            pass

    return 0

if __name__ == "__main__":
    sys.exit(main())
