"""
Core interfaces for the weather data downloader system.

This module provides the abstract base classes that define the contract
for all implementations in the system.
"""

from .weather_model_provider import WeatherModelProvider
from .data_downloader import DataDownloader
from .data_processor import DataProcessor
from .storage_manager import StorageManager
from .variable_mapper import VariableMapper
from .data_subsetter import DataSubsetter

__all__ = [
    "WeatherModelProvider",
    "DataDownloader", 
    "DataProcessor",
    "StorageManager",
    "VariableMapper",
    "DataSubsetter"
]
