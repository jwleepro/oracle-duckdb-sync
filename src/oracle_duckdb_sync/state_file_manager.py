"""StateFileManager - Centralized JSON file I/O with consistent error handling"""
import json
import os
from typing import Optional


class StateFileManager:
    """Base class for JSON state file operations with consistent error handling."""

    def __init__(self, logger):
        """Initialize StateFileManager with a logger.
        
        Args:
            logger: Logger instance for recording operations and errors
        """
        self.logger = logger

    def save_json(self, file_path: str, data: dict, default_data: Optional[dict] = None) -> bool:
        """Save data to JSON file with consistent error handling.
        
        Args:
            file_path: Path to the JSON file
            data: Dictionary data to save
            default_data: Not used in save, kept for API consistency
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create parent directories if they don't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except (FileNotFoundError, json.JSONDecodeError, IOError) as e:
            self.logger.error(f"Failed to save {file_path}: {e}")
            return False

    def load_json(self, file_path: str, default_data: Optional[dict] = None) -> dict:
        """Load data from JSON file with consistent error handling.
        
        Args:
            file_path: Path to the JSON file
            default_data: Default data to return if file doesn't exist or is corrupted
            
        Returns:
            dict: Loaded data, or default_data if error occurs
        """
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.warning(f"File not found: {file_path}, using default")
            return default_data or {}
        except (json.JSONDecodeError, IOError) as e:
            self.logger.error(f"Failed to load {file_path}: {e}")
            return default_data or {}
