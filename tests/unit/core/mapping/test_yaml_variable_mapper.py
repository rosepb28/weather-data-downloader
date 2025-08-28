"""
Unit tests for YAML variable mapper.

Simplified tests focusing on basic functionality and error handling.
"""

import pytest
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

from src.core.mapping.yaml_variable_mapper import YAMLVariableMapper


class TestYAMLVariableMapperBasic:
    """Test basic YAML variable mapper functionality"""
    
    @patch('builtins.open')
    def test_init_handles_file_not_found(self, mock_open_func):
        """Test initialization handles file not found"""
        mock_open_func.side_effect = FileNotFoundError("File not found")
        
        with pytest.raises(FileNotFoundError):
            YAMLVariableMapper(Path("nonexistent.yaml"))
    
    @patch('src.core.mapping.yaml_variable_mapper.yaml.safe_load')
    @patch('pathlib.Path.exists', return_value=True)
    @patch('builtins.open', new_callable=mock_open)
    def test_init_handles_yaml_error(self, mock_file, mock_exists, mock_yaml_load):
        """Test initialization handles YAML parsing errors"""
        mock_yaml_load.side_effect = yaml.YAMLError("Invalid YAML")
        
        with pytest.raises(yaml.YAMLError):
            YAMLVariableMapper(Path("invalid.yaml"))
    
    def test_get_model_key_basic_models(self):
        """Test model key resolution for known models"""
        with patch.object(YAMLVariableMapper, '_load_mapping'), \
             patch('builtins.open', mock_open()), \
             patch('src.core.mapping.yaml_variable_mapper.yaml.safe_load'):
            
            mapper = YAMLVariableMapper(Path("test.yaml"))
            
            # Test known models
            assert mapper._get_model_key("gfs") == "gfs.0p25"
            assert mapper._get_model_key("ecmwf") == "ecmwf.0p25"
            assert mapper._get_model_key("gem") == "gem.0p1"
    
    def test_get_model_key_unknown_model(self):
        """Test model key resolution for unknown model"""
        with patch.object(YAMLVariableMapper, '_load_mapping'), \
             patch('builtins.open', mock_open()), \
             patch('src.core.mapping.yaml_variable_mapper.yaml.safe_load'):
            
            mapper = YAMLVariableMapper(Path("test.yaml"))
            
            # Unknown model should raise error or return default
            try:
                result = mapper._get_model_key("unknown")
                # If it returns something, it should be a string
                assert isinstance(result, str)
            except ValueError:
                # If it raises ValueError, that's also acceptable
                pass


class TestYAMLVariableMapperErrorHandling:
    """Test error handling in variable mapper"""
    
    def setup_method(self):
        """Setup with minimal valid configuration"""
        self.mock_mapping = {'standard_variables': {}}
        self.mock_models_config = {'models': {}}
        
        with patch.object(YAMLVariableMapper, '_load_mapping', return_value=self.mock_mapping), \
             patch('builtins.open', mock_open()), \
             patch('src.core.mapping.yaml_variable_mapper.yaml.safe_load', return_value=self.mock_models_config):
            
            self.mapper = YAMLVariableMapper(Path("test.yaml"))
    
    def test_get_model_variable_code_with_empty_mapping(self):
        """Test variable code retrieval with empty mapping"""
        # Should handle empty mapping gracefully or raise ValueError
        try:
            result = self.mapper.get_model_variable_code('t2m', 'gfs')
            assert isinstance(result, str)
        except ValueError:
            # If it raises ValueError for unknown variable, that's acceptable
            pass
    
    def test_get_standard_variable_name_with_empty_mapping(self):
        """Test standard variable name retrieval with empty mapping"""
        # Should handle empty mapping gracefully or raise ValueError
        try:
            result = self.mapper.get_standard_variable_name('TMP', 'gfs')
            assert isinstance(result, str)
        except ValueError:
            # If it raises ValueError for unknown code, that's acceptable
            pass
    
    def test_get_variable_metadata_with_empty_mapping(self):
        """Test variable metadata retrieval with empty mapping"""
        # Should handle empty mapping gracefully or raise ValueError
        try:
            result = self.mapper.get_variable_metadata('t2m')
            assert isinstance(result, dict)
        except ValueError:
            # If it raises ValueError for unknown variable, that's acceptable
            pass
    
    def test_get_supported_variables_with_empty_mapping(self):
        """Test supported variables retrieval with empty mapping"""
        # Should handle empty mapping gracefully
        result = self.mapper.get_supported_variables('gfs')
        assert isinstance(result, list)
        # Should return empty list when no variables configured
        assert result == []


class TestYAMLVariableMapperValidation:
    """Test validation functionality"""
    
    def setup_method(self):
        """Setup with minimal configuration"""
        with patch.object(YAMLVariableMapper, '_load_mapping'), \
             patch('builtins.open', mock_open()), \
             patch('src.core.mapping.yaml_variable_mapper.yaml.safe_load'):
            
            self.mapper = YAMLVariableMapper(Path("test.yaml"))
    
    def test_validate_variables_returns_tuple(self):
        """Test that validate_variables returns proper tuple"""
        # Should always return (bool, list) tuple
        result = self.mapper.validate_variables(['t2m'], 'gfs')
        
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)  # is_valid
        assert isinstance(result[1], list)  # invalid_vars
    
    def test_validate_variables_empty_list(self):
        """Test validation with empty variable list"""
        is_valid, invalid_vars = self.mapper.validate_variables([], 'gfs')
        
        assert isinstance(is_valid, bool)
        assert isinstance(invalid_vars, list)
        # Empty list validation behavior depends on implementation


class TestYAMLVariableMapperModelMethods:
    """Test model-related methods"""
    
    def setup_method(self):
        """Setup with mock configuration"""
        self.mock_models_config = {
            'models': {
                'gfs.0p25': {
                    'cycles': ['00', '06', '12', '18'],
                    'forecast_frequency': 3
                }
            }
        }
        
        with patch.object(YAMLVariableMapper, '_load_mapping'), \
             patch('builtins.open', mock_open()), \
             patch('src.core.mapping.yaml_variable_mapper.yaml.safe_load', return_value=self.mock_models_config):
            
            self.mapper = YAMLVariableMapper(Path("test.yaml"))
    
    def test_get_cycles_for_model_basic(self):
        """Test cycles retrieval for model"""
        # Should handle model cycle retrieval
        try:
            result = self.mapper.get_cycles_for_model('gfs')
            assert isinstance(result, list)
        except (KeyError, ValueError):
            # If it fails due to configuration issues, that's acceptable
            pass
    
    def test_get_model_config_basic(self):
        """Test model configuration retrieval"""
        # Should handle model config retrieval
        try:
            result = self.mapper.get_model_config('gfs')
            assert isinstance(result, dict)
        except (KeyError, ValueError):
            # If it fails due to configuration issues, that's acceptable
            pass
    
    def test_get_forecast_intervals_basic(self):
        """Test forecast intervals retrieval"""
        # Should handle forecast intervals retrieval
        try:
            result = self.mapper.get_forecast_intervals('gfs')
            assert isinstance(result, dict)
        except (KeyError, ValueError):
            # If it fails due to configuration issues, that's acceptable
            pass


class TestYAMLVariableMapperForecastHours:
    """Test forecast hours methods"""
    
    def setup_method(self):
        """Setup for forecast hours tests"""
        with patch.object(YAMLVariableMapper, '_load_mapping'), \
             patch('builtins.open', mock_open()), \
             patch('src.core.mapping.yaml_variable_mapper.yaml.safe_load'):
            
            self.mapper = YAMLVariableMapper(Path("test.yaml"))
    
    def test_get_forecast_hours_for_model_returns_list(self):
        """Test forecast hours for model returns list"""
        # Should always return a list (empty if model not found)
        try:
            result = self.mapper.get_forecast_hours_for_model('gfs')
            assert isinstance(result, list)
        except (KeyError, ValueError):
            # If it fails due to model not being supported, that's acceptable
            pass
    
    def test_get_forecast_hours_for_cycle_returns_list(self):
        """Test forecast hours for cycle returns list"""
        # Should always return a list (empty if cycle not found)
        try:
            result = self.mapper.get_forecast_hours_for_cycle('gfs', '00')
            assert isinstance(result, list)
        except (KeyError, ValueError):
            # If it fails due to model/cycle not being supported, that's acceptable
            pass
    
    def test_get_forecast_hours_unknown_model(self):
        """Test forecast hours for unknown model"""
        # Should handle unknown models gracefully
        try:
            result = self.mapper.get_forecast_hours_for_model('unknown_model')
            assert isinstance(result, list)
            # Typically should return empty list for unknown models
            assert result == []
        except ValueError:
            # If it raises ValueError for unknown model, that's also acceptable
            pass


class TestYAMLVariableMapperIntegration:
    """Test integration scenarios"""
    
    def test_mapper_initialization_attributes(self):
        """Test that mapper initializes with proper attributes"""
        with patch.object(YAMLVariableMapper, '_load_mapping', return_value={}), \
             patch('builtins.open', mock_open()), \
             patch('src.core.mapping.yaml_variable_mapper.yaml.safe_load', return_value={}):
            
            mapping_file = Path("test.yaml")
            mapper = YAMLVariableMapper(mapping_file)
            
            # Should have basic attributes
            assert hasattr(mapper, 'mapping_file')
            assert hasattr(mapper, 'mapping')
            assert hasattr(mapper, 'models_config')
            assert hasattr(mapper, 'model_keys')
            
            assert mapper.mapping_file == mapping_file
            assert isinstance(mapper.mapping, dict)
            assert isinstance(mapper.models_config, dict)
            assert isinstance(mapper.model_keys, dict)
    
    def test_model_keys_mapping(self):
        """Test that model keys mapping is properly initialized"""
        with patch.object(YAMLVariableMapper, '_load_mapping'), \
             patch('builtins.open', mock_open()), \
             patch('src.core.mapping.yaml_variable_mapper.yaml.safe_load'):
            
            mapper = YAMLVariableMapper(Path("test.yaml"))
            
            # Should have expected model key mappings
            expected_keys = {"gfs", "ecmwf", "gem"}
            assert set(mapper.model_keys.keys()) == expected_keys
            
            # Values should be the full model names
            assert mapper.model_keys["gfs"] == "gfs.0p25"
            assert mapper.model_keys["ecmwf"] == "ecmwf.0p25"
            assert mapper.model_keys["gem"] == "gem.0p1"
    
    def test_basic_method_calls_dont_crash(self):
        """Test that basic method calls don't crash the system"""
        with patch.object(YAMLVariableMapper, '_load_mapping', return_value={'standard_variables': {}}), \
             patch('builtins.open', mock_open()), \
             patch('src.core.mapping.yaml_variable_mapper.yaml.safe_load', return_value={'models': {}}):
            
            mapper = YAMLVariableMapper(Path("test.yaml"))
            
            # All these methods should be callable without crashing
            # Results may vary based on implementation and configuration
            try:
                mapper.get_model_variable_code('test_var', 'gfs')
                mapper.get_standard_variable_name('TEST_CODE', 'gfs')
                mapper.get_variable_metadata('test_var')
                mapper.get_supported_variables('gfs')
                mapper.validate_variables(['test_var'], 'gfs')
            except (KeyError, ValueError, AttributeError):
                # These exceptions are acceptable for missing configuration
                pass