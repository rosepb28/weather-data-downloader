"""
Data downloader implementations.

This module provides concrete implementations of the DataDownloader interface
for different download protocols (HTTP, FTP, etc.).
"""

from .http_data_downloader import HTTPDataDownloader

__all__ = ['HTTPDataDownloader']
