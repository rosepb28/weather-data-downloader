"""
NetCDF subsetter implementation.

This module provides the NetCDF-specific implementation of the DataSubsetter interface,
allowing extraction of specific data subsets from NetCDF weather model datasets.
"""

import xarray as xr
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import numpy as np

from ..interfaces.data_subsetter import DataSubsetter
from ..interfaces.variable_mapper import VariableMapper


class NetCDFSubsetter(DataSubsetter):
    """
    NetCDF-specific implementation of the DataSubsetter interface.
    
    This class provides methods to extract specific variables, levels, regions,
    and time ranges from NetCDF weather model datasets.
    """
    
    def __init__(self, variable_mapper: VariableMapper):
        """
        Initialize the NetCDF subsetter.
        
        Args:
            variable_mapper: Variable mapper for handling variable name conversions
        """
        self.variable_mapper = variable_mapper
    
    def subset_variables(self, dataset: xr.Dataset, variables: List[str]) -> xr.Dataset:
        """
        Extract only the specified variables from the dataset.
        
        Args:
            dataset: Input dataset
            variables: List of standard variable names to extract
            
        Returns:
            Dataset containing only the specified variables
            
        Raises:
            ValueError: If any variable is not found in the dataset
        """
        if not variables:
            return dataset
        
        subset_vars = {}
        missing_vars = []
        
        for std_var in variables:
            # Try to find the variable in the dataset
            found = False
            
            # First, try to find by standard name directly
            if std_var in dataset.data_vars:
                subset_vars[std_var] = dataset[std_var]
                found = True
                continue
            
            # If not found, try to map from model-specific codes
            for var_name in dataset.data_vars:
                try:
                    # Try to map back to standard name
                    mapped_std_var = self.variable_mapper.get_standard_variable_name(var_name, 'unknown')
                    if mapped_std_var == std_var:
                        # Rename to standard name
                        subset_vars[std_var] = dataset[var_name].rename(std_var)
                        found = True
                        break
                except ValueError:
                    # If mapping fails, check if names are similar
                    if var_name.lower() == std_var.lower():
                        subset_vars[std_var] = dataset[var_name].rename(std_var)
                        found = True
                        break
            
            if not found:
                missing_vars.append(std_var)
        
        if missing_vars:
            raise ValueError(f"Variables not found in dataset: {missing_vars}")
        
        return xr.Dataset(subset_vars)
    
    def subset_levels(self, dataset: xr.Dataset, levels: List[str]) -> xr.Dataset:
        """
        Extract only the specified levels from the dataset.
        
        Args:
            dataset: Input dataset
            levels: List of level names to extract
            
        Returns:
            Dataset containing only the specified levels
            
        Raises:
            ValueError: If any level is not found in the dataset
        """
        if not levels:
            return dataset
        
        # Check if dataset has level dimension
        level_dims = ['level', 'lev', 'pressure', 'height']
        level_dim = None
        
        for dim in level_dims:
            if dim in dataset.dims:
                level_dim = dim
                break
        
        if level_dim is None:
            # No level dimension found, return dataset as is
            return dataset
        
        # Find level values that match the requested levels
        level_values = dataset[level_dim].values
        level_indices = []
        
        for level in levels:
            # Try exact match first
            if level in level_values:
                level_indices.append(np.where(level_values == level)[0][0])
            else:
                # Try partial match (e.g., "2_m_above_ground" vs "2")
                for i, val in enumerate(level_values):
                    if str(level) in str(val) or str(val) in str(level):
                        level_indices.append(i)
                        break
                else:
                    raise ValueError(f"Level {level} not found in dataset")
        
        # Select only the specified levels
        return dataset.isel({level_dim: level_indices})
    
    def subset_spatial(self, dataset: xr.Dataset, bounds: Dict[str, float]) -> xr.Dataset:
        """
        Extract only the specified spatial region from the dataset.
        
        Args:
            dataset: Input dataset
            bounds: Dictionary with spatial bounds (lon_min, lon_max, lat_min, lat_max)
            
        Returns:
            Dataset cropped to the specified spatial bounds
        """
        if not bounds:
            return dataset
        
        required_bounds = ['lon_min', 'lon_max', 'lat_min', 'lat_max']
        if not all(bound in bounds for bound in required_bounds):
            raise ValueError(f"Missing required bounds: {required_bounds}")
        
        # Find coordinate dimensions
        lon_dims = ['longitude', 'lon', 'x']
        lat_dims = ['latitude', 'lat', 'y']
        
        lon_dim = None
        lat_dim = None
        
        for dim in lon_dims:
            if dim in dataset.dims:
                lon_dim = dim
                break
        
        for dim in lat_dims:
            if dim in dataset.dims:
                lat_dim = dim
                break
        
        if lon_dim is None or lat_dim is None:
            raise ValueError("Could not find longitude/latitude dimensions")
        
        # Apply spatial subsetting
        subset_dataset = dataset.sel({
            lon_dim: slice(bounds['lon_min'], bounds['lon_max']),
            lat_dim: slice(bounds['lat_min'], bounds['lat_max'])
        })
        
        return subset_dataset
    
    def subset_temporal(self, dataset: xr.Dataset, time_range: Dict[str, Any]) -> xr.Dataset:
        """
        Extract only the specified time range from the dataset.
        
        Args:
            dataset: Input dataset
            time_range: Dictionary with temporal bounds (start_time, end_time, frequency)
            
        Returns:
            Dataset cropped to the specified temporal bounds
        """
        if not time_range:
            return dataset
        
        # Find time dimension
        time_dims = ['time', 't', 'forecast_time']
        time_dim = None
        
        for dim in time_dims:
            if dim in dataset.dims:
                time_dim = dim
                break
        
        if time_dim is None:
            # No time dimension found, return dataset as is
            return dataset
        
        subset_dataset = dataset
        
        # Apply start time filter
        if 'start_time' in time_range:
            subset_dataset = subset_dataset.sel({
                time_dim: slice(time_range['start_time'], None)
            })
        
        # Apply end time filter
        if 'end_time' in time_range:
            subset_dataset = subset_dataset.sel({
                time_dim: slice(None, time_range['end_time'])
            })
        
        # Apply frequency filter (resample)
        if 'frequency' in time_range:
            subset_dataset = subset_dataset.resample({
                time_dim: time_range['frequency']
            }).mean()
        
        return subset_dataset
    
    def subset_comprehensive(
        self, 
        dataset: xr.Dataset, 
        variables: Optional[List[str]] = None,
        levels: Optional[List[str]] = None,
        bounds: Optional[Dict[str, float]] = None,
        time_range: Optional[Dict[str, Any]] = None
    ) -> xr.Dataset:
        """
        Apply multiple subsetting operations in sequence.
        
        Args:
            dataset: Input dataset
            variables: List of variables to extract (optional)
            levels: List of levels to extract (optional)
            bounds: Spatial bounds (optional)
            time_range: Temporal bounds (optional)
            
        Returns:
            Dataset with all subsetting operations applied
        """
        subset_dataset = dataset
        
        # Apply subsetting operations in order
        if variables:
            subset_dataset = self.subset_variables(subset_dataset, variables)
        
        if levels:
            subset_dataset = self.subset_levels(subset_dataset, levels)
        
        if bounds:
            subset_dataset = self.subset_spatial(subset_dataset, bounds)
        
        if time_range:
            subset_dataset = self.subset_temporal(subset_dataset, time_range)
        
        return subset_dataset
    
    def get_subsetting_info(self, dataset: xr.Dataset) -> Dict[str, Any]:
        """
        Get information about what subsetting operations can be applied.
        
        Args:
            dataset: Input dataset
            
        Returns:
            Dictionary containing subsetting capabilities and current state
        """
        info = {
            'dimensions': dict(dataset.dims),
            'variables': list(dataset.data_vars.keys()),
            'coordinates': list(dataset.coords.keys()),
            'spatial_subsetting': False,
            'temporal_subsetting': False,
            'level_subsetting': False
        }
        
        # Check spatial subsetting capability
        lon_dims = ['longitude', 'lon', 'x']
        lat_dims = ['latitude', 'lat', 'y']
        
        if any(dim in dataset.dims for dim in lon_dims) and any(dim in dataset.dims for dim in lat_dims):
            info['spatial_subsetting'] = True
        
        # Check temporal subsetting capability
        time_dims = ['time', 't', 'forecast_time']
        if any(dim in dataset.dims for dim in time_dims):
            info['temporal_subsetting'] = True
        
        # Check level subsetting capability
        level_dims = ['level', 'lev', 'pressure', 'height']
        if any(dim in dataset.dims for dim in level_dims):
            info['level_subsetting'] = True
        
        return info
    
    def validate_subsetting_parameters(
        self, 
        variables: Optional[List[str]] = None,
        levels: Optional[List[str]] = None,
        bounds: Optional[Dict[str, float]] = None,
        time_range: Optional[Dict[str, Any]] = None
    ) -> tuple[bool, List[str]]:
        """
        Validate subsetting parameters before applying them.
        
        Args:
            variables: List of variables to validate
            levels: List of levels to validate
            bounds: Spatial bounds to validate
            time_range: Temporal bounds to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Validate variables
        if variables:
            if not isinstance(variables, list):
                errors.append("Variables must be a list")
            else:
                for var in variables:
                    if not isinstance(var, str):
                        errors.append(f"Variable {var} must be a string")
        
        # Validate levels
        if levels:
            if not isinstance(levels, list):
                errors.append("Levels must be a list")
            else:
                for level in levels:
                    if not isinstance(level, str):
                        errors.append(f"Level {level} must be a string")
        
        # Validate bounds
        if bounds:
            if not isinstance(bounds, dict):
                errors.append("Bounds must be a dictionary")
            else:
                required_bounds = ['lon_min', 'lon_max', 'lat_min', 'lat_max']
                for bound in required_bounds:
                    if bound not in bounds:
                        errors.append(f"Missing required bound: {bound}")
                    elif not isinstance(bounds[bound], (int, float)):
                        errors.append(f"Bound {bound} must be a number")
        
        # Validate time range
        if time_range:
            if not isinstance(time_range, dict):
                errors.append("Time range must be a dictionary")
            else:
                if 'start_time' in time_range and not isinstance(time_range['start_time'], str):
                    errors.append("start_time must be a string")
                if 'end_time' in time_range and not isinstance(time_range['end_time'], str):
                    errors.append("end_time must be a string")
                if 'frequency' in time_range and not isinstance(time_range['frequency'], str):
                    errors.append("frequency must be a string")
        
        return len(errors) == 0, errors
