"""
Main entry point for the weather data downloader package.

This module allows the package to be run directly with python -m src.
"""

from .cli import cli

if __name__ == "__main__":
    cli()
