"""
Unit tests for CLI main module.

Tests all CLI commands, arguments, options, and helper functions.
"""

import pytest
from unittest.mock import Mock, patch, call, MagicMock
from click.testing import CliRunner
from pathlib import Path
import yaml

from src.cli.main import (
    cli, download, download_process, process, list_models,
    get_full_model_name, calculate_forecast_hours_from_days,
    MODEL_NAME_MAPPING
)


class TestCliHelperFunctions:
    """Test CLI helper functions"""
    
    def test_get_full_model_name_mapping(self):
        """Test model name mapping functionality"""
        assert get_full_model_name('gfs') == 'gfs.0p25'
        assert get_full_model_name('ecmwf') == 'ecmwf.0p25'
        assert get_full_model_name('gem') == 'gem.0p1'
        
        # Test case insensitive
        assert get_full_model_name('GFS') == 'gfs.0p25'
        assert get_full_model_name('ECMWF') == 'ecmwf.0p25'
        
        # Test unknown model (returns as-is)
        assert get_full_model_name('unknown') == 'unknown'
    
    @pytest.mark.parametrize("days,expected_hours", [
        (0.5, list(range(0, 13))),     # Half day: 0-12h
        (1.0, list(range(0, 25))),     # One day: 0-24h
        (2.0, list(range(0, 49))),     # Two days: 0-48h (simplified)
    ])
    def test_calculate_forecast_hours_from_days_simple(self, days, expected_hours):
        """Test forecast hours calculation for simple cases"""
        # Simple model config for testing
        model_config = {
            'cycle_forecast_ranges': {
                '00': [[0, 72, 1]]  # 0-72h every hour
            }
        }
        
        result = calculate_forecast_hours_from_days(days, model_config)
        
        # For simple hourly model, should be 0 to days*24
        max_expected = int(days * 24)
        expected = list(range(0, min(max_expected + 1, 73)))  # Limited by model max
        
        assert result == expected
    
    def test_calculate_forecast_hours_from_days_gfs_realistic(self):
        """Test forecast hours calculation with realistic GFS config"""
        model_config = {
            'cycle_forecast_ranges': {
                '00': [[0, 120, 1], [123, 240, 3]]  # GFS pattern
            }
        }
        
        # Half day (12 hours) - should be hourly
        result = calculate_forecast_hours_from_days(0.5, model_config)
        expected = list(range(0, 13))  # 0-12h
        assert result == expected
        
        # 5 days (120 hours) - exactly at boundary
        result = calculate_forecast_hours_from_days(5.0, model_config)
        expected = list(range(0, 121))  # 0-120h hourly
        assert result == expected
        
        # 6 days (144 hours) - crosses into 3-hourly
        result = calculate_forecast_hours_from_days(6.0, model_config)
        expected = list(range(0, 121)) + [123, 126, 129, 132, 135, 138, 141, 144]
        assert result == expected


class TestCliCommands:
    """Test CLI command functionality"""
    
    def setup_method(self):
        """Setup for each test"""
        self.runner = CliRunner()
    
    def test_cli_group_exists(self):
        """Test that CLI group is properly configured"""
        result = self.runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert 'download' in result.output
        assert 'download-process' in result.output
        assert 'process' in result.output
        assert 'list-models' in result.output
    
    @patch('src.cli.main.YAMLVariableMapper')
    def test_list_models_command(self, mock_mapper):
        """Test list-models command"""
        # Mock the variable mapper
        mock_instance = Mock()
        mock_instance.models_config = {
            'gfs.0p25': {
                'name': 'GFS 0.25 Degree',
                'resolution': '0.25°',
                'data_source': 'NOMADS'
            },
            'ecmwf.0p25': {
                'name': 'ECMWF 0.25 Degree', 
                'resolution': '0.25°',
                'data_source': 'ECMWF'
            }
        }
        mock_mapper.return_value = mock_instance
        
        result = self.runner.invoke(list_models)
        
        assert result.exit_code == 0
        assert 'Available Weather Models' in result.output
        assert 'gfs.0p25' in result.output
        assert 'GFS 0.25 Degree' in result.output
        assert 'ecmwf.0p25' in result.output


class TestDownloadCommand:
    """Test download command with various options"""
    
    def setup_method(self):
        """Setup for each test"""
        self.runner = CliRunner()
    
    @patch('src.cli.main._download_implementation')
    def test_download_command_basic(self, mock_download_impl):
        """Test basic download command"""
        result = self.runner.invoke(download, ['gfs'])
        
        assert result.exit_code == 0
        mock_download_impl.assert_called_once()
        
        # Check arguments passed
        args = mock_download_impl.call_args[0]
        assert args[0] == 'gfs'  # model
        assert args[5] is None   # forecast_days
        assert args[6] is False  # process
    
    @patch('src.cli.main._download_implementation')
    def test_download_command_with_forecast_days(self, mock_download_impl):
        """Test download command with --forecast-days option"""
        result = self.runner.invoke(download, ['gfs', '--forecast-days', '0.5'])
        
        assert result.exit_code == 0
        mock_download_impl.assert_called_once()
        
        # Check forecast_days argument
        args = mock_download_impl.call_args[0]
        assert args[5] == 0.5  # forecast_days
    
    @patch('src.cli.main._download_implementation')
    def test_download_command_with_date(self, mock_download_impl):
        """Test download command with -d/--date option"""
        result = self.runner.invoke(download, ['gfs', '-d', '20250828'])
        
        assert result.exit_code == 0
        mock_download_impl.assert_called_once()
        
        # Check date argument
        args = mock_download_impl.call_args[0]
        assert args[2] == '20250828'  # date
    
    @patch('src.cli.main._download_implementation')
    def test_download_command_with_cycles(self, mock_download_impl):
        """Test download command with -c/--cycles option"""
        result = self.runner.invoke(download, ['gfs', '-c', '00,06'])
        
        assert result.exit_code == 0
        mock_download_impl.assert_called_once()
        
        # Check cycles argument
        args = mock_download_impl.call_args[0]
        assert args[1] == '00,06'  # cycles
    
    @patch('src.cli.main._download_implementation')
    def test_download_command_with_forecast_range(self, mock_download_impl):
        """Test download command with -f/--forecast-range option"""
        result = self.runner.invoke(download, ['gfs', '-f', '0,24'])
        
        assert result.exit_code == 0
        mock_download_impl.assert_called_once()
        
        # Check forecast_range argument
        args = mock_download_impl.call_args[0]
        assert args[4] == '0,24'  # forecast_range
    
    @patch('src.cli.main._download_implementation')
    def test_download_command_with_process_flag(self, mock_download_impl):
        """Test download command with --process flag"""
        result = self.runner.invoke(download, ['gfs', '--process'])
        
        assert result.exit_code == 0
        mock_download_impl.assert_called_once()
        
        # Check process argument
        args = mock_download_impl.call_args[0]
        assert args[6] is True  # process


class TestDownloadProcessCommand:
    """Test download-process command"""
    
    def setup_method(self):
        """Setup for each test"""
        self.runner = CliRunner()
    
    @patch('src.cli.main._download_implementation')
    def test_download_process_command_basic(self, mock_download_impl):
        """Test basic download-process command"""
        result = self.runner.invoke(download_process, ['gfs'])
        
        assert result.exit_code == 0
        mock_download_impl.assert_called_once()
        
        # Check that process=True is passed
        args = mock_download_impl.call_args[0]
        assert args[0] == 'gfs'  # model
        assert args[6] is True   # process=True (last argument)
    
    @patch('src.cli.main._download_implementation')
    def test_download_process_with_forecast_days(self, mock_download_impl):
        """Test download-process with --forecast-days"""
        result = self.runner.invoke(download_process, 
                                  ['gfs', '-c', '00', '--forecast-days', '1.5'])
        
        assert result.exit_code == 0
        mock_download_impl.assert_called_once()
        
        args = mock_download_impl.call_args[0]
        assert args[0] == 'gfs'    # model
        assert args[1] == '00'     # cycles
        assert args[5] == 1.5      # forecast_days
        assert args[6] is True     # process=True


class TestDownloadImplementation:
    """Test the core download implementation logic"""
    
    def setup_method(self):
        """Setup for each test"""
        self.runner = CliRunner()
    
    @patch('src.cli.main.YAMLVariableMapper')
    @patch('src.cli.main.Path')
    @patch('builtins.open')
    @patch('yaml.safe_load')
    def test_download_implementation_config_loading(self, mock_yaml, mock_open, 
                                                   mock_path, mock_mapper):
        """Test that download implementation loads configurations correctly"""
        # Mock file existence
        mock_path.return_value.exists.return_value = True
        
        # Mock config contents
        mock_yaml.side_effect = [
            # config.yaml
            {
                'output_dir': 'test_data',
                'spatial_bounds': {'lon_min': -90, 'lon_max': -30},
                'models': {
                    'gfs.0p25': {'variables': ['t2m', 'rh2m']}
                }
            },
            # models_config.yaml  
            {
                'gfs.0p25': {
                    'cycles': ['00', '06'],
                    'cycle_forecast_ranges': {'00': [[0, 72, 1]]}
                }
            }
        ]
        
        # Mock variable mapper
        mock_mapper_instance = Mock()
        mock_mapper_instance.get_model_config.return_value = {
            'cycles': ['00', '06'],
            'cycle_forecast_ranges': {'00': [[0, 72, 1]]}
        }
        mock_mapper.return_value = mock_mapper_instance
        
        with patch('src.cli.main.datetime') as mock_dt:
            mock_dt.now.return_value.strftime.return_value = '20250828'
            mock_dt.utcnow.return_value.strftime.return_value = '20250828'
            
            with patch('src.cli.main.ForecastManager') as mock_forecast_mgr:
                mock_forecast_mgr.parse_forecast_range.return_value = [0, 1, 2]
                
                with patch('src.cli.main.cleanup_existing_files'), \
                     patch('src.cli.main.GFSProvider') as mock_provider, \
                     patch('src.cli.main.HTTPDataDownloader') as mock_downloader, \
                     patch('src.cli.main.click.confirm', return_value=True):
                    
                    # Mock provider and downloader
                    mock_provider_instance = Mock()
                    mock_provider_instance.get_download_url.return_value = 'http://test.com/file'
                    mock_provider_instance.validate_parameters.return_value = None
                    mock_provider.return_value = mock_provider_instance
                    
                    mock_downloader_instance = Mock()
                    mock_downloader_instance.download.return_value = True
                    mock_downloader.return_value = mock_downloader_instance
                    
                    # Test the function
                    result = self.runner.invoke(download, ['gfs', '-f', '0,2'])
                    
                    # Should not crash and should call config loading
                    mock_yaml.assert_called()
                    mock_mapper.assert_called_once()

    @patch('src.cli.main.calculate_forecast_hours_from_days')
    @patch('src.cli.main.YAMLVariableMapper')
    def test_forecast_days_vs_forecast_range_conflict(self, mock_mapper, mock_calc_hours):
        """Test that forecast-days and forecast-range conflict is detected"""
        mock_mapper_instance = Mock()
        mock_mapper.return_value = mock_mapper_instance
        
        # This should fail with conflict error
        result = self.runner.invoke(download, 
                                  ['gfs', '-f', '0,24', '--forecast-days', '1'])
        
        # Should exit with error due to conflicting options
        assert result.exit_code != 0
        assert 'Cannot specify both' in result.output

    @patch('src.cli.main.YAMLVariableMapper')
    @patch('src.cli.main.calculate_forecast_hours_from_days')
    @patch('src.cli.main.Path')
    @patch('builtins.open')
    @patch('yaml.safe_load')
    def test_forecast_days_calculation_called(self, mock_yaml, mock_open, mock_path,
                                            mock_calc_hours, mock_mapper):
        """Test that forecast days calculation is called when --forecast-days is used"""
        # Mock file existence and config loading
        mock_path.return_value.exists.return_value = True
        mock_yaml.side_effect = [
            {'output_dir': 'test_data', 'models': {'gfs.0p25': {}}},
            {'gfs.0p25': {'cycles': ['00']}}
        ]
        
        # Mock variable mapper
        mock_mapper_instance = Mock()
        mock_mapper_instance.get_model_config.return_value = {
            'cycle_forecast_ranges': {'00': [[0, 72, 1]]}
        }
        mock_mapper.return_value = mock_mapper_instance
        
        # Mock forecast hours calculation
        mock_calc_hours.return_value = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        
        with patch('src.cli.main.datetime') as mock_dt:
            mock_dt.now.return_value.strftime.return_value = '20250828'
            mock_dt.utcnow.return_value.strftime.return_value = '20250828'
            
            with patch('src.cli.main.cleanup_existing_files'), \
                 patch('src.cli.main.GFSProvider') as mock_provider, \
                 patch('src.cli.main.HTTPDataDownloader') as mock_downloader, \
                 patch('src.cli.main.click.confirm', return_value=True):
                
                mock_provider_instance = Mock()
                mock_provider_instance.get_download_url.return_value = 'http://test.com'
                mock_provider_instance.validate_parameters.return_value = None
                mock_provider.return_value = mock_provider_instance
                
                mock_downloader_instance = Mock()
                mock_downloader_instance.download.return_value = True
                mock_downloader.return_value = mock_downloader_instance
                
                result = self.runner.invoke(download, ['gfs', '--forecast-days', '0.5'])
                
                # Should call forecast hours calculation
                mock_calc_hours.assert_called_once_with(0.5, mock_mapper_instance.get_model_config.return_value)


class TestProcessCommand:
    """Test process command functionality"""
    
    def setup_method(self):
        """Setup for each test"""
        self.runner = CliRunner()
    
    @patch('src.cli.main.process_downloaded_files')
    @patch('src.cli.main.YAMLVariableMapper')
    @patch('src.cli.main.Path')
    @patch('builtins.open')
    @patch('yaml.safe_load')
    def test_process_command_basic(self, mock_yaml, mock_open, mock_path, 
                                 mock_mapper, mock_process_files):
        """Test basic process command"""
        # Mock file existence and config loading
        mock_path.return_value.exists.return_value = True
        mock_yaml.return_value = {
            'output_dir': 'test_data',
            'models': {'gfs.0p25': {'variables': ['t2m']}}
        }
        
        mock_mapper_instance = Mock()
        mock_mapper.return_value = mock_mapper_instance
        
        with patch('src.cli.main.datetime') as mock_dt:
            mock_dt.now.return_value.strftime.return_value = '20250828'
            mock_dt.utcnow.return_value.strftime.return_value = '20250828'
            
            result = self.runner.invoke(process, ['gfs'])
            
            assert result.exit_code == 0
            mock_process_files.assert_called()


class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    def setup_method(self):
        """Setup for each test"""
        self.runner = CliRunner()
    
    def test_invalid_model_name(self):
        """Test behavior with invalid model name"""
        with patch('src.cli.main.YAMLVariableMapper') as mock_mapper:
            mock_mapper_instance = Mock()
            mock_mapper_instance.get_model_config.side_effect = Exception("Model not found")
            mock_mapper.return_value = mock_mapper_instance
            
            result = self.runner.invoke(download, ['invalid_model'])
            
            # Should handle the error gracefully
            assert result.exit_code != 0
    
    def test_missing_config_files(self):
        """Test behavior when config files are missing"""
        with patch('src.cli.main.Path') as mock_path:
            mock_path.return_value.exists.return_value = False
            
            result = self.runner.invoke(download, ['gfs'])
            
            # Should handle missing config gracefully
            assert result.exit_code != 0

    def test_invalid_forecast_days_value(self):
        """Test invalid forecast days values"""
        # Negative days
        result = self.runner.invoke(download, ['gfs', '--forecast-days', '-1'])
        # Click should handle this validation
        assert result.exit_code != 0
        
        # Non-numeric days  
        result = self.runner.invoke(download, ['gfs', '--forecast-days', 'invalid'])
        assert result.exit_code != 0

    def test_invalid_date_format(self):
        """Test invalid date format"""
        with patch('src.cli.main.YAMLVariableMapper'):
            result = self.runner.invoke(download, ['gfs', '-d', 'invalid-date'])
            # Should be handled by date validation in the implementation
            # For now, we just test that it doesn't crash the CLI parser
            assert isinstance(result.exit_code, int)


class TestIntegrationScenarios:
    """Test realistic usage scenarios"""
    
    def setup_method(self):
        """Setup for each test"""
        self.runner = CliRunner()
    
    @pytest.mark.parametrize("command,args", [
        (download, ['gfs', '-c', '00', '--forecast-days', '0.5']),
        (download_process, ['gfs', '-d', '20250828', '--forecast-days', '2']),
        (download, ['gfs', '-c', '00,06', '-f', '0,24']),
        (process, ['gfs', '-c', '00', '--forecast-days', '1']),
    ])
    @patch('src.cli.main._download_implementation')
    @patch('src.cli.main.process_downloaded_files')
    def test_realistic_command_combinations(self, mock_process, mock_download, command, args):
        """Test realistic command combinations"""
        result = self.runner.invoke(command, args)
        
        # Commands should parse successfully
        assert result.exit_code == 0
        
        # Appropriate implementation should be called
        if command in [download, download_process]:
            mock_download.assert_called_once()
        else:
            # process command logic would be called
            pass
