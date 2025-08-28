"""
Global pytest configuration and fixtures for weather-data-downloader tests.

This module provides shared fixtures and configuration for all tests.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime, timezone
import yaml
import xarray as xr
import numpy as np
import pandas as pd

# ============================================================================
# FIXTURES GLOBALES
# ============================================================================

@pytest.fixture(scope="session")
def test_data_dir():
    """Directory containing test data files"""
    return Path(__file__).parent / "fixtures"

@pytest.fixture(scope="session") 
def temp_dir():
    """Temporary directory for test files"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)

@pytest.fixture
def mock_config():
    """Standard test configuration"""
    return {
        'output_dir': 'test_data',
        'spatial_bounds': {
            'lon_min': -90.0, 'lon_max': -30.0,
            'lat_min': -60.0, 'lat_max': 15.0
        },
        'processing': {
            'target_frequency': '1H',
            'compression': {'enabled': True, 'level': 5},
            'workers': 2,
            'chunk_size': '100MB',
            'netcdf': {'chunking': True, 'shuffle': True, 'fletcher32': True}
        },
        'download': {
            'retry_attempts': 3,
            'timeout': 30,
            'concurrent_downloads': 4
        }
    }

@pytest.fixture
def mock_models_config():
    """Standard models configuration"""
    return {
        'gfs.0p25': {
            'name': 'GFS 0.25 Degree',
            'resolution': '0.25°',
            'base_url': 'https://nomads.ncep.noaa.gov',
            'data_source': 'NOMADS',
            'cycles': ['00', '06', '12', '18'],
            'cycle_forecast_ranges': {
                '00': [[0, 120, 1], [123, 240, 3]],
                '06': [[0, 120, 1], [123, 240, 3]],
                '12': [[0, 120, 1], [123, 240, 3]], 
                '18': [[0, 120, 1], [123, 240, 3]]
            },
            'max_forecast_hours': 240,
            'availability_delays': {
                '00': 300, '06': 300, '12': 300, '18': 300
            },
            'download_format': 'grib2',
            'file_extension': '.grb2',
            'final_format': 'netcdf'
        }
    }

@pytest.fixture
def mock_variables_mapping():
    """Standard variables mapping configuration"""
    return {
        'standard_variables': {
            't2m': {'description': '2m Temperature', 'units': 'K'},
            'rh2m': {'description': '2m Relative Humidity', 'units': '%'},
            'u10m': {'description': '10m U Wind', 'units': 'm/s'},
            'v10m': {'description': '10m V Wind', 'units': 'm/s'},
            'hgt': {'description': 'Surface Height', 'units': 'm'}
        },
        'model_mappings': {
            'gfs': {
                't2m': 'TMP',
                'rh2m': 'RH', 
                'u10m': 'UGRD',
                'v10m': 'VGRD',
                'hgt': 'HGT'
            }
        }
    }

@pytest.fixture
def sample_xarray_dataset():
    """Sample xarray dataset for testing"""
    # Fixed random seed for reproducible tests
    np.random.seed(42)
    
    time = pd.date_range('2025-01-01T00:00:00', periods=5, freq='h')
    lat = np.linspace(15, -60, 76)  # South America latitudes
    lon = np.linspace(-90, -30, 61)  # South America longitudes
    
    # Create realistic weather data
    temp_data = 280 + 10 * np.random.random((5, 76, 61))  # Temperature: 280-290K
    rh_data = 20 + 60 * np.random.random((5, 76, 61))     # RH: 20-80%
    u_data = 5 * np.random.random((5, 76, 61)) - 2.5      # U wind: -2.5 to 2.5 m/s
    v_data = 5 * np.random.random((5, 76, 61)) - 2.5      # V wind: -2.5 to 2.5 m/s
    height_data = 1000 * np.random.random((76, 61))       # Height: 0-1000m
    
    dataset = xr.Dataset({
        't2m': (['time', 'latitude', 'longitude'], temp_data),
        'r2': (['time', 'latitude', 'longitude'], rh_data),
        'u10': (['time', 'latitude', 'longitude'], u_data),
        'v10': (['time', 'latitude', 'longitude'], v_data),
        'orog': (['latitude', 'longitude'], height_data),
    }, coords={
        'time': time, 
        'latitude': lat, 
        'longitude': lon
    })
    
    # Add attributes
    dataset.attrs = {
        'source': 'Test dataset',
        'created': '2025-01-01T00:00:00Z'
    }
    
    return dataset

@pytest.fixture
def sample_grib_files(tmp_path):
    """Create mock GRIB files for testing"""
    grib_files = []
    for i in range(3):
        grib_file = tmp_path / f"gfs.t00z.pgrb2.0p25.f{i:03d}"
        # Create mock binary content (GRIB2 magic bytes + dummy data)
        mock_content = b'GRIB' + b'\x00' * 100 + b'7777'  # GRIB2 format
        grib_file.write_bytes(mock_content)
        grib_files.append(grib_file)
    return grib_files

# ============================================================================
# MOCK PATCHES GLOBALES
# ============================================================================

@pytest.fixture
def mock_datetime_now():
    """Mock datetime.now() to return consistent time for specific tests"""
    fixed_time = datetime(2025, 8, 28, 6, 0, 0, tzinfo=timezone.utc)
    
    with patch('datetime.datetime.now') as mock_now, \
         patch('datetime.datetime.utcnow') as mock_utcnow:
        mock_now.return_value = fixed_time
        mock_utcnow.return_value = fixed_time.replace(tzinfo=None)
        yield mock_now

@pytest.fixture
def mock_file_system(tmp_path):
    """Mock file system operations"""
    with patch('pathlib.Path.home') as mock_home:
        mock_home.return_value = tmp_path
        yield tmp_path

@pytest.fixture
def no_network():
    """Disable all network requests for unit tests"""
    with patch('requests.get') as mock_get, \
         patch('requests.Session') as mock_session:
        
        mock_get.side_effect = Exception("Network access not allowed in unit tests")
        mock_session.return_value.get.side_effect = Exception("Network access not allowed in unit tests")
        yield

@pytest.fixture
def mock_config_files(tmp_path, mock_config, mock_models_config, mock_variables_mapping):
    """Create mock configuration files"""
    # Create config.yaml
    config_file = tmp_path / "config.yaml"
    with open(config_file, 'w') as f:
        yaml.dump(mock_config, f)
    
    # Create models_config.yaml
    models_config_file = tmp_path / "models_config.yaml"
    with open(models_config_file, 'w') as f:
        yaml.dump(mock_models_config, f)
    
    # Create variables_mapping.yaml
    variables_file = tmp_path / "variables_mapping.yaml"
    with open(variables_file, 'w') as f:
        yaml.dump(mock_variables_mapping, f)
    
    return {
        'config': config_file,
        'models_config': models_config_file,
        'variables_mapping': variables_file
    }

# ============================================================================
# PYTEST HOOKS
# ============================================================================

def pytest_configure(config):
    """Configure pytest"""
    import sys
    if not hasattr(sys, '_pytest_configured'):
        # Add project root to Python path
        project_root = Path(__file__).parent.parent
        sys.path.insert(0, str(project_root))
        sys._pytest_configured = True

def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically"""
    for item in items:
        # Add 'unit' marker to all tests in unit/ directory
        if 'unit/' in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        # Add 'integration' marker to integration tests
        elif 'integration/' in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # Add 'slow' marker to tests that might be slow
        if any(keyword in item.name.lower() for keyword in ['download', 'process', 'integration']):
            item.add_marker(pytest.mark.slow)
        
        # Add 'cli' marker to CLI tests
        if 'cli/' in str(item.fspath):
            item.add_marker(pytest.mark.cli)
        
        # Add 'network' marker to tests that use network
        if any(keyword in item.name.lower() for keyword in ['download', 'http', 'request']):
            item.add_marker(pytest.mark.network)

# ============================================================================
# CUSTOM ASSERTIONS
# ============================================================================

def assert_xarray_equal(actual, expected, rtol=1e-5, atol=1e-8):
    """Custom assertion for xarray datasets with tolerance"""
    try:
        xr.testing.assert_allclose(actual, expected, rtol=rtol, atol=atol)
        return True
    except AssertionError as e:
        pytest.fail(f"xarray datasets not equal: {e}")

def assert_file_exists_and_valid(file_path, min_size=0):
    """Assert file exists and has minimum size"""
    path = Path(file_path)
    assert path.exists(), f"File does not exist: {file_path}"
    assert path.stat().st_size >= min_size, f"File too small: {file_path} ({path.stat().st_size} bytes)"

# Register custom assertions
pytest.assert_xarray_equal = assert_xarray_equal
pytest.assert_file_exists_and_valid = assert_file_exists_and_valid
