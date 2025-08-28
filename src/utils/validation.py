"""
Validation utilities for the weather data downloader system.

This module provides utilities for validating data, parameters,
and configurations.
"""

from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import re


class DataValidator:
    """Utilities for data validation."""
    
    @staticmethod
    def validate_model_name(model_name: str) -> bool:
        """
        Validate weather model name format.
        
        Args:
            model_name: Model name to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not model_name or not isinstance(model_name, str):
            return False
        
        # Allow alphanumeric characters, dots, and underscores
        pattern = r'^[a-zA-Z0-9._-]+$'
        return bool(re.match(pattern, model_name))
    
    @staticmethod
    def validate_variable_name(variable: str) -> bool:
        """
        Validate variable name format.
        
        Args:
            variable: Variable name to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not variable or not isinstance(variable, str):
            return False
        
        # Allow uppercase letters and numbers
        pattern = r'^[A-Z0-9_]+$'
        return bool(re.match(pattern, variable))
    
    @staticmethod
    def validate_level_name(level: str) -> bool:
        """
        Validate level name format.
        
        Args:
            level: Level name to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not level or not isinstance(level, str):
            return False
        
        # Allow alphanumeric characters, spaces, and common separators
        pattern = r'^[a-zA-Z0-9\s._-]+$'
        return bool(re.match(pattern, level))
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """
        Validate URL format.
        
        Args:
            url: URL to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not url or not isinstance(url, str):
            return False
        
        # Basic URL validation
        pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        return bool(re.match(pattern, url))
    
    @staticmethod
    def validate_file_path(path: Union[str, Path]) -> bool:
        """
        Validate file path.
        
        Args:
            path: Path to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            path_obj = Path(path)
            # Check if path is absolute or can be resolved
            return path_obj.is_absolute() or path_obj.resolve() is not None
        except (OSError, RuntimeError):
            return False
    
    @staticmethod
    def validate_compression_level(level: int) -> bool:
        """
        Validate compression level.
        
        Args:
            level: Compression level to validate
            
        Returns:
            True if valid, False otherwise
        """
        return isinstance(level, int) and 0 <= level <= 9
    
    @staticmethod
    def validate_config_structure(config: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate configuration structure.
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        required_keys = ['models', 'processing', 'storage']
        
        # Check required top-level keys
        for key in required_keys:
            if key not in config:
                errors.append(f"Missing required key: {key}")
        
        if errors:
            return False, errors
        
        # Validate models section
        if 'models' in config:
            if not isinstance(config['models'], dict):
                errors.append("'models' must be a dictionary")
            else:
                for model_name, model_config in config['models'].items():
                    if not DataValidator.validate_model_name(model_name):
                        errors.append(f"Invalid model name: {model_name}")
                    
                    if isinstance(model_config, dict):
                        required_model_keys = ['name', 'resolution', 'base_url']
                        for req_key in required_model_keys:
                            if req_key not in model_config:
                                errors.append(f"Missing required key in {model_name}: {req_key}")
        
        # Validate processing section
        if 'processing' in config:
            if not isinstance(config['processing'], dict):
                errors.append("'processing' must be a dictionary")
        
        # Validate storage section
        if 'storage' in config:
            if not isinstance(config['storage'], dict):
                errors.append("'storage' must be a dictionary")
            else:
                if 'base_path' in config['storage']:
                    if not DataValidator.validate_file_path(config['storage']['base_path']):
                        errors.append("Invalid base_path in storage configuration")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_download_parameters(
        model_name: str,
        date: str,
        cycle: str,
        forecast_hour: int
    ) -> tuple[bool, List[str]]:
        """
        Validate download parameters.
        
        Args:
            model_name: Name of the weather model
            date: Date in YYYYMMDD format
            cycle: Forecast cycle
            forecast_hour: Forecast hour
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        if not DataValidator.validate_model_name(model_name):
            errors.append(f"Invalid model name: {model_name}")
        
        # Date validation is handled by TimeRangeManager
        # Cycle validation is handled by CycleManager
        # Forecast hour validation is handled by ForecastManager
        
        return len(errors) == 0, errors
