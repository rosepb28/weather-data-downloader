"""
File operations utilities for the weather data downloader system.

This module provides utilities for common file operations including
file validation, directory creation, and file management.
"""

import os
import shutil
from pathlib import Path
from typing import Optional, List
import hashlib


class FileOperations:
    """Utilities for file operations."""
    
    @staticmethod
    def ensure_directory(path: Path) -> Path:
        """
        Ensure a directory exists, creating it if necessary.
        
        Args:
            path: Path to the directory
            
        Returns:
            Path to the created/existing directory
        """
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @staticmethod
    def safe_remove(path: Path) -> bool:
        """
        Safely remove a file or directory.
        
        Args:
            path: Path to remove
            
        Returns:
            True if removal was successful, False otherwise
        """
        try:
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path)
            return True
        except (OSError, PermissionError):
            return False
    
    @staticmethod
    def get_file_size(path: Path) -> Optional[int]:
        """
        Get file size in bytes.
        
        Args:
            path: Path to the file
            
        Returns:
            File size in bytes, or None if file doesn't exist
        """
        try:
            return path.stat().st_size if path.exists() else None
        except OSError:
            return None
    
    @staticmethod
    def calculate_file_hash(path: Path, algorithm: str = "md5") -> Optional[str]:
        """
        Calculate file hash.
        
        Args:
            path: Path to the file
            algorithm: Hash algorithm to use
            
        Returns:
            File hash as hex string, or None if error
        """
        try:
            hash_func = getattr(hashlib, algorithm)()
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_func.update(chunk)
            return hash_func.hexdigest()
        except (OSError, AttributeError):
            return None
    
    @staticmethod
    def list_files(
        directory: Path, 
        pattern: str = "*", 
        recursive: bool = False
    ) -> List[Path]:
        """
        List files in a directory matching a pattern.
        
        Args:
            directory: Directory to search
            pattern: File pattern to match
            recursive: Whether to search recursively
            
        Returns:
            List of matching file paths
        """
        if not directory.exists() or not directory.is_dir():
            return []
        
        if recursive:
            return list(directory.rglob(pattern))
        else:
            return list(directory.glob(pattern))
    
    @staticmethod
    def get_file_extension(path: Path) -> str:
        """
        Get file extension.
        
        Args:
            path: Path to the file
            
        Returns:
            File extension (including the dot)
        """
        return path.suffix
    
    @staticmethod
    def is_netcdf_file(path: Path) -> bool:
        """
        Check if a file is a NetCDF file.
        
        Args:
            path: Path to the file
            
        Returns:
            True if file is NetCDF, False otherwise
        """
        return path.suffix.lower() in ['.nc', '.netcdf', '.cdf']
    
    @staticmethod
    def backup_file(path: Path, backup_suffix: str = ".backup") -> Optional[Path]:
        """
        Create a backup of a file.
        
        Args:
            path: Path to the file to backup
            backup_suffix: Suffix for the backup file
            
        Returns:
            Path to the backup file, or None if error
        """
        if not path.exists():
            return None
        
        backup_path = path.with_suffix(path.suffix + backup_suffix)
        try:
            shutil.copy2(path, backup_path)
            return backup_path
        except (OSError, PermissionError):
            return None
    
    @staticmethod
    def get_disk_usage(path: Path) -> Optional[int]:
        """
        Get disk usage for a path in bytes.
        
        Args:
            path: Path to check
            
        Returns:
            Disk usage in bytes, or None if error
        """
        try:
            total, used, free = shutil.disk_usage(path)
            return used
        except OSError:
            return None
