"""
Interface for variable mapping between standard names and model-specific codes.

This module defines the abstract base class that all variable mappers
must implement, ensuring consistent variable naming across different models.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any


class VariableMapper(ABC):
    """
    Abstract base class for variable mappers.
    
    This interface defines the contract that all variable mappers must implement,
    ensuring consistent variable naming across different weather models.
    """
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    def get_supported_variables(self, model: str) -> List[str]:
        """
        Get list of supported standard variables for a specific model.
        
        Args:
            model: Model identifier
            
        Returns:
            List of supported standard variable names
        """
        pass
    
    @abstractmethod
    def get_model_download_config(self, model: str) -> Dict[str, Any]:
        """
        Get download configuration for a specific model.
        
        Args:
            model: Model identifier
            
        Returns:
            Dictionary containing model download configuration
        """
        pass
    
    @abstractmethod
    def validate_variables(self, variables: List[str], model: str) -> tuple[bool, List[str]]:
        """
        Validate if variables are supported for a specific model.
        
        Args:
            variables: List of standard variable names to validate
            model: Model identifier
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        pass
