"""
Interface for storage management operations.

This module defines the abstract base class that all storage managers
must implement, ensuring consistent data organization and access.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pathlib import Path


class StorageManager(ABC):
    """
    Abstract base class for storage managers.
    
    This interface defines the contract that all storage managers must implement,
    ensuring consistent data organization by model and product type.
    """
    
    @abstractmethod
    def get_model_directory(self, model_name: str) -> Path:
        """
        Get the base directory for a specific model.
        
        Args:
            model_name: Name of the weather model (e.g., 'gfs.0p25')
            
        Returns:
            Path to the model directory
        """
        pass
    
    @abstractmethod
    def get_product_directory(
        self, 
        model_name: str, 
        product_type: str
    ) -> Path:
        """
        Get the directory for a specific product type.
        
        Args:
            model_name: Name of the weather model
            product_type: Type of product ('raw', 'processed', 'metadata')
            
        Returns:
            Path to the product directory
        """
        pass
    
    @abstractmethod
    def get_date_directory(
        self, 
        model_name: str, 
        product_type: str, 
        date: str
    ) -> Path:
        """
        Get the directory for a specific date.
        
        Args:
            model_name: Name of the weather model
            product_type: Type of product
            date: Date in YYYYMMDD format
            
        Returns:
            Path to the date directory
        """
        pass
    
    @abstractmethod
    def get_cycle_directory(
        self, 
        model_name: str, 
        product_type: str, 
        date: str, 
        cycle: str
    ) -> Path:
        """
        Get the directory for a specific forecast cycle.
        
        Args:
            model_name: Name of the weather model
            product_type: Type of product
            date: Date in YYYYMMDD format
            cycle: Forecast cycle (e.g., '00', '06')
            
        Returns:
            Path to the cycle directory
        """
        pass
    
    @abstractmethod
    def create_directory_structure(
        self, 
        model_name: str, 
        product_type: str, 
        date: str, 
        cycle: str
    ) -> Path:
        """
        Create the complete directory structure for storing data.
        
        Args:
            model_name: Name of the weather model
            product_type: Type of product
            date: Date in YYYYMMDD format
            cycle: Forecast cycle
            
        Returns:
            Path to the created cycle directory
        """
        pass
    
    @abstractmethod
    def get_file_path(
        self, 
        model_name: str, 
        product_type: str, 
        date: str, 
        cycle: str, 
        forecast_hour: int,
        file_extension: str = '.nc'
    ) -> Path:
        """
        Get the complete file path for storing data.
        
        Args:
            model_name: Name of the weather model
            product_type: Type of product
            date: Date in YYYYMMDD format
            cycle: Forecast cycle
            forecast_hour: Forecast hour
            file_extension: File extension (default: 's')
            
        Returns:
            Complete file path
        """
        pass
    
    @abstractmethod
    def file_exists(
        self, 
        model_name: str, 
        product_type: str, 
        date: str, 
        cycle: str, 
        forecast_hour: int
    ) -> bool:
        """
        Check if a file already exists.
        
        Args:
            model_name: Name of the weather model
            product_type: Type of product
            date: Date in YYYYMMDD format
            cycle: Forecast cycle
            forecast_hour: Forecast hour
            
        Returns:
            True if file exists, False otherwise
        """
        pass
    
    @abstractmethod
    def get_storage_info(self, model_name: str) -> Dict[str, Any]:
        """
        Get information about storage usage for a model.
        
        Args:
            model_name: Name of the weather model
            
        Returns:
            Dictionary containing storage information
        """
        pass
    
    @abstractmethod
    def cleanup_old_data(
        self, 
        model_name: str, 
        max_age_days: int
    ) -> int:
        """
        Clean up old data files.
        
        Args:
            model_name: Name of the weather model
            max_age_days: Maximum age of files to keep
            
        Returns:
            Number of files removed
        """
        pass
