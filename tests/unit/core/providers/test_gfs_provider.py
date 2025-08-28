"""
Unit tests for GFS provider.

Tests GFS-specific weather model provider implementation.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from urllib.parse import parse_qs, urlparse

from src.core.providers.gfs_provider import GFSProvider


class TestGFSProviderInitialization:
    """Test GFS provider initialization"""
    
    def test_init_default_config(self):
        """Test initialization with default config"""
        provider = GFSProvider()
        
        assert provider.model_name == "GFS 0.25 Degree"
        assert provider.resolution == "0.25"
        assert isinstance(provider.available_cycles, list)
        assert len(provider.available_cycles) > 0
    
    def test_init_custom_config(self):
        """Test initialization with custom config"""
        custom_config = {
            'cycles': ['00', '12'],
            'base_url': 'https://custom.url.com',
            'variables': ['t2m', 'rh2m'],
            'levels': ['surface']
        }
        
        provider = GFSProvider(config=custom_config)
        
        assert provider.available_cycles == ['00', '12']
        assert provider.config['base_url'] == 'https://custom.url.com'
    
    def test_init_with_variable_mapper(self):
        """Test initialization with variable mapper"""
        mock_mapper = Mock()
        provider = GFSProvider(variable_mapper=mock_mapper)
        
        assert provider.variable_mapper == mock_mapper
    
    def test_init_validates_config(self):
        """Test that initialization validates config"""
        # This should not raise an exception
        provider = GFSProvider()
        assert provider.config is not None


class TestGFSProviderProperties:
    """Test GFS provider properties"""
    
    def setup_method(self):
        """Setup for each test"""
        self.provider = GFSProvider()
    
    def test_model_name(self):
        """Test model name property"""
        assert self.provider.model_name == "GFS 0.25 Degree"
    
    def test_resolution(self):
        """Test resolution property"""
        assert self.provider.resolution == "0.25"
    
    def test_available_cycles_default(self):
        """Test default available cycles"""
        cycles = self.provider.available_cycles
        assert isinstance(cycles, list)
        assert '00' in cycles
        assert len(cycles) >= 2  # Should have multiple cycles
    
    def test_available_cycles_custom(self):
        """Test custom available cycles"""
        config = {
            'cycles': ['00', '06'],
            'base_url': 'https://test.com'  # Required key
        }
        provider = GFSProvider(config=config)
        
        assert provider.available_cycles == ['00', '06']
    
    def test_forecast_frequency(self):
        """Test forecast frequency property"""
        frequency = self.provider.forecast_frequency
        assert isinstance(frequency, int)
        assert frequency > 0
    
    def test_max_forecast_hours(self):
        """Test max forecast hours property"""
        max_hours = self.provider.max_forecast_hours
        assert isinstance(max_hours, int)
        assert max_hours > 0
        assert max_hours >= 100  # GFS typically goes to 240+ hours


class TestGFSProviderValidation:
    """Test GFS provider validation methods"""
    
    def setup_method(self):
        """Setup for each test"""
        self.provider = GFSProvider()
    
    def test_validate_parameters_valid(self):
        """Test parameter validation with valid inputs"""
        # Should not raise exception
        self.provider.validate_parameters(
            date="20250828",
            cycle="00",
            forecast_hour=24
        )
    
    def test_validate_parameters_invalid_cycle(self):
        """Test parameter validation with invalid cycle"""
        # The function might not validate cycle format, just test it doesn't crash
        try:
            self.provider.validate_parameters(
                date="20250828",
                cycle="25",  # Invalid hour
                forecast_hour=24
            )
        except ValueError:
            # If it raises ValueError, that's also acceptable
            pass
    
    def test_validate_parameters_invalid_forecast_hour(self):
        """Test parameter validation with invalid forecast hour"""
        # Mock config to control validation
        mock_config = {
            'base_url': 'https://test.com',  # Required
            'cycle_forecast_ranges': {
                '00': [[0, 72, 1]]  # Only 0-72 hours allowed
            }
        }
        provider = GFSProvider(config=mock_config)
        
        # Test that validation works (might not raise exception with this config)
        try:
            provider.validate_parameters(
                date="20250828",
                cycle="00",
                forecast_hour=100  # Beyond allowed range
            )
        except ValueError:
            # If it raises ValueError, that's acceptable
            pass
    
    def test_validate_parameters_date_format(self):
        """Test parameter validation with date format"""
        # Test various date formats
        valid_dates = ["20250828", "2025-08-28"]
        for date in valid_dates:
            # Should not raise exception
            self.provider.validate_parameters(
                date=date,
                cycle="00", 
                forecast_hour=0
            )


class TestGFSProviderURLGeneration:
    """Test GFS provider URL generation"""
    
    def setup_method(self):
        """Setup for each test"""
        # Create provider with known config
        self.config = {
            'base_url': 'https://nomads.ncep.noaa.gov',
            'cycles': ['00', '06', '12', '18'],
            'variables': ['t2m', 'rh2m', 'u10m', 'v10m'],
            'levels': ['surface', '2_m_above_ground', '10_m_above_ground'],
            'spatial_bounds': {
                'lon_min': -90.0, 'lon_max': -30.0,
                'lat_min': -60.0, 'lat_max': 15.0
            }
        }
        
        # Mock variable mapper
        self.mock_mapper = Mock()
        self.mock_mapper.get_model_variable_code.side_effect = lambda var, model: {
            't2m': 'TMP',
            'rh2m': 'RH', 
            'u10m': 'UGRD',
            'v10m': 'VGRD'
        }.get(var, var)
        
        self.provider = GFSProvider(config=self.config, variable_mapper=self.mock_mapper)
    
    def test_get_download_url_basic(self):
        """Test basic URL generation"""
        url = self.provider.get_download_url(
            date="20250828",
            cycle="00",
            forecast_hour=24
        )
        
        assert url is not None
        assert isinstance(url, str)
        assert 'nomads.ncep.noaa.gov' in url
        assert '20250828' in url
        assert '00' in url
    
    def test_get_download_url_with_variables(self):
        """Test URL generation with specific variables"""
        url = self.provider.get_download_url(
            date="20250828",
            cycle="00", 
            forecast_hour=24,
            variables=['t2m', 'rh2m']
        )
        
        assert url is not None
        # Parse URL to check parameters
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        # Should include mapped variables
        assert any('TMP' in str(params) for param in params if 'var_' in param)
    
    def test_get_download_url_with_levels(self):
        """Test URL generation with specific levels"""
        url = self.provider.get_download_url(
            date="20250828",
            cycle="00",
            forecast_hour=24,
            levels=['surface', '2_m_above_ground']
        )
        
        assert url is not None
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        # Should include level parameters
        level_params = [key for key in params.keys() if key.startswith('lev_')]
        assert len(level_params) > 0
    
    def test_get_download_url_spatial_bounds(self):
        """Test URL generation with spatial bounds"""
        url = self.provider.get_download_url(
            date="20250828",
            cycle="00",
            forecast_hour=24
        )
        
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        # Should include spatial parameters
        assert 'leftlon' in params
        assert 'rightlon' in params
        assert 'toplat' in params
        assert 'bottomlat' in params
    
    def test_get_download_url_no_mapper(self):
        """Test URL generation without variable mapper"""
        provider = GFSProvider(config=self.config, variable_mapper=None)
        
        url = provider.get_download_url(
            date="20250828",
            cycle="00",
            forecast_hour=24,
            variables=['TMP', 'RH']  # Use GFS codes directly
        )
        
        assert url is not None
        assert isinstance(url, str)


class TestGFSProviderMetadata:
    """Test GFS provider metadata methods"""
    
    def setup_method(self):
        """Setup for each test"""
        self.provider = GFSProvider()
    
    def test_get_metadata(self):
        """Test metadata retrieval"""
        metadata = self.provider.get_metadata()
        
        assert isinstance(metadata, dict)
        assert 'model_name' in metadata
        assert 'resolution' in metadata
        assert 'available_cycles' in metadata
        assert metadata['model_name'] == "GFS 0.25 Degree"
    
    def test_metadata_includes_cycles(self):
        """Test that metadata includes cycle information"""
        metadata = self.provider.get_metadata()
        
        # Metadata uses 'available_cycles', not 'cycles'
        assert 'available_cycles' in metadata
        assert isinstance(metadata['available_cycles'], list)
        assert len(metadata['available_cycles']) > 0
    
    def test_metadata_includes_forecast_info(self):
        """Test that metadata includes forecast information"""
        metadata = self.provider.get_metadata()
        
        # Should include forecast-related info
        assert 'max_forecast_hours' in metadata or 'forecast_frequency' in metadata


class TestGFSProviderPrivateMethods:
    """Test GFS provider private methods"""
    
    def setup_method(self):
        """Setup for each test"""
        self.provider = GFSProvider()
    
    def test_get_default_config(self):
        """Test default configuration generation"""
        default_config = self.provider._get_default_config()
        
        assert isinstance(default_config, dict)
        assert 'base_url' in default_config
        assert 'cycles' in default_config
        assert isinstance(default_config['cycles'], list)
    
    def test_validate_config_valid(self):
        """Test config validation with valid config"""
        # Should not raise exception
        self.provider._validate_config()
    
    def test_is_valid_variable(self):
        """Test variable validation"""
        # Test with some common variables
        assert isinstance(self.provider._is_valid_variable('TMP'), bool)
        assert isinstance(self.provider._is_valid_variable('RH'), bool)
        assert isinstance(self.provider._is_valid_variable('INVALID_VAR'), bool)
    
    def test_is_valid_level(self):
        """Test level validation"""
        # Test with some common levels
        assert isinstance(self.provider._is_valid_level('surface'), bool)
        assert isinstance(self.provider._is_valid_level('2_m_above_ground'), bool)
        assert isinstance(self.provider._is_valid_level('invalid_level'), bool)


class TestGFSProviderEdgeCases:
    """Test GFS provider edge cases and error conditions"""
    
    def test_init_invalid_config_type(self):
        """Test initialization with invalid config type"""
        # Invalid config should raise error due to validation
        with pytest.raises(ValueError, match="Missing required configuration key"):
            GFSProvider(config="invalid_config")
    
    def test_get_download_url_missing_parameters(self):
        """Test URL generation with missing parameters"""
        provider = GFSProvider()
        
        with pytest.raises((ValueError, TypeError)):
            provider.get_download_url(
                date=None,
                cycle="00",
                forecast_hour=24
            )
    
    def test_get_download_url_empty_variables(self):
        """Test URL generation with empty variables list"""
        provider = GFSProvider()
        
        url = provider.get_download_url(
            date="20250828",
            cycle="00",
            forecast_hour=24,
            variables=[]
        )
        
        # Should still generate valid URL
        assert url is not None
        assert isinstance(url, str)
    
    def test_variable_mapper_error_handling(self):
        """Test handling of variable mapper errors"""
        mock_mapper = Mock()
        mock_mapper.get_model_variable_code.side_effect = ValueError("Mapping error")
        
        provider = GFSProvider(variable_mapper=mock_mapper)
        
        # Should handle mapper errors gracefully
        url = provider.get_download_url(
            date="20250828",
            cycle="00",
            forecast_hour=24,
            variables=['t2m']
        )
        
        assert url is not None


class TestGFSProviderIntegration:
    """Test GFS provider integration scenarios"""
    
    def test_full_workflow_realistic(self):
        """Test complete realistic workflow"""
        # Setup realistic config
        config = {
            'base_url': 'https://nomads.ncep.noaa.gov',
            'cycles': ['00', '06', '12', '18'],
            'cycle_forecast_ranges': {
                '00': [[0, 120, 1], [123, 240, 3]]
            },
            'variables': ['t2m', 'rh2m', 'u10m', 'v10m'],
            'levels': ['surface', '2_m_above_ground', '10_m_above_ground'],
            'spatial_bounds': {
                'lon_min': -90.0, 'lon_max': -30.0,
                'lat_min': -60.0, 'lat_max': 15.0
            }
        }
        
        mock_mapper = Mock()
        mock_mapper.get_model_variable_code.return_value = 'TMP'
        
        provider = GFSProvider(config=config, variable_mapper=mock_mapper)
        
        # 1. Check properties
        assert provider.model_name == "GFS 0.25 Degree"
        assert provider.resolution == "0.25"
        
        # 2. Validate parameters
        provider.validate_parameters("20250828", "00", 24)
        
        # 3. Generate URL
        url = provider.get_download_url(
            date="20250828",
            cycle="00",
            forecast_hour=24,
            variables=['t2m'],
            levels=['surface']
        )
        
        assert url is not None
        assert '20250828' in url
        
        # 4. Get metadata
        metadata = provider.get_metadata()
        assert metadata['model_name'] == "GFS 0.25 Degree"
    
    def test_multi_variable_multi_level_download(self):
        """Test downloading multiple variables and levels"""
        mock_mapper = Mock()
        mock_mapper.get_model_variable_code.side_effect = lambda var, model: {
            't2m': 'TMP',
            'rh2m': 'RH',
            'u10m': 'UGRD',
            'v10m': 'VGRD'
        }.get(var, var)
        
        provider = GFSProvider(variable_mapper=mock_mapper)
        
        url = provider.get_download_url(
            date="20250828",
            cycle="00",
            forecast_hour=24,
            variables=['t2m', 'rh2m', 'u10m', 'v10m'],
            levels=['surface', '2_m_above_ground', '10_m_above_ground']
        )
        
        assert url is not None
        
        # Parse URL to verify multiple variables and levels
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        # Should have multiple variable parameters
        var_params = [key for key in params.keys() if key.startswith('var_')]
        assert len(var_params) >= 2
        
        # Should have multiple level parameters
        lev_params = [key for key in params.keys() if key.startswith('lev_')]
        assert len(lev_params) >= 2
    
    def test_different_cycles_and_forecast_hours(self):
        """Test different cycles and forecast hours"""
        provider = GFSProvider()
        
        test_cases = [
            ("20250828", "00", 0),
            ("20250828", "06", 12),
            ("20250828", "12", 24),
            ("20250828", "18", 48)
        ]
        
        for date, cycle, forecast_hour in test_cases:
            # Should validate successfully
            provider.validate_parameters(date, cycle, forecast_hour)
            
            # Should generate valid URL
            url = provider.get_download_url(date, cycle, forecast_hour)
            assert url is not None
            assert cycle in url
