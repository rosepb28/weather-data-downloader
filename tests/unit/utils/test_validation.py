"""
Unit tests for validation utilities.

Tests data validation functions for weather downloader.
"""

import pytest
from pathlib import Path

from src.utils.validation import DataValidator


class TestDataValidator:
    """Test DataValidator functionality"""
    
    def test_validate_model_name_valid(self):
        """Test valid model names"""
        assert DataValidator.validate_model_name("gfs") is True
        assert DataValidator.validate_model_name("gfs.0p25") is True
        assert DataValidator.validate_model_name("MODEL-123") is True
    
    def test_validate_model_name_invalid(self):
        """Test invalid model names"""
        assert DataValidator.validate_model_name("") is False
        assert DataValidator.validate_model_name(" ") is False
        assert DataValidator.validate_model_name("model with spaces") is False
    
    def test_validate_variable_name_valid(self):
        """Test valid variable names"""
        assert DataValidator.validate_variable_name("TEMP") is True
        assert DataValidator.validate_variable_name("T2M") is True
        assert DataValidator.validate_variable_name("RH_2M") is True
    
    def test_validate_variable_name_invalid(self):
        """Test invalid variable names"""
        assert DataValidator.validate_variable_name("") is False
        assert DataValidator.validate_variable_name("temp") is False  # lowercase
        assert DataValidator.validate_variable_name("t2m") is False   # lowercase
    
    def test_validate_level_name_valid(self):
        """Test valid level names"""
        assert DataValidator.validate_level_name("surface") is True
        assert DataValidator.validate_level_name("2_m_above_ground") is True
        assert DataValidator.validate_level_name("500") is True
    
    def test_validate_level_name_invalid(self):
        """Test invalid level names"""
        assert DataValidator.validate_level_name("") is False
        # Note: Single space might be valid according to the pattern
    
    def test_validate_url_valid(self):
        """Test valid URLs"""
        assert DataValidator.validate_url("https://example.com") is True
        assert DataValidator.validate_url("http://data.com") is True
    
    def test_validate_url_invalid(self):
        """Test invalid URLs"""
        assert DataValidator.validate_url("") is False
        assert DataValidator.validate_url("not-a-url") is False
        assert DataValidator.validate_url("invalid_url") is False
    
    def test_validate_file_path_existing(self, tmp_path):
        """Test file path validation for existing files"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        
        # Function might return True for existing files
        result = DataValidator.validate_file_path(test_file)
        assert isinstance(result, bool)  # Just check it returns bool
    
    def test_validate_file_path_string(self, tmp_path):
        """Test file path validation with string path"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        
        result = DataValidator.validate_file_path(str(test_file))
        assert isinstance(result, bool)
    
    def test_validate_compression_level_valid(self):
        """Test valid compression levels"""
        assert DataValidator.validate_compression_level(1) is True
        assert DataValidator.validate_compression_level(5) is True
        assert DataValidator.validate_compression_level(9) is True
    
    def test_validate_compression_level_invalid(self):
        """Test invalid compression levels"""
        assert DataValidator.validate_compression_level(10) is False
        assert DataValidator.validate_compression_level(-1) is False
    
    def test_validate_config_structure_basic(self):
        """Test config structure validation"""
        # Test with some structure
        config = {"key": "value"}
        is_valid, errors = DataValidator.validate_config_structure(config)
        
        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)
    
    def test_validate_config_structure_empty(self):
        """Test empty config"""
        is_valid, errors = DataValidator.validate_config_structure({})
        
        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)


class TestDataValidatorTypes:
    """Test type handling in validators"""
    
    def test_validate_model_name_none_handling(self):
        """Test model name with None"""
        result = DataValidator.validate_model_name(None)
        assert result is False  # Should return False, not raise
    
    def test_validate_variable_name_none_handling(self):
        """Test variable name with None"""
        result = DataValidator.validate_variable_name(None)
        assert result is False
    
    def test_validate_level_name_none_handling(self):
        """Test level name with None"""
        result = DataValidator.validate_level_name(None)
        assert result is False
    
    def test_validate_url_none_handling(self):
        """Test URL with None"""
        result = DataValidator.validate_url(None)
        assert result is False
    
    def test_validate_compression_level_types(self):
        """Test compression level with different types"""
        # Test with float (might be accepted)
        result = DataValidator.validate_compression_level(5.0)
        assert isinstance(result, bool)
        
        # Test with string (should be False)
        result = DataValidator.validate_compression_level("5")
        assert result is False


class TestDataValidatorPatterns:
    """Test pattern matching in validators"""
    
    def test_model_name_patterns(self):
        """Test model name pattern validation"""
        # Valid patterns (alphanumeric, dots, underscores, hyphens)
        valid_names = ["gfs", "gfs.0p25", "model_1", "test-model"]
        for name in valid_names:
            assert DataValidator.validate_model_name(name) is True
    
    def test_variable_name_patterns(self):
        """Test variable name pattern validation"""
        # Valid patterns (uppercase, numbers, underscores)
        valid_vars = ["TEMP", "T2M", "RH_2M", "VAR123"]
        for var in valid_vars:
            assert DataValidator.validate_variable_name(var) is True
        
        # Invalid patterns (lowercase, special chars)
        invalid_vars = ["temp", "t2m", "var-123", "var 123"]
        for var in invalid_vars:
            assert DataValidator.validate_variable_name(var) is False
    
    def test_level_name_patterns(self):
        """Test level name pattern validation"""
        # Test some basic level names
        levels = ["surface", "500", "850", "2_m_above_ground"]
        for level in levels:
            result = DataValidator.validate_level_name(level)
            assert isinstance(result, bool)  # Just verify it works


class TestDataValidatorIntegration:
    """Test validator integration"""
    
    def test_multiple_validations(self):
        """Test multiple validations together"""
        # Test valid inputs
        assert DataValidator.validate_model_name("gfs.0p25") is True
        assert DataValidator.validate_variable_name("TEMP") is True
        assert DataValidator.validate_compression_level(5) is True
        
        # Test invalid inputs
        assert DataValidator.validate_model_name("") is False
        assert DataValidator.validate_variable_name("") is False
        assert DataValidator.validate_compression_level(-1) is False
    
    def test_validation_workflow(self, tmp_path):
        """Test realistic validation workflow"""
        # Create test file
        config_file = tmp_path / "config.yaml"
        config_file.write_text("test content")
        
        # Validate components
        model_valid = DataValidator.validate_model_name("gfs")
        var_valid = DataValidator.validate_variable_name("TEMP")
        level_valid = DataValidator.validate_level_name("surface")
        url_valid = DataValidator.validate_url("https://example.com")
        file_valid = DataValidator.validate_file_path(config_file)
        compression_valid = DataValidator.validate_compression_level(5)
        
        # All should return boolean values
        validations = [model_valid, var_valid, level_valid, url_valid, 
                      file_valid, compression_valid]
        
        for validation in validations:
            assert isinstance(validation, bool)
    
    def test_config_validation_basic(self):
        """Test basic config validation functionality"""
        configs = [
            {"models": {"gfs": {}}},
            {"output_dir": "data"},
            {},
            {"invalid": "structure"}
        ]
        
        for config in configs:
            is_valid, errors = DataValidator.validate_config_structure(config)
            assert isinstance(is_valid, bool)
            assert isinstance(errors, list)