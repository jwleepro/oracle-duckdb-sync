"""
UI 핸들러 리팩토링 테스트

이 테스트는 중복 코드 제거 후에도 기능이 정확히 동작하는지 검증합니다.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from oracle_duckdb_sync.ui.handlers import (
    _validate_table_name,
    _acquire_sync_lock_with_ui,
    _start_sync_worker,
    _handle_sync_error
)


class TestValidateTableName:
    """테이블명 검증 헬퍼 함수 테스트"""
    
    @patch('oracle_duckdb_sync.ui.handlers.st')
    def test_empty_table_name_shows_warning(self, mock_st):
        """빈 테이블명은 경고를 표시하고 False를 반환한다"""
        result = _validate_table_name("")
        
        assert result is False
        mock_st.sidebar.warning.assert_called_once()
        assert "테이블명을 입력하세요" in mock_st.sidebar.warning.call_args[0][0]
    
    @patch('oracle_duckdb_sync.ui.handlers.st')
    def test_none_table_name_shows_warning(self, mock_st):
        """None 테이블명은 경고를 표시하고 False를 반환한다"""
        result = _validate_table_name(None)
        
        assert result is False
        mock_st.sidebar.warning.assert_called_once()
    
    @patch('oracle_duckdb_sync.ui.handlers.st')
    def test_valid_table_name_returns_true(self, mock_st):
        """유효한 테이블명은 경고 없이 True를 반환한다"""
        result = _validate_table_name("VALID_TABLE")
        
        assert result is True
        mock_st.sidebar.warning.assert_not_called()


class TestAcquireSyncLockWithUI:
    """락 획득 헬퍼 함수 테스트"""
    
    @patch('oracle_duckdb_sync.ui.handlers.st')
    def test_lock_already_acquired_shows_warning(self, mock_st):
        """이미 락이 걸려있으면 경고를 표시하고 None을 반환한다"""
        mock_lock = Mock()
        mock_lock.is_locked.return_value = True
        mock_lock.get_lock_info.return_value = {'pid': 12345}
        
        result = _acquire_sync_lock_with_ui(mock_lock)
        
        assert result is None
        mock_st.sidebar.warning.assert_called_once()
        assert "다른 동기화 작업이 실행 중입니다" in mock_st.sidebar.warning.call_args[0][0]
    
    @patch('oracle_duckdb_sync.ui.handlers.st')
    def test_lock_acquisition_failure_shows_error(self, mock_st):
        """락 획득 실패 시 에러를 표시하고 None을 반환한다"""
        mock_lock = Mock()
        mock_lock.is_locked.return_value = False
        mock_lock.acquire.return_value = False
        
        result = _acquire_sync_lock_with_ui(mock_lock)
        
        assert result is None
        mock_st.sidebar.error.assert_called_once()
        assert "잠금을 획득할 수 없습니다" in mock_st.sidebar.error.call_args[0][0]
    
    @patch('oracle_duckdb_sync.ui.handlers.st')
    def test_successful_lock_acquisition_returns_lock(self, mock_st):
        """락 획득 성공 시 락 객체를 반환한다"""
        mock_lock = Mock()
        mock_lock.is_locked.return_value = False
        mock_lock.acquire.return_value = True
        
        result = _acquire_sync_lock_with_ui(mock_lock)
        
        assert result is mock_lock
        mock_st.sidebar.warning.assert_not_called()
        mock_st.sidebar.error.assert_not_called()


class TestStartSyncWorker:
    """동기화 워커 시작 헬퍼 함수 테스트"""

    @patch('oracle_duckdb_sync.ui.handlers.st')
    @patch('oracle_duckdb_sync.ui.handlers.SyncWorker')
    def test_worker_starts_successfully(self, mock_worker_class, mock_st):
        """워커가 성공적으로 시작되면 세션 상태를 업데이트한다"""
        mock_st.session_state = Mock()
        mock_st.session_state.progress_queue = Mock()
        
        mock_config = Mock()
        mock_sync_params = {'sync_type': 'test'}
        mock_sync_lock = Mock()
        
        mock_worker = Mock()
        mock_worker_class.return_value = mock_worker
        
        _start_sync_worker(mock_config, mock_sync_params, mock_sync_lock)
        
        # Worker 생성 확인
        mock_worker_class.assert_called_once()
        mock_worker.start.assert_called_once()
        
        # 세션 상태 업데이트 확인
        assert mock_st.session_state.sync_worker == mock_worker
        assert mock_st.session_state.sync_status == 'running'
        assert mock_st.session_state.sync_progress == {}
        assert mock_st.session_state.sync_lock == mock_sync_lock
        
        # Rerun 호출 확인
        mock_st.rerun.assert_called_once()
    
    @patch('oracle_duckdb_sync.ui.handlers.st')
    @patch('oracle_duckdb_sync.ui.handlers.SyncWorker')
    def test_worker_sets_expected_rows_for_test_sync(self, mock_worker_class, mock_st):
        """테스트 동기화 시 expected_rows가 설정된다"""
        mock_st.session_state = Mock()
        mock_st.session_state.progress_queue = Mock()
        
        mock_config = Mock()
        mock_sync_params = {'sync_type': 'test', 'row_limit': 1000}
        mock_sync_lock = Mock()
        
        mock_worker = Mock()
        mock_worker_class.return_value = mock_worker
        
        _start_sync_worker(mock_config, mock_sync_params, mock_sync_lock)
        
        assert mock_worker.expected_rows == 1000


class TestHandleSyncError:
    """동기화 에러 처리 헬퍼 함수 테스트"""
    
    @patch('oracle_duckdb_sync.ui.handlers.st')
    @patch('oracle_duckdb_sync.ui.handlers.traceback')
    def test_error_releases_lock_and_shows_message(self, mock_traceback, mock_st):
        """에러 발생 시 락을 해제하고 에러 메시지를 표시한다"""
        mock_traceback.format_exc.return_value = "Traceback..."
        
        mock_sync_lock = Mock()
        exception = ValueError("Test error")
        
        _handle_sync_error(mock_sync_lock, exception)
        
        # 락 해제 확인
        mock_sync_lock.release.assert_called_once()
        
        # 에러 메시지 표시 확인
        mock_st.sidebar.error.assert_called_once()
        assert "동기화 시작 실패" in mock_st.sidebar.error.call_args[0][0]
    
    @patch('oracle_duckdb_sync.ui.handlers.st')
    @patch('oracle_duckdb_sync.ui.handlers.traceback')
    def test_error_displays_traceback(self, mock_traceback, mock_st):
        """에러 발생 시 상세 트레이스백을 표시한다"""
        mock_traceback.format_exc.return_value = "Detailed traceback"
        mock_expander = Mock()
        mock_st.sidebar.expander.return_value.__enter__ = Mock(return_value=mock_expander)
        mock_st.sidebar.expander.return_value.__exit__ = Mock(return_value=None)
        
        mock_sync_lock = Mock()
        exception = ValueError("Test error")
        
        _handle_sync_error(mock_sync_lock, exception)
        
        # Expander가 생성되고 트레이스백이 표시되는지 확인
        mock_st.sidebar.expander.assert_called_once_with("상세 에러 정보")
