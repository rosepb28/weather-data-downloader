"""
Time management utilities for weather data operations.

This module provides utilities for managing temporal aspects of weather data,
including date ranges, forecast cycles, and forecast hours.
"""

from typing import List, Optional, Tuple
from datetime import datetime, timedelta
import re
from pathlib import Path


class TimeRangeManager:
    """Manages temporal ranges for data downloads."""
    
    @staticmethod
    def parse_date_range(start_date: str, end_date: str) -> Tuple[datetime, datetime]:
        """
        Parse date range from YYYYMMDD format.
        
        Args:
            start_date: Start date in YYYYMMDD format
            end_date: End date in YYYYMMDD format
            
        Returns:
            Tuple of (start_datetime, end_datetime)
            
        Raises:
            ValueError: If date format is invalid
        """
        try:
            start_dt = datetime.strptime(start_date, "%Y%m%d")
            end_dt = datetime.strptime(end_date, "%Y%m%d")
            
            if start_dt > end_dt:
                raise ValueError("Start date must be before or equal to end date")
                
            return start_dt, end_dt
        except ValueError as e:
            raise ValueError(f"Invalid date format. Use YYYYMMDD: {e}")
    
    @staticmethod
    def generate_date_sequence(start_date: str, end_date: str) -> List[str]:
        """
        Generate sequence of dates between start and end.
        
        Args:
            start_date: Start date in YYYYMMDD format
            end_date: End date in YYYYMMDD format
            
        Returns:
            List of dates in YYYYMMDD format
        """
        start_dt, end_dt = TimeRangeManager.parse_date_range(start_date, end_date)
        dates = []
        current_dt = start_dt
        
        while current_dt <= end_dt:
            dates.append(current_dt.strftime("%Y%m%d"))
            current_dt += timedelta(days=1)
            
        return dates
    
    @staticmethod
    def validate_date_format(date: str) -> bool:
        """
        Validate if a date string is in YYYYMMDD format.
        
        Args:
            date: Date string to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not re.match(r'^\d{8}$', date):
            return False
        
        try:
            datetime.strptime(date, "%Y%m%d")
            return True
        except ValueError:
            return False


class CycleManager:
    """Manages forecast cycles for weather models."""
    
    DEFAULT_CYCLES = ["00", "06", "12", "18"]
    
    @staticmethod
    def validate_cycle(cycle: str) -> bool:
        """
        Validate if a cycle string is valid.
        
        Args:
            cycle: Cycle string to validate
            
        Returns:
            True if valid, False otherwise
        """
        return cycle in CycleManager.DEFAULT_CYCLES
    
    @staticmethod
    def parse_cycles(cycles_str: str) -> List[str]:
        """
        Parse cycles string (e.g., "00,06,12,18").
        
        Args:
            cycles_str: Comma-separated cycles string
            
        Returns:
            List of cycle strings
            
        Raises:
            ValueError: If any cycle is invalid
        """
        if not cycles_str:
            return CycleManager.DEFAULT_CYCLES
            
        cycles = [c.strip() for c in cycles_str.split(",")]
        
        for cycle in cycles:
            if not CycleManager.validate_cycle(cycle):
                raise ValueError(f"Invalid cycle: {cycle}")
                
        return cycles
    
    @staticmethod
    def get_cycle_info(cycle: str) -> dict:
        """
        Get information about a specific cycle.
        
        Args:
            cycle: Cycle string
            
        Returns:
            Dictionary with cycle information
        """
        if not CycleManager.validate_cycle(cycle):
            raise ValueError(f"Invalid cycle: {cycle}")
            
        return {
            "cycle": cycle,
            "hour": int(cycle),
            "description": f"{cycle}Z cycle",
            "next_cycle": CycleManager._get_next_cycle(cycle)
        }
    
    @staticmethod
    def _get_next_cycle(cycle: str) -> str:
        """Get the next cycle in sequence."""
        cycle_hour = int(cycle)
        next_hour = (cycle_hour + 6) % 24
        return f"{next_hour:02d}"


class ForecastManager:
    """Manages forecast hours for weather models."""
    
    @staticmethod
    def validate_forecast_hour(forecast_hour: int) -> bool:
        """
        Validate if a forecast hour is valid.
        
        Args:
            forecast_hour: Forecast hour to validate
            
        Returns:
            True if valid, False otherwise
        """
        return 0 <= forecast_hour <= 240  # GFS goes up to 240 hours
    
    @staticmethod
    def parse_forecast_hours(forecasts_str: str) -> List[int]:
        """
        Parse forecast hours string (e.g., "0,3,6,9,12").
        
        Args:
            forecasts_str: Comma-separated forecast hours string
            
        Returns:
            List of forecast hours
            
        Raises:
            ValueError: If any forecast hour is invalid
        """
        if not forecasts_str:
            return [0, 3, 6, 9, 12, 15, 18, 21, 24, 27, 30, 33, 36, 39, 42, 45, 48]
            
        forecasts = [int(f.strip()) for f in forecasts_str.split(",")]
        
        for forecast in forecasts:
            if not ForecastManager.validate_forecast_hour(forecast):
                raise ValueError(f"Invalid forecast hour: {forecast}")
                
        return sorted(forecasts)
    
    @staticmethod
    def generate_forecast_sequence(
        start_hour: int = 0, 
        end_hour: int = 48, 
        frequency: int = 3
    ) -> List[int]:
        """
        Generate sequence of forecast hours.
        
        Args:
            start_hour: Starting forecast hour
            end_hour: Ending forecast hour
            frequency: Frequency in hours
            
        Returns:
            List of forecast hours
        """
        if not ForecastManager.validate_forecast_hour(start_hour):
            raise ValueError(f"Invalid start hour: {start_hour}")
        if not ForecastManager.validate_forecast_hour(end_hour):
            raise ValueError(f"Invalid end hour: {end_hour}")
        if frequency <= 0:
            raise ValueError("Frequency must be positive")
            
        return list(range(start_hour, end_hour + 1, frequency))
    
    @staticmethod
    def get_forecast_info(forecast_hour: int) -> dict:
        """
        Get information about a specific forecast hour.
        
        Args:
            forecast_hour: Forecast hour
            
        Returns:
            Dictionary with forecast information
        """
        if not ForecastManager.validate_forecast_hour(forecast_hour):
            raise ValueError(f"Invalid forecast hour: {forecast_hour}")
            
        return {
            "forecast_hour": forecast_hour,
            "description": f"F{forecast_hour:03d}",
            "is_analysis": forecast_hour == 0,
            "is_short_range": 0 <= forecast_hour <= 48,
            "is_medium_range": 48 < forecast_hour <= 240
        }
    
    @staticmethod
    def parse_forecast_range(forecast_range: str, model_config: dict = None) -> List[int]:
        """
        Parse forecast range string (e.g., "0,0", "0,3", "3,12").
        
        Args:
            forecast_range: Forecast range string in format "start,end"
            model_config: Model configuration dictionary (optional)
            
        Returns:
            List of forecast hours in the range
            
        Raises:
            ValueError: If range format is invalid
        """
        try:
            # Split by comma and convert to integers
            parts = forecast_range.split(',')
            if len(parts) != 2:
                raise ValueError("Forecast range must be in format 'start,end'")
            
            start_hour = int(parts[0].strip())
            end_hour = int(parts[1].strip())
            
            # Validate hours
            if not ForecastManager.validate_forecast_hour(start_hour):
                raise ValueError(f"Invalid start hour: {start_hour}")
            if not ForecastManager.validate_forecast_hour(end_hour):
                raise ValueError(f"Invalid end hour: {end_hour}")
            
            if start_hour > end_hour:
                raise ValueError(f"Start hour ({start_hour}) cannot be greater than end hour ({end_hour})")
            
            # If single hour requested
            if start_hour == end_hour:
                return [start_hour]
            
            # Use model configuration if available, otherwise fallback to defaults
            if model_config and 'cycle_forecast_ranges' in model_config:
                # Get the first cycle's configuration as reference
                first_cycle = list(model_config['cycle_forecast_ranges'].keys())[0]
                ranges = model_config['cycle_forecast_ranges'][first_cycle]
                
                # Generate sequence based on model's actual frequency
                forecast_hours = []
                
                # Generate all valid forecast hours for the model
                all_valid_hours = []
                for start, end, freq in ranges:
                    for hour in range(start, end + 1, freq):
                        all_valid_hours.append(hour)
                
                # Filter to only include hours in our requested range
                for hour in all_valid_hours:
                    if start_hour <= hour <= end_hour:
                        forecast_hours.append(hour)
                
                return sorted(forecast_hours)
            else:
                # Fallback: generate every hour for short range, every 3h for longer
                if end_hour <= 120:
                    return list(range(start_hour, end_hour + 1, 1))  # Every hour
                else:
                    return list(range(start_hour, end_hour + 1, 3))  # Every 3 hours
            
        except ValueError as e:
            if "Invalid" in str(e):
                raise e
            raise ValueError(f"Invalid forecast range format: {forecast_range}. Use 'start,end' (e.g., '0,0', '0,3')")
