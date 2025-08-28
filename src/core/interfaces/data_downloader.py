"""
Interface for data download strategies.

This module defines the abstract base class that all data download
strategies must implement.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from pathlib import Path
import asyncio


class DataDownloader(ABC):
    """
    Abstract base class for data download strategies.
    
    This interface defines the contract that all download strategies
    must implement, allowing for different download methods (HTTP, FTP, etc.).
    """
    
    @abstractmethod
    async def download_file(
        self, 
        url: str, 
        destination: Path,
        chunk_size: int = 8192,
        timeout: int = 300
    ) -> bool:
        """
        Download a file from the given URL to the destination path.
        
        Args:
            url: Source URL to download from
            destination: Local path where file should be saved
            chunk_size: Size of chunks to download (bytes)
            timeout: Download timeout in seconds
            
        Returns:
            True if download was successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def download_multiple_files(
        self, 
        downloads: list[tuple[str, Path]],
        max_concurrent: int = 5,
        **kwargs
    ) -> Dict[str, bool]:
        """
        Download multiple files concurrently.
        
        Args:
            downloads: List of (url, destination) tuples
            max_concurrent: Maximum number of concurrent downloads
            **kwargs: Additional arguments passed to download_file
            
        Returns:
            Dictionary mapping URLs to download success status
        """
        pass
    
    @abstractmethod
    def get_file_size(self, url: str) -> Optional[int]:
        """
        Get the size of a remote file in bytes.
        
        Args:
            url: URL of the file
            
        Returns:
            File size in bytes, or None if unable to determine
        """
        pass
    
    @abstractmethod
    def validate_download(
        self, 
        local_file: Path, 
        expected_size: Optional[int] = None
    ) -> bool:
        """
        Validate a downloaded file.
        
        Args:
            local_file: Path to the downloaded file
            expected_size: Expected file size in bytes (optional)
            
        Returns:
            True if file is valid, False otherwise
        """
        pass
    
    @abstractmethod
    def cleanup_failed_download(self, destination: Path) -> None:
        """
        Clean up a failed download attempt.
        
        Args:
            destination: Path to the failed download file
        """
        pass
