"""
Mock objects and utilities for testing.

This module provides reusable mock objects and utilities for testing
various components of the weather data downloader.
"""

from unittest.mock import Mock, MagicMock, patch
from pathlib import Path
import requests
import xarray as xr
import numpy as np

class MockResponse:
    """Mock HTTP response object for testing download functionality"""
    
    def __init__(self, content=b"mock_grib_data", status_code=200, headers=None, 
                 url="https://example.com/test.grb2"):
        self.content = content
        self.status_code = status_code
        self.headers = headers or {'content-type': 'application/octet-stream'}
        self.url = url
        self.ok = status_code < 400
        self.text = content.decode('utf-8', errors='ignore')
    
    def raise_for_status(self):
        """Raise HTTPError for bad status codes"""
        if not self.ok:
            raise requests.HTTPError(f"HTTP {self.status_code} for url: {self.url}")
    
    def iter_content(self, chunk_size=8192):
        """Mock streaming content"""
        for i in range(0, len(self.content), chunk_size):
            yield self.content[i:i + chunk_size]

class MockGRIBFile:
    """Mock GRIB file for testing file operations"""
    
    def __init__(self, path, forecast_hour=0, size=1024*1024):
        self.path = Path(path)
        self.forecast_hour = forecast_hour
        self.size = size
        self.name = self.path.name
        
    def exists(self):
        """Mock file existence check"""
        return True
    
    def stat(self):
        """Mock file stats"""
        stat = Mock()
        stat.st_size = self.size
        return stat
    
    def write_bytes(self, data):
        """Mock writing bytes to file"""
        self.size = len(data)

class MockXarrayDataset:
    """Mock xarray dataset for testing data processing"""
    
    def __init__(self, variables=None, time_size=5, spatial_shape=(76, 61)):
        self.variables = variables or ['t2m', 'r2', 'u10', 'v10']
        self.time_size = time_size
        self.spatial_shape = spatial_shape
        
        # Create mock data_vars
        self.data_vars = {}
        for var in self.variables:
            mock_var = Mock()
            mock_var.dims = ('time', 'latitude', 'longitude')
            mock_var.shape = (time_size,) + spatial_shape
            self.data_vars[var] = mock_var
        
        # Create mock coordinates
        self.coords = {
            'time': Mock(),
            'latitude': Mock(), 
            'longitude': Mock()
        }
        
        # Mock dimensions
        self.dims = {
            'time': time_size,
            'latitude': spatial_shape[0],
            'longitude': spatial_shape[1]
        }
        
        # Mock time coordinate
        self.time = Mock()
        self.time.size = time_size
        
    def sel(self, **kwargs):
        """Mock spatial selection"""
        return MockXarrayDataset(
            variables=self.variables,
            time_size=self.time_size,
            spatial_shape=(50, 40)  # Reduced size after selection
        )
    
    def copy(self):
        """Mock dataset copy"""
        return MockXarrayDataset(
            variables=self.variables,
            time_size=self.time_size,
            spatial_shape=self.spatial_shape
        )

class MockVariableMapper:
    """Mock variable mapper for testing"""
    
    def __init__(self, mappings=None):
        self.mappings = mappings or {
            'gfs': {
                't2m': 'TMP',
                'rh2m': 'RH',
                'u10m': 'UGRD', 
                'v10m': 'VGRD',
                'hgt': 'HGT'
            }
        }
    
    def get_model_variable_code(self, standard_name, model):
        """Mock variable code lookup"""
        return self.mappings.get(model, {}).get(standard_name, standard_name.upper())
    
    def get_model_config(self, model):
        """Mock model config lookup"""
        return {
            'name': f'{model.upper()} Model',
            'cycles': ['00', '06', '12', '18'],
            'cycle_forecast_ranges': {
                '00': [[0, 120, 1], [123, 240, 3]]
            }
        }

class MockGFSProvider:
    """Mock GFS provider for testing"""
    
    def __init__(self, config=None):
        self.config = config or {}
        self.model_name = 'gfs'
        self.resolution = '0.25°'
        
    def get_download_url(self, date, cycle, forecast_hour, **kwargs):
        """Mock URL generation"""
        return (
            f"https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25_1hr.pl?"
            f"file=gfs.t{cycle}z.pgrb2.0p25.f{forecast_hour:03d}&"
            f"dir=%2Fgfs.{date}%2F{cycle}%2Fatmos"
        )
    
    def validate_parameters(self, date, cycle, forecast_hour):
        """Mock parameter validation"""
        if cycle not in ['00', '06', '12', '18']:
            raise ValueError(f"Invalid cycle: {cycle}")
        if forecast_hour < 0 or forecast_hour > 240:
            raise ValueError(f"Invalid forecast hour: {forecast_hour}")

class MockGRIBProcessor:
    """Mock GRIB processor for testing"""
    
    def __init__(self, variable_mapper=None, user_config=None):
        self.variable_mapper = variable_mapper or MockVariableMapper()
        self.user_config = user_config or {}
    
    def process(self, grib_files, output_path):
        """Mock processing method"""
        return {
            'processed': Path(output_path).with_suffix('.nc'),
            'interpolated': Path(output_path).parent / 'interpolated' / Path(output_path).with_suffix('.nc').name,
            'variables': ['t2m', 'rh2m', 'u10m', 'v10m', 'hgt'],
            'time_steps': 5,
            'compression_ratio': 6.5
        }

# ============================================================================
# CONTEXT MANAGERS AND DECORATORS
# ============================================================================

def mock_requests_get(response=None, side_effect=None):
    """Context manager for mocking requests.get"""
    if response is None:
        response = MockResponse()
    
    return patch('requests.get', return_value=response, side_effect=side_effect)

def mock_xarray_open_mfdataset(dataset=None, side_effect=None):
    """Context manager for mocking xarray.open_mfdataset"""
    if dataset is None:
        dataset = MockXarrayDataset()
    
    return patch('xarray.open_mfdataset', return_value=dataset, side_effect=side_effect)

def mock_pathlib_operations():
    """Context manager for mocking pathlib operations"""
    return patch.multiple(
        'pathlib.Path',
        exists=Mock(return_value=True),
        mkdir=Mock(),
        unlink=Mock(),
        write_bytes=Mock(),
        stat=Mock(return_value=Mock(st_size=1024))
    )

def mock_yaml_load(config_data):
    """Context manager for mocking YAML file loading"""
    return patch('yaml.safe_load', return_value=config_data)

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def create_mock_grib_content():
    """Create realistic mock GRIB2 file content"""
    # GRIB2 files have specific structure
    header = b'GRIB'              # GRIB indicator
    reserved = b'\x00\x00'        # Reserved
    discipline = b'\x00'          # Discipline
    edition = b'\x02'             # GRIB edition number (2)
    total_length = b'\x00\x00\x00\x00\x00\x00\x04\x00'  # Total message length
    
    # Simplified sections (normally much more complex)
    section1 = b'\x00' * 21       # Identification section
    section3 = b'\x00' * 72       # Grid definition section  
    section4 = b'\x00' * 34       # Product definition section
    section5 = b'\x00' * 23       # Data representation section
    section6 = b'\x00' * 6        # Bit map section
    section7 = b'\x00' * 500      # Data section
    
    footer = b'7777'              # End section
    
    return header + reserved + discipline + edition + total_length + \
           section1 + section3 + section4 + section5 + section6 + section7 + footer

def create_mock_netcdf_content():
    """Create simple mock NetCDF content"""
    # Very simplified NetCDF header
    return b'\x89HDF\r\n\x1a\n' + b'\x00' * 1000

def assert_mock_called_with_pattern(mock_obj, pattern):
    """Assert that mock was called with arguments matching pattern"""
    for call in mock_obj.call_args_list:
        args, kwargs = call
        if any(pattern in str(arg) for arg in args):
            return True
        if any(pattern in str(val) for val in kwargs.values()):
            return True
    return False
