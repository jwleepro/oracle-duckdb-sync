"""Tests for StateFileManager - JSON file I/O with consistent error handling"""
import json
import os
import tempfile
import pytest
from oracle_duckdb_sync.state_file_manager import StateFileManager


class TestStateFileManager:
    """Test suite for StateFileManager class"""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            yield tmp_dir

    @pytest.fixture
    def manager(self):
        """Create a StateFileManager instance"""
        import logging
        logger = logging.getLogger("test")
        return StateFileManager(logger)

    def test_save_json_creates_file(self, manager, temp_dir):
        """Test that save_json creates a file with correct data"""
        file_path = os.path.join(temp_dir, "test.json")
        data = {"key": "value", "number": 42}
        
        result = manager.save_json(file_path, data)
        
        assert result is True
        assert os.path.exists(file_path)
        
        with open(file_path, "r") as f:
            loaded = json.load(f)
        assert loaded == data

    def test_save_json_creates_directory_if_not_exists(self, manager, temp_dir):
        """Test that save_json creates parent directories"""
        file_path = os.path.join(temp_dir, "subdir", "test.json")
        data = {"key": "value"}
        
        result = manager.save_json(file_path, data)
        
        assert result is True
        assert os.path.exists(file_path)

    def test_save_json_overwrites_existing_file(self, manager, temp_dir):
        """Test that save_json overwrites existing file"""
        file_path = os.path.join(temp_dir, "test.json")
        
        # Save initial data
        manager.save_json(file_path, {"old": "data"})
        
        # Overwrite with new data
        new_data = {"new": "data"}
        result = manager.save_json(file_path, new_data)
        
        assert result is True
        with open(file_path, "r") as f:
            loaded = json.load(f)
        assert loaded == new_data

    def test_load_json_returns_data(self, manager, temp_dir):
        """Test that load_json returns correct data"""
        file_path = os.path.join(temp_dir, "test.json")
        data = {"key": "value", "number": 42}
        
        with open(file_path, "w") as f:
            json.dump(data, f)
        
        result = manager.load_json(file_path)
        
        assert result == data

    def test_load_json_returns_default_if_file_not_found(self, manager, temp_dir):
        """Test that load_json returns default data when file doesn't exist"""
        file_path = os.path.join(temp_dir, "nonexistent.json")
        default = {"default": "value"}
        
        result = manager.load_json(file_path, default_data=default)
        
        assert result == default

    def test_load_json_returns_empty_dict_if_no_default(self, manager, temp_dir):
        """Test that load_json returns empty dict when no default provided"""
        file_path = os.path.join(temp_dir, "nonexistent.json")
        
        result = manager.load_json(file_path)
        
        assert result == {}

    def test_load_json_handles_corrupted_json(self, manager, temp_dir):
        """Test that load_json handles corrupted JSON files"""
        file_path = os.path.join(temp_dir, "corrupted.json")
        
        with open(file_path, "w") as f:
            f.write("{ invalid json }")
        
        default = {"default": "value"}
        result = manager.load_json(file_path, default_data=default)
        
        assert result == default

    def test_save_json_handles_io_error(self, manager, temp_dir):
        """Test that save_json handles I/O errors gracefully"""
        # Try to write to a file that can't be created (use a directory as filename)
        file_path = os.path.join(temp_dir, "dir_as_file")
        os.makedirs(file_path)  # Create directory first
        
        # Now try to write to that directory as if it were a file
        result = manager.save_json(file_path, {"data": "test"})
        
        assert result is False

    def test_save_json_formats_with_indent(self, manager, temp_dir):
        """Test that save_json formats JSON with proper indentation"""
        file_path = os.path.join(temp_dir, "test.json")
        data = {"key": "value"}
        
        manager.save_json(file_path, data)
        
        with open(file_path, "r") as f:
            content = f.read()
        
        # Check that it's indented (has newlines and spaces)
        assert "\n" in content
        assert "  " in content
