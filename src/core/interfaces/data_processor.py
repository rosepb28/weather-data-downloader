"""
Interface for data processing operations.

This module defines the abstract base class that all data processors
must implement, including internal interpolation and future extensibility.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pathlib import Path
import xarray as xr


class DataProcessor(ABC):
    """
    Abstract base class for data processors.
    
    This interface defines the contract that all data processors must implement.
    Processing includes validation, interpolation, and preparation for future
    variable calculations.
    """
    
    @abstractmethod
    def process(
        self, 
        raw_data_path: Path,
        output_path: Path,
        config: Dict[str, Any]
    ) -> bool:
        """
        Process raw data from the model.
        
        This method internally handles:
        - Data validation
        - Temporal interpolation (if enabled)
        - Preparation for future variable calculations
        - Compression and optimization
        
        Args:
            raw_data_path: Path to raw data file
            output_path: Path where processed data should be saved
            config: Processing configuration
            
        Returns:
            True if processing was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def validate_data(
        self, 
        data: xr.Dataset
    ) -> tuple[bool, List[str]]:
        """
        Validate the quality and consistency of the data.
        
        Args:
            data: Dataset to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        pass
    
    @abstractmethod
    def interpolate_temporal(
        self, 
        data: xr.Dataset,
        target_frequency: str
    ) -> xr.Dataset:
        """
        Interpolate data to a different temporal frequency.
        
        Args:
            data: Input dataset
            target_frequency: Target frequency (e.g., '1H', '3H')
            
        Returns:
            Interpolated dataset
        """
        pass
    
    @abstractmethod
    def prepare_for_variable_calculation(
        self, 
        data: xr.Dataset
    ) -> xr.Dataset:
        """
        Prepare data for future variable calculations.
        
        This method ensures the data is in the right format and
        structure for calculating derived variables.
        
        Args:
            data: Input dataset
            
        Returns:
            Prepared dataset
        """
        pass
    
    @abstractmethod
    def optimize_storage(
        self, 
        data: xr.Dataset,
        compression_level: int = 6
    ) -> xr.Dataset:
        """
        Optimize dataset for storage and memory usage.
        
        Args:
            data: Input dataset
            compression_level: Compression level (0-9)
            
        Returns:
            Optimized dataset
        """
        pass
    
    @abstractmethod
    def get_processing_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about the processing operations performed.
        
        Returns:
            Dictionary containing processing metadata
        """
        pass
