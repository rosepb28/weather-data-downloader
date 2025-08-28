"""
GFS (Global Forecast System) provider implementation.

This module provides the GFS-specific implementation of the WeatherModelProvider
interface for downloading GFS 0.25 degree data from NOMADS.
"""

from typing import List, Dict, Any, Optional
from urllib.parse import urlencode
from ..interfaces.weather_model_provider import WeatherModelProvider


class GFSProvider(WeatherModelProvider):
    """
    GFS 0.25 degree weather model provider.
    
    This provider handles downloads from the NOMADS GFS 0.25 degree
    dataset, which provides global weather forecasts at 0.25 degree resolution.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, variable_mapper=None):
        """
        Initialize GFS provider.
        
        Args:
            config: Configuration dictionary (optional)
            variable_mapper: Variable mapper for handling variable name conversions
        """
        self.config = config or self._get_default_config()
        self.variable_mapper = variable_mapper
        
        # Validate configuration
        self._validate_config()
    
    @property
    def model_name(self) -> str:
        """Return the name of the weather model."""
        return "GFS 0.25 Degree"
    
    @property
    def resolution(self) -> str:
        """Return the resolution of the model."""
        return "0.25"
    
    @property
    def available_cycles(self) -> List[str]:
        """Return available forecast cycles."""
        return self.config.get('cycles', ["00", "06", "12", "18"])
    
    @property
    def forecast_frequency(self) -> int:
        """Return forecast output frequency in hours."""
        return self.config.get('forecast_frequency', 3)
    
    @property
    def max_forecast_hours(self) -> int:
        """Return maximum forecast hours available."""
        return self.config.get('max_forecast_hours', 240)
    
    def get_download_url(
        self, 
        date: str, 
        cycle: str, 
        forecast_hour: int,
        variables: Optional[List[str]] = None,
        levels: Optional[List[str]] = None
    ) -> str:
        """
        Generate download URL for GFS data.
        
        Args:
            date: Date in YYYYMMDD format
            cycle: Forecast cycle (e.g., '00', '06')
            forecast_hour: Forecast hour (e.g., 0, 3, 6)
            variables: List of standard variable names to download (optional)
            levels: List of levels to download (optional)
            
        Returns:
            Complete download URL for GFS data
        """
        # Validate parameters
        if not self.validate_parameters(date, cycle, forecast_hour):
            raise ValueError(f"Invalid parameters: date={date}, cycle={cycle}, forecast_hour={forecast_hour}")
        
        # Build base URL
        base_url = self.config['base_url']
        
        # Prepare query parameters
        params = {
            'file': f'gfs.t{cycle}z.pgrb2.0p25.f{forecast_hour:03d}',
            'dir': f'/gfs.{date}/{cycle}/atmos'
        }
        
        # Add spatial bounds from config or use defaults
        if 'spatial_bounds' in self.config:
            bounds = self.config['spatial_bounds']
            params.update({
                'leftlon': bounds['lon_min'],
                'rightlon': bounds['lon_max'],
                'toplat': bounds['lat_max'],
                'bottomlat': bounds['lat_min']
            })
        else:
            # Default to global coverage if no bounds specified
            params.update({
                'leftlon': 0,
                'rightlon': 360,
                'toplat': 90,
                'bottomlat': -90
            })
        
        # Handle variables
        if variables and self.variable_mapper:
            # Convert standard variable names to GFS codes
            gfs_variables = []
            for std_var in variables:
                try:
                    gfs_code = self.variable_mapper.get_model_variable_code(std_var, 'gfs')
                    gfs_variables.append(gfs_code)
                except ValueError as e:
                    print(f"Warning: {e}, skipping variable {std_var}")
                    continue
            
            # Add GFS variable parameters
            for gfs_var in gfs_variables:
                params[f'var_{gfs_var}'] = 'on'
        else:
            # Use default variables from config
            default_vars = self.config.get('variables', ['t2m', 'rh2m', 'u10m', 'v10m', 'hgt'])
            if self.variable_mapper:
                for std_var in default_vars:
                    try:
                        gfs_code = self.variable_mapper.get_model_variable_code(std_var, 'gfs')
                        params[f'var_{gfs_code}'] = 'on'
                    except ValueError:
                        continue
            else:
                # Fallback to hardcoded variables
                params.update({
                    'var_TMP': 'on',  # Temperature
                    'var_RH': 'on',   # Relative humidity
                    'var_UGRD': 'on', # U-component of wind
                    'var_VGRD': 'on', # V-component of wind
                    'var_HGT': 'on',  # Geopotential height
                })
        
        # Handle levels
        if levels:
            # Add level parameters
            for level in levels:
                if self._is_valid_level(level):
                    params[f'lev_{level}'] = 'on'
        else:
            # Use default levels
            params.update({
                'lev_2_m_above_ground': 'on',
                'lev_10_m_above_ground': 'on',
                'lev_surface': 'on',
            })
        
        # Build final URL
        query_string = urlencode(params)
        return f"{base_url}?{query_string}"
    
    def validate_parameters(
        self, 
        date: str, 
        cycle: str, 
        forecast_hour: int
    ) -> bool:
        """
        Validate if the requested parameters are valid for GFS.
        
        Args:
            date: Date in YYYYMMDD format
            cycle: Forecast cycle
            forecast_hour: Forecast hour
            
        Returns:
            True if parameters are valid, False otherwise
        """
        # Validate date format (basic check)
        if len(date) != 8 or not date.isdigit():
            return False
        
        # Validate cycle
        if cycle not in self.available_cycles:
            return False
        
        # Validate forecast hour
        if not (0 <= forecast_hour <= self.max_forecast_hours):
            return False
        
        # Validate forecast hour frequency based on model configuration
        if 'cycle_forecast_ranges' in self.config:
            # Check if forecast hour is valid according to model's frequency rules
            valid_forecast_hours = []
            for cycle_ranges in self.config['cycle_forecast_ranges'].values():
                for start, end, frequency in cycle_ranges:
                    for hour in range(start, end + 1, frequency):
                        valid_forecast_hours.append(hour)
            
            if forecast_hour not in valid_forecast_hours:
                return False
        else:
            # Fallback: use old frequency-based validation
            if forecast_hour % self.forecast_frequency != 0:
                return False
        
        return True
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about the GFS model.
        
        Returns:
            Dictionary containing GFS model metadata
        """
        return {
            'model_name': self.model_name,
            'resolution': self.resolution,
            'available_cycles': self.available_cycles,
            'forecast_frequency': self.forecast_frequency,
            'max_forecast_hours': self.max_forecast_hours,
            'data_source': 'NOMADS',
            'base_url': self.config['base_url'],
            'variables': self.config.get('variables', []),
            'levels': self.config.get('levels', []),
            'spatial_coverage': 'Global',
            'temporal_coverage': f'0-{self.max_forecast_hours} hours',
            'update_frequency': 'Every 6 hours'
        }
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for GFS."""
        return {
            'base_url': 'https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25_1hr.pl',
            'cycles': ["00", "06", "12", "18"],
            'forecast_frequency': 3,
            'max_forecast_hours': 240,
            'variables': ["TMP", "RH", "UGRD", "VGRD", "HGT"],
            'levels': ["surface", "2_m_above_ground", "10_m_above_ground"]
        }
    
    def _validate_config(self) -> None:
        """Validate the configuration."""
        required_keys = ['base_url']
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"Missing required configuration key: {key}")
    
    def _is_valid_variable(self, variable: str) -> bool:
        """Check if a variable is valid for GFS."""
        valid_variables = [
            'TMP', 'RH', 'UGRD', 'VGRD', 'HGT', 'PRES', 'TCDC', 'APCP',
            'CAPE', 'CIN', 'LFTX', 'PWAT', 'VVEL', 'DZDT', 'ABSV'
        ]
        return variable in valid_variables
    
    def _is_valid_level(self, level: str) -> bool:
        """Check if a level is valid for GFS."""
        valid_levels = [
            'surface', '2_m_above_ground', '10_m_above_ground',
            '1000_mb', '925_mb', '850_mb', '700_mb', '500_mb',
            '250_mb', '200_mb', '100_mb', '50_mb'
        ]
        return level in valid_levels
