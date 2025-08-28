"""
Test data factories for creating mock objects and datasets.

These factories provide consistent test data generation using factory_boy.
"""

import factory
import numpy as np
import xarray as xr
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

class MockDatasetFactory(factory.Factory):
    """Factory for creating mock xarray datasets"""
    
    class Meta:
        model = xr.Dataset
    
    @classmethod
    def create(cls, **kwargs):
        """Create a mock dataset with specified parameters"""
        # Default parameters
        time_periods = kwargs.get('time_periods', 5)
        freq = kwargs.get('freq', '1H')
        lat_size = kwargs.get('lat_size', 76)
        lon_size = kwargs.get('lon_size', 61)
        variables = kwargs.get('variables', ['t2m', 'r2', 'u10', 'v10'])
        start_date = kwargs.get('start_date', '2025-01-01T00:00:00')
        
        # Create coordinates
        time = pd.date_range(start_date, periods=time_periods, freq=freq.replace('H', 'h'))
        lat = np.linspace(15, -60, lat_size)   # South America bounds
        lon = np.linspace(-90, -30, lon_size)  # South America bounds
        
        # Create realistic data with fixed seed for reproducibility
        np.random.seed(42)
        data_vars = {}
        
        for var in variables:
            if var in ['t2m', 't']:
                # Temperature: 270-300K range
                data = 285 + 15 * np.random.random((time_periods, lat_size, lon_size))
            elif var in ['r2', 'rh2m']:
                # Relative humidity: 0-100%
                data = 100 * np.random.random((time_periods, lat_size, lon_size))
            elif var in ['u10', 'v10', 'u10m', 'v10m']:
                # Wind components: -10 to 10 m/s
                data = 20 * np.random.random((time_periods, lat_size, lon_size)) - 10
            elif var in ['orog', 'hgt']:
                # Surface height: 0-3000m (time-independent)
                data = 3000 * np.random.random((lat_size, lon_size))
                data_vars[var] = (['latitude', 'longitude'], data)
                continue
            elif var in ['msl', 'prmsl']:
                # Mean sea level pressure: 980-1040 hPa
                data = 98000 + 6000 * np.random.random((time_periods, lat_size, lon_size))
            else:
                # Generic variable
                data = np.random.random((time_periods, lat_size, lon_size))
            
            data_vars[var] = (['time', 'latitude', 'longitude'], data)
        
        # Create dataset
        dataset = xr.Dataset(data_vars, coords={
            'time': time, 'latitude': lat, 'longitude': lon
        })
        
        # Add realistic attributes
        dataset.attrs.update({
            'source': 'Mock test dataset',
            'model': 'test-model',
            'created': datetime.now().isoformat(),
            'conventions': 'CF-1.6'
        })
        
        return dataset

class MockConfigFactory(factory.DictFactory):
    """Factory for creating mock configurations"""
    
    output_dir = "test_data"
    
    spatial_bounds = factory.Dict({
        'lon_min': -90.0, 'lon_max': -30.0,
        'lat_min': -60.0, 'lat_max': 15.0
    })
    
    processing = factory.Dict({
        'target_frequency': '1H',
        'workers': 2,
        'chunk_size': '100MB',
        'compression': {'enabled': True, 'level': 5},
        'netcdf': {'chunking': True, 'shuffle': True, 'fletcher32': True}
    })
    
    download = factory.Dict({
        'retry_attempts': 3,
        'timeout': 30,
        'concurrent_downloads': 2
    })

class MockModelsConfigFactory(factory.DictFactory):
    """Factory for creating mock model configurations"""
    
    @classmethod
    def gfs_config(cls):
        """Create GFS model configuration"""
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

class MockGRIBFileFactory(factory.Factory):
    """Factory for creating mock GRIB files"""
    
    class Meta:
        model = Path
    
    @classmethod
    def create(cls, file_path=None, forecast_hour=0, **kwargs):
        """Create a mock GRIB file"""
        if file_path is None:
            file_path = Path(f"gfs.t00z.pgrb2.0p25.f{forecast_hour:03d}")
        
        # Create realistic GRIB2 file structure
        # GRIB2 files start with "GRIB" and end with "7777"
        header = b'GRIB'  # GRIB2 indicator
        section1 = b'\x00' * 21  # Identification section
        section3 = b'\x00' * 72  # Grid definition section
        section4 = b'\x00' * 34  # Product definition section
        section5 = b'\x00' * 23  # Data representation section
        section6 = b'\x00' * 6   # Bit map section
        section7 = b'\x00' * 1000  # Data section (mock data)
        footer = b'7777'  # End section
        
        mock_content = header + section1 + section3 + section4 + section5 + section6 + section7 + footer
        
        # Write to file
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(mock_content)
        
        return file_path

def create_sample_forecast_hours(model='gfs', cycle='00', max_hours=240):
    """Generate realistic forecast hours for testing"""
    if model.lower() == 'gfs':
        if max_hours <= 120:
            return list(range(0, min(max_hours + 1, 121)))
        else:
            hourly = list(range(0, 121))  # 0-120h hourly
            three_hourly = list(range(123, min(max_hours + 1, 241), 3))  # 123-240h every 3h
            return hourly + three_hourly
    else:
        # Generic model: hourly for first 72h, then 3-hourly
        if max_hours <= 72:
            return list(range(0, max_hours + 1))
        else:
            hourly = list(range(0, 73))
            three_hourly = list(range(75, min(max_hours + 1, 241), 3))
            return hourly + three_hourly

def create_mock_url_response(status_code=200, content_type='application/octet-stream', 
                           content=b'mock_grib_data'):
    """Create mock HTTP response for URL testing"""
    from unittest.mock import Mock
    
    response = Mock()
    response.status_code = status_code
    response.headers = {'content-type': content_type}
    response.content = content
    response.ok = status_code < 400
    
    def raise_for_status():
        if not response.ok:
            from requests.exceptions import HTTPError
            raise HTTPError(f"HTTP {status_code}")
    
    response.raise_for_status = raise_for_status
    return response
