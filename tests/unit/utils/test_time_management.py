"""
Unit tests for time management utilities.

Tests actual functionality from time_management.py module.
"""

import pytest
from datetime import datetime, timedelta

from src.utils.time_management import ForecastManager, TimeRangeManager, CycleManager


class TestForecastManager:
    """Test ForecastManager functionality"""
    
    @pytest.mark.parametrize("forecast_hour,expected", [
        (0, True),
        (24, True),
        (240, True),
        (-1, False),
        (241, False),
    ])
    def test_validate_forecast_hour(self, forecast_hour, expected):
        """Test forecast hour validation"""
        result = ForecastManager.validate_forecast_hour(forecast_hour)
        assert result == expected
    
    @pytest.mark.parametrize("forecasts_str,expected", [
        ("0,3,6", [0, 3, 6]),
        ("0,6,3", [0, 3, 6]),  # Should sort
        ("24,12,0", [0, 12, 24]),  # Should sort
    ])
    def test_parse_forecast_hours_valid(self, forecasts_str, expected):
        """Test forecast hours string parsing"""
        result = ForecastManager.parse_forecast_hours(forecasts_str)
        assert result == expected
    
    def test_parse_forecast_hours_empty_gives_default(self):
        """Test empty string gives default forecast hours"""
        result = ForecastManager.parse_forecast_hours("")
        assert isinstance(result, list)
        assert len(result) > 0
        assert 0 in result
    
    def test_parse_forecast_hours_invalid(self):
        """Test invalid forecast hours"""
        with pytest.raises(ValueError, match="Invalid forecast hour"):
            ForecastManager.parse_forecast_hours("0,3,300")  # 300 is invalid
    
    @pytest.mark.parametrize("start,end,freq,expected", [
        (0, 12, 3, [0, 3, 6, 9, 12]),
        (0, 24, 6, [0, 6, 12, 18, 24]),
        (12, 12, 1, [12]),  # Single hour
    ])
    def test_generate_forecast_sequence(self, start, end, freq, expected):
        """Test forecast sequence generation"""
        result = ForecastManager.generate_forecast_sequence(start, end, freq)
        assert result == expected
    
    def test_generate_forecast_sequence_invalid_start(self):
        """Test invalid start hour"""
        with pytest.raises(ValueError, match="Invalid start hour"):
            ForecastManager.generate_forecast_sequence(-1, 24, 3)
    
    def test_generate_forecast_sequence_invalid_frequency(self):
        """Test invalid frequency"""
        with pytest.raises(ValueError, match="Frequency must be positive"):
            ForecastManager.generate_forecast_sequence(0, 24, 0)
    
    def test_get_forecast_info_valid(self):
        """Test getting forecast information"""
        result = ForecastManager.get_forecast_info(24)
        assert isinstance(result, dict)
        assert "forecast_hour" in result
        assert result["forecast_hour"] == 24
    
    def test_get_forecast_info_invalid(self):
        """Test invalid forecast hour for info"""
        with pytest.raises(ValueError, match="Invalid forecast hour"):
            ForecastManager.get_forecast_info(300)


class TestTimeRangeManager:
    """Test TimeRangeManager functionality"""
    
    def test_parse_date_range_valid(self):
        """Test valid date range parsing"""
        start_dt, end_dt = TimeRangeManager.parse_date_range("20250828", "20250830")
        
        assert isinstance(start_dt, datetime)
        assert isinstance(end_dt, datetime)
        assert start_dt.year == 2025
        assert start_dt.month == 8
        assert start_dt.day == 28
        assert end_dt.day == 30
    
    def test_parse_date_range_invalid_order(self):
        """Test invalid date order"""
        with pytest.raises(ValueError, match="Start date must be before or equal"):
            TimeRangeManager.parse_date_range("20250830", "20250828")
    
    def test_parse_date_range_invalid_format(self):
        """Test invalid date format"""
        with pytest.raises(ValueError, match="Invalid date format"):
            TimeRangeManager.parse_date_range("invalid", "20250828")
    
    def test_generate_date_sequence_single_day(self):
        """Test single day sequence"""
        result = TimeRangeManager.generate_date_sequence("20250828", "20250828")
        assert result == ["20250828"]
    
    def test_generate_date_sequence_multiple_days(self):
        """Test multiple days sequence"""
        result = TimeRangeManager.generate_date_sequence("20250828", "20250830")
        assert result == ["20250828", "20250829", "20250830"]


class TestCycleManager:
    """Test CycleManager functionality"""
    
    @pytest.mark.parametrize("cycle,expected", [
        ("00", True),
        ("06", True),
        ("12", True),
        ("18", True),
        ("03", False),
        ("25", False),
    ])
    def test_is_valid_cycle(self, cycle, expected):
        """Test cycle validation"""
        result = CycleManager.validate_cycle(cycle)
        assert result == expected
    
    def test_get_cycle_info_valid(self):
        """Test getting cycle information"""
        result = CycleManager.get_cycle_info("00")
        assert isinstance(result, dict)
        assert "cycle" in result
        assert result["cycle"] == "00"
    
    def test_get_cycle_info_invalid(self):
        """Test invalid cycle for info"""
        with pytest.raises(ValueError, match="Invalid cycle"):
            CycleManager.get_cycle_info("25")


class TestParseRangeFunction:
    """Test the parse_forecast_range function used by CLI"""
    
    def test_parse_forecast_range_exists(self):
        """Test that parse_forecast_range function exists and works"""
        from src.utils.time_management import ForecastManager
        
        # This function should exist since it's used in CLI
        assert hasattr(ForecastManager, 'parse_forecast_range')
    
    def test_parse_forecast_range_simple_case(self):
        """Test simple forecast range parsing"""
        simple_config = {
            'cycle_forecast_ranges': {
                '00': [[0, 72, 1]]  # 0-72h every hour
            }
        }
        
        result = ForecastManager.parse_forecast_range("0,24", simple_config)
        expected = list(range(0, 25))  # 0-24h
        assert result == expected


class TestIntegration:
    """Test integration between time management classes"""
    
    def test_full_workflow_realistic(self):
        """Test realistic workflow with all managers"""
        # Generate date sequence
        dates = TimeRangeManager.generate_date_sequence("20250828", "20250829")
        assert len(dates) == 2
        
        # Validate cycles
        assert CycleManager.validate_cycle("00")
        assert CycleManager.validate_cycle("12")
        
        # Generate forecast sequence
        forecasts = ForecastManager.generate_forecast_sequence(0, 24, 6)
        assert forecasts == [0, 6, 12, 18, 24]
        
        # Validate all forecast hours
        for forecast in forecasts:
            assert ForecastManager.validate_forecast_hour(forecast)


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_forecast_manager_boundary_values(self):
        """Test boundary values for forecast validation"""
        # Minimum valid
        assert ForecastManager.validate_forecast_hour(0)
        # Maximum valid
        assert ForecastManager.validate_forecast_hour(240)
        # Just outside boundaries
        assert not ForecastManager.validate_forecast_hour(-1)
        assert not ForecastManager.validate_forecast_hour(241)
    
    def test_time_range_same_day(self):
        """Test time range with same start and end date"""
        start_dt, end_dt = TimeRangeManager.parse_date_range("20250828", "20250828")
        assert start_dt == end_dt
    
    def test_cycle_manager_all_valid_cycles(self):
        """Test all standard cycles are valid"""
        valid_cycles = ["00", "06", "12", "18"]
        for cycle in valid_cycles:
            assert CycleManager.validate_cycle(cycle)
            # Should not raise exception
            info = CycleManager.get_cycle_info(cycle)
            assert info["cycle"] == cycle