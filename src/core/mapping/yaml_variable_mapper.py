"""
YAML-based variable mapper implementation.

This module provides the YAML-based implementation of the VariableMapper interface,
reading variable mappings from a YAML configuration file.
"""

import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from ..interfaces.variable_mapper import VariableMapper


class YAMLVariableMapper(VariableMapper):
    """
    YAML-based implementation of the VariableMapper interface.
    
    This class reads variable mappings from a YAML configuration file and provides
    methods to convert between standard variable names and model-specific codes.
    """
    
    def __init__(self, mapping_file: Path):
        """
        Initialize the YAML variable mapper.
        
        Args:
            mapping_file: Path to the YAML mapping configuration file
        """
        self.mapping_file = mapping_file
        self.mapping = self._load_mapping()
        
        # Load model technical configurations
        models_config_path = Path(__file__).parent.parent.parent.parent / "models_config.yaml"
        with open(models_config_path, 'r') as f:
            self.models_config = yaml.safe_load(f)
        
        # Model name to config key mapping
        self.model_keys = {
            "gfs": "gfs.0p25",
            "ecmwf": "ecmwf.0p25", 
            "gem": "gem.0p1"
        }
    
    def _get_model_key(self, model: str) -> str:
        """
        Get the config key for a model.
        
        Args:
            model: Model identifier (e.g., 'gfs', 'ecmwf', 'gem')
            
        Returns:
            Config key for the model
            
        Raises:
            ValueError: If model is not supported
        """
        if model not in self.model_keys:
            raise ValueError(f"Unsupported model: {model}")
        
        return self.model_keys[model]
    
    def _load_mapping(self) -> Dict[str, Any]:
        """
        Load the YAML mapping configuration.
        
        Returns:
            Dictionary containing the mapping configuration
            
        Raises:
            FileNotFoundError: If mapping file doesn't exist
            yaml.YAMLError: If YAML file is malformed
        """
        if not self.mapping_file.exists():
            raise FileNotFoundError(f"Mapping file not found: {self.mapping_file}")
        
        try:
            with open(self.mapping_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Error parsing YAML file: {e}")
    
    def get_model_variable_code(self, standard_variable: str, model: str) -> str:
        """
        Get the model-specific code for a standard variable name.
        
        Args:
            standard_variable: Standard variable name (e.g., 't2m', 'u10m')
            model: Model identifier (e.g., 'gfs', 'ecmwf', 'gem')
            
        Returns:
            Model-specific variable code
            
        Raises:
            ValueError: If variable or model is not supported
        """
        if standard_variable not in self.mapping['standard_variables']:
            raise ValueError(f"Unknown standard variable: {standard_variable}")
        
        variable_config = self.mapping['standard_variables'][standard_variable]
        
        if model not in variable_config:
            raise ValueError(f"Model {model} not supported for variable {standard_variable}")
        
        return variable_config[model]
    
    def get_standard_variable_name(self, model_code: str, model: str) -> str:
        """
        Get the standard variable name for a model-specific code.
        
        Args:
            model_code: Model-specific variable code
            model: Model identifier
            
        Returns:
            Standard variable name
            
        Raises:
            ValueError: If code or model is not supported
        """
        for std_var, config in self.mapping['standard_variables'].items():
            if config.get(model) == model_code:
                return std_var
        
        raise ValueError(f"Unknown model code: {model_code} for model: {model}")
    
    def get_variable_metadata(self, standard_variable: str) -> Dict[str, Any]:
        """
        Get metadata for a standard variable.
        
        Args:
            standard_variable: Standard variable name
            
        Returns:
            Dictionary containing variable metadata (description, units, levels)
            
        Raises:
            ValueError: If variable is not supported
        """
        if standard_variable not in self.mapping['standard_variables']:
            raise ValueError(f"Unknown standard variable: {standard_variable}")
        
        return self.mapping['standard_variables'][standard_variable].copy()
    
    def get_supported_variables(self, model: str) -> List[str]:
        """
        Get list of supported standard variables for a specific model.
        
        Args:
            model: Model identifier
            
        Returns:
            List of supported standard variable names
        """
        supported = []
        for std_var, config in self.mapping['standard_variables'].items():
            if model in config:
                supported.append(std_var)
        return supported
    
    def get_model_download_config(self, model: str) -> Dict[str, Any]:
        """
        Get download configuration for a specific model.
        
        Args:
            model: Model identifier
            
        Returns:
            Dictionary containing model download configuration
            
        Raises:
            ValueError: If model is not supported
        """
        model_key = self._get_model_key(model)
        if model_key not in self.models_config['models']:
            raise ValueError(f"Unsupported model: {model}")
        
        return self.models_config['models'][model_key]
    
    def validate_variables(self, variables: List[str], model: str) -> tuple[bool, List[str]]:
        """
        Validate if variables are supported for a specific model.
        
        Args:
            variables: List of standard variable names to validate
            model: Model identifier
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check if model is supported
        if model not in [m.split('.')[0] for m in self.models_config['models'].keys()]:
            errors.append(f"Model {model} not supported")
            return False, errors
        
        # Check if variables are supported for this model
        supported_vars = self.get_supported_variables(model)
        
        for var in variables:
            if var not in supported_vars:
                errors.append(f"Variable {var} is not supported for model {model}")
        
        return len(errors) == 0, errors
    
    def get_forecast_intervals(self, model: str) -> Dict[str, int]:
        """
        Get forecast intervals for a specific model.
        
        Args:
            model: Model identifier
            
        Returns:
            Dictionary mapping time ranges to forecast intervals in hours
        """
        config = self.get_model_download_config(model)
        return config.get('forecast_intervals', {})
    
    def get_forecast_hours_for_model(self, model: str, max_forecast: int = 240) -> List[int]:
        """
        Get all available forecast hours for a specific model.
        
        Args:
            model: Model identifier
            max_forecast: Maximum forecast hour
            
        Returns:
            List of forecast hours
            
        Raises:
            ValueError: If model is not supported
        """
        model_key = self._get_model_key(model)
        if model_key not in self.models_config['models']:
            raise ValueError(f"Unsupported model: {model}")
        
        model_config = self.models_config['models'][model_key]
        all_forecast_hours = set()
        
        # Get forecast hours from all cycles using ranges
        for cycle, ranges in model_config['cycle_forecast_ranges'].items():
            for range_tuple in ranges:
                start, end, frequency = range_tuple  # Unpack tuple: [start, end, frequency]
                
                # Generate forecast hours for this range
                for hour in range(start, end + 1, frequency):
                    if hour <= max_forecast:
                        all_forecast_hours.add(hour)
        
        return sorted(list(all_forecast_hours))
    
    def get_cycles_for_model(self, model: str) -> List[str]:
        """
        Get all available cycles for a specific model.
        
        Args:
            model: Model identifier (e.g., 'gfs', 'ecmwf', 'gem')
            
        Returns:
            List of available cycles
            
        Raises:
            ValueError: If model is not supported
        """
        model_key = self._get_model_key(model)
        if model_key not in self.models_config['models']:
            raise ValueError(f"Unsupported model: {model}")
        
        return self.models_config['models'][model_key]['cycles']
    
    def get_forecast_hours_for_cycle(self, model: str, cycle: str) -> List[int]:
        """
        Get available forecast hours for a specific model and cycle.
        
        Args:
            model: Model identifier (e.g., 'gfs', 'ecmwf', 'gem')
            cycle: Forecast cycle (e.g., '00', '06', '12', '18')
            
        Returns:
            List of available forecast hours for the cycle
            
        Raises:
            ValueError: If model or cycle is not supported
        """
        model_key = self._get_model_key(model)
        if model_key not in self.models_config['models']:
            raise ValueError(f"Unsupported model: {model}")
        
        model_config = self.models_config['models'][model_key]
        if cycle not in model_config['cycle_forecast_ranges']:
            raise ValueError(f"Unsupported cycle {cycle} for model {model}")
        
        forecast_hours = []
        ranges = model_config['cycle_forecast_ranges'][cycle]
        
        # Generate forecast hours from ranges
        for range_tuple in ranges:
            start, end, frequency = range_tuple  # Unpack tuple: [start, end, frequency]
            
            for hour in range(start, end + 1, frequency):
                forecast_hours.append(hour)
        
        return sorted(forecast_hours)
    
    def get_model_config(self, model: str) -> Dict[str, Any]:
        """
        Get complete configuration for a specific model.
        
        Args:
            model: Model name (e.g., 'gfs', 'ecmwf', 'gem')
            
        Returns:
            Dictionary with complete model configuration
        """
        return self.get_model_download_config(model)
