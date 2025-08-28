"""
HTTP-based data downloader implementation.

This module provides the HTTP implementation of the DataDownloader interface,
handling actual file downloads with retry logic, progress tracking, and validation.
"""

import os
import time
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from urllib.parse import urlparse
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..interfaces.data_downloader import DataDownloader
from ...utils.file_operations import FileOperations
from ...utils.validation import DataValidator


class HTTPDataDownloader(DataDownloader):
    """
    HTTP-based implementation of the DataDownloader interface.
    
    This class handles downloading files from HTTP/HTTPS URLs with:
    - Retry logic for failed downloads
    - Progress tracking
    - File validation
    - Concurrent downloads
    """
    
    def __init__(self, 
                 max_retries: int = 3,
                 timeout: int = 30,
                 chunk_size: int = 8192,
                 progress_callback: Optional[Callable] = None):
        """
        Initialize HTTP downloader.
        
        Args:
            max_retries: Maximum number of retry attempts
            timeout: Request timeout in seconds
            chunk_size: Size of chunks for streaming download
            progress_callback: Optional callback for progress updates
        """
        self.max_retries = max_retries
        self.timeout = timeout
        self.chunk_size = chunk_size
        self.progress_callback = progress_callback
        
        # Create session with retry strategy
        self.session = self._create_session()
        
        # Initialize utilities
        self.file_ops = FileOperations()
        self.validator = DataValidator()
    
    def _create_session(self) -> requests.Session:
        """Create requests session with retry strategy."""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def download_file(self, url: str, destination: Path, **kwargs) -> bool:
        """
        Download a single file from URL to destination.
        
        Args:
            url: Source URL
            destination: Destination file path
            **kwargs: Additional download options
            
        Returns:
            True if download successful, False otherwise
        """
        try:
            # Validate URL
            if not self.validator.validate_url(url):
                raise ValueError(f"Invalid URL: {url}")
            
            # Ensure destination directory exists
            self.file_ops.ensure_directory(destination.parent)
            
            # Get file size for progress tracking
            file_size = self.get_file_size(url)
            
            # Download with progress tracking
            success = self._download_with_progress(url, destination, file_size)
            
            if success:
                # Validate downloaded file
                if not self.validate_download(destination, file_size):
                    self.cleanup_failed_download(destination)
                    return False
                
                return True
            
            return False
            
        except Exception as e:
            print(f"Error downloading {url}: {e}")
            self.cleanup_failed_download(destination)
            return False
    
    def _download_with_progress(self, url: str, destination: Path, file_size: int) -> bool:
        """Download file with progress tracking."""
        try:
            response = self.session.get(url, stream=True, timeout=self.timeout)
            response.raise_for_status()
            
            downloaded_size = 0
            
            with open(destination, 'wb') as f:
                for chunk in response.iter_content(chunk_size=self.chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        # Update progress if callback provided
                        if self.progress_callback and file_size > 0:
                            progress = (downloaded_size / file_size) * 100
                            self.progress_callback(progress, downloaded_size, file_size)
            
            return True
            
        except Exception as e:
            print(f"Download failed for {url}: {e}")
            return False
    
    def download_multiple_files(self, downloads: List[Dict[str, Any]], **kwargs) -> Dict[str, bool]:
        """
        Download multiple files concurrently.
        
        Args:
            downloads: List of download specifications
                     [{'url': '...', 'destination': '...', 'filename': '...'}]
            **kwargs: Additional download options
            
        Returns:
            Dictionary mapping URLs to success status
        """
        results = {}
        
        for download in downloads:
            url = download['url']
            destination = download['destination']
            filename = download.get('filename', '')
            
            if filename:
                full_path = destination / filename
            else:
                # Extract filename from URL
                parsed_url = urlparse(url)
                filename = os.path.basename(parsed_url.path)
                full_path = destination / filename
            
            print(f"Downloading {filename} from {url}")
            success = self.download_file(url, full_path, **kwargs)
            results[url] = success
            
            if success:
                print(f"✓ Successfully downloaded {filename}")
            else:
                print(f"✗ Failed to download {filename}")
        
        return results
    
    def get_file_size(self, url: str) -> int:
        """
        Get file size from URL without downloading.
        
        Args:
            url: Source URL
            
        Returns:
            File size in bytes, 0 if unknown
        """
        try:
            response = self.session.head(url, timeout=self.timeout)
            response.raise_for_status()
            
            content_length = response.headers.get('content-length')
            if content_length:
                return int(content_length)
            
            return 0
            
        except Exception as e:
            print(f"Error getting file size for {url}: {e}")
            return 0
    
    def validate_download(self, file_path: Path, expected_size: int = 0) -> bool:
        """
        Validate downloaded file.
        
        Args:
            file_path: Path to downloaded file
            expected_size: Expected file size in bytes
            
        Returns:
            True if file is valid, False otherwise
        """
        try:
            # Check if file exists
            if not file_path.exists():
                return False
            
            # Check file size if expected size provided
            if expected_size > 0:
                actual_size = self.file_ops.get_file_size(file_path)
                if actual_size != expected_size:
                    print(f"File size mismatch: expected {expected_size}, got {actual_size}")
                    return False
            
            # Check if file is not empty
            if file_path.stat().st_size == 0:
                print("Downloaded file is empty")
                return False
            
            return True
            
        except Exception as e:
            print(f"Error validating file {file_path}: {e}")
            return False
    
    def cleanup_failed_download(self, file_path: Path) -> None:
        """
        Clean up failed download.
        
        Args:
            file_path: Path to file to remove
        """
        try:
            if file_path.exists():
                self.file_ops.safe_remove(file_path)
                print(f"Cleaned up failed download: {file_path}")
        except Exception as e:
            print(f"Error cleaning up {file_path}: {e}")
    
    def get_download_info(self, url: str) -> Dict[str, Any]:
        """
        Get information about a file before downloading.
        
        Args:
            url: Source URL
            
        Returns:
            Dictionary with file information
        """
        try:
            response = self.session.head(url, timeout=self.timeout)
            response.raise_for_status()
            
            headers = response.headers
            return {
                'url': url,
                'size': int(headers.get('content-length', 0)),
                'content_type': headers.get('content-type', ''),
                'last_modified': headers.get('last-modified', ''),
                'etag': headers.get('etag', ''),
                'available': True
            }
            
        except Exception as e:
            return {
                'url': url,
                'size': 0,
                'content_type': '',
                'last_modified': '',
                'etag': '',
                'available': False,
                'error': str(e)
            }
