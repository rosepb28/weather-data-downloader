"""
Interface for weather model providers.

This module defines the abstract base class that all weather model
providers must implement.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path


class WeatherModelProvider(ABC):
    """
    Abstract base class for weather model providers.
    
    This interface defines the contract that all weather model providers
    must implement, ensuring consistency across different models.
    """
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the name of the weather model."""
        pass
    
    @property
    @abstractmethod
    def resolution(self) -> str:
        """Return the resolution of the model."""
        pass
    
    @property
    @abstractmethod
    def available_cycles(self) -> List[str]:
        """Return available forecast cycles (e.g., ['00', '06', '12', '18'])."""
        pass
    
    @property
    @abstractmethod
    def forecast_frequency(self) -> int:
        """Return forecast output frequency in hours."""
        pass
    
    @property
    @abstractmethod
    def max_forecast_hours(self) -> int:
        """Return maximum forecast hours available."""
        pass
    
    @abstractmethod
    def get_download_url(
        self, 
        date: str, 
        cycle: str, 
        forecast_hour: int,
        variables: Optional[List[str]] = None,
        levels: Optional[List[str]] = None
    ) -> str:
        """
        Generate download URL for specific parameters.
        
        Args:
            date: Date in YYYYMMDD format
            cycle: Forecast cycle (e.g., '00', '06')
            forecast_hour: Forecast hour (e.g., 0, 3, 6)
            variables: List of variables to download (optional)
            levels: List of levels to download (optional)
            
        Returns:
            Complete download URL
        """
        pass
    
    @abstractmethod
    def validate_parameters(
        self, 
        date: str, 
        cycle: str, 
        forecast_hour: int
    ) -> bool:
        """
        Validate if the requested parameters are valid for this model.
        
        Args:
            date: Date in YYYYMMDD format
            cycle: Forecast cycle
            forecast_hour: Forecast hour
            
        Returns:
            True if parameters are valid, False otherwise
        """
        pass
    
    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about the model.
        
        Returns:
            Dictionary containing model metadata
        """
        pass
