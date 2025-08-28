"""
Interface for data subsetting operations.

This module defines the abstract base class that all data subsetters
must implement, allowing extraction of specific variables, levels, regions, and time ranges.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import xarray as xr


class DataSubsetter(ABC):
    """
    Abstract base class for data subsetters.
    
    This interface defines the contract that all data subsetters must implement,
    allowing extraction of specific data subsets from weather model datasets.
    """
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    def subset_spatial(self, dataset: xr.Dataset, bounds: Dict[str, float]) -> xr.Dataset:
        """
        Extract only the specified spatial region from the dataset.
        
        Args:
            dataset: Input dataset
            bounds: Dictionary with spatial bounds (lon_min, lon_max, lat_min, lat_max)
            
        Returns:
            Dataset cropped to the specified spatial bounds
        """
        pass
    
    @abstractmethod
    def subset_temporal(self, dataset: xr.Dataset, time_range: Dict[str, Any]) -> xr.Dataset:
        """
        Extract only the specified time range from the dataset.
        
        Args:
            dataset: Input dataset
            time_range: Dictionary with temporal bounds (start_time, end_time, frequency)
            
        Returns:
            Dataset cropped to the specified temporal bounds
        """
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    def get_subsetting_info(self, dataset: xr.Dataset) -> Dict[str, Any]:
        """
        Get information about what subsetting operations can be applied.
        
        Args:
            dataset: Input dataset
            
        Returns:
            Dictionary containing subsetting capabilities and current state
        """
        pass
    
    @abstractmethod
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
        pass
