"""
Compression utilities for the weather data downloader system.

This module provides utilities for NetCDF compression and optimization
to reduce storage requirements and improve performance.
"""

from typing import Dict, Any, Optional
import xarray as xr
from pathlib import Path


class CompressionManager:
    """Utilities for NetCDF compression and optimization."""
    
    @staticmethod
    def get_compression_encoding(
        compression_level: int = 6,
        chunking: str = "auto"
    ) -> Dict[str, Any]:
        """
        Get compression encoding configuration for NetCDF files.
        
        Args:
            compression_level: Compression level (0-9, where 9 is maximum)
            chunking: Chunking strategy ('auto', 'time', 'space', 'balanced')
            
        Returns:
            Dictionary with compression encoding configuration
        """
        if not 0 <= compression_level <= 9:
            raise ValueError("Compression level must be between 0 and 9")
        
        # Base encoding with zlib compression
        encoding = {
            'zlib': True,
            'complevel': compression_level,
            'shuffle': True,  # Better compression for floating point data
        }
        
        # Add chunking strategy
        if chunking == "auto":
            encoding['chunksizes'] = 'auto'
        elif chunking == "time":
            encoding['chunksizes'] = (1, -1, -1)  # Time dimension chunked
        elif chunking == "space":
            encoding['chunksizes'] = (-1, 100, 100)  # Spatial dimensions chunked
        elif chunking == "balanced":
            encoding['chunksizes'] = (10, 200, 200)  # Balanced approach
        
        return encoding
    
    @staticmethod
    def optimize_dataset_for_storage(
        dataset: xr.Dataset,
        compression_level: int = 6,
        chunking: str = "auto"
    ) -> xr.Dataset:
        """
        Optimize a dataset for storage and memory usage.
        
        Args:
            dataset: Input dataset
            compression_level: Compression level (0-9)
            chunking: Chunking strategy
            
        Returns:
            Optimized dataset
        """
        # Get compression encoding
        encoding = CompressionManager.get_compression_encoding(
            compression_level, chunking
        )
        
        # Apply encoding to all variables
        for var_name in dataset.data_vars:
            var = dataset[var_name]
            
            # Skip variables that are already encoded
            if 'encoding' in var.attrs:
                continue
            
            # Apply compression encoding
            var.encoding.update(encoding)
        
        return dataset
    
    @staticmethod
    def estimate_compression_ratio(
        original_size: int,
        compressed_size: int
    ) -> float:
        """
        Calculate compression ratio.
        
        Args:
            original_size: Original file size in bytes
            compressed_size: Compressed file size in bytes
            
        Returns:
            Compression ratio (original_size / compressed_size)
        """
        if compressed_size == 0:
            return 0.0
        
        return original_size / compressed_size
    
    @staticmethod
    def get_optimal_chunk_size(
        dataset: xr.Dataset,
        target_chunk_size_mb: float = 10.0
    ) -> Dict[str, int]:
        """
        Calculate optimal chunk sizes for a dataset.
        
        Args:
            dataset: Input dataset
            target_chunk_size_mb: Target chunk size in MB
            
        Returns:
            Dictionary mapping dimension names to chunk sizes
        """
        target_chunk_size_bytes = target_chunk_size_mb * 1024 * 1024
        
        # Get dataset dimensions
        dims = dataset.dims
        
        # Calculate total elements
        total_elements = 1
        for dim_size in dims.values():
            total_elements *= dim_size
        
        # Calculate elements per chunk
        elements_per_chunk = target_chunk_size_bytes / 8  # Assuming 8 bytes per element
        
        # Distribute chunks across dimensions
        chunk_sizes = {}
        remaining_elements = elements_per_chunk
        
        for dim_name, dim_size in dims.items():
            if remaining_elements <= 1:
                chunk_sizes[dim_name] = 1
            else:
                # Calculate chunk size for this dimension
                chunk_size = max(1, int(remaining_elements ** (1 / (len(dims) - len(chunk_sizes)))))
                chunk_size = min(chunk_size, dim_size)
                chunk_sizes[dim_name] = chunk_size
                remaining_elements /= chunk_size
        
        return chunk_sizes
    
    @staticmethod
    def apply_compression_to_file(
        input_path: Path,
        output_path: Path,
        compression_level: int = 6,
        chunking: str = "auto"
    ) -> bool:
        """
        Apply compression to a NetCDF file.
        
        Args:
            input_path: Path to input NetCDF file
            output_path: Path for compressed output file
            compression_level: Compression level (0-9)
            chunking: Chunking strategy
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Load dataset
            dataset = xr.open_dataset(input_path)
            
            # Optimize for storage
            optimized_dataset = CompressionManager.optimize_dataset_for_storage(
                dataset, compression_level, chunking
            )
            
            # Save with compression
            optimized_dataset.to_netcdf(
                output_path,
                engine='netcdf4',
                encoding=optimized_dataset.encoding
            )
            
            # Close dataset
            dataset.close()
            optimized_dataset.close()
            
            return True
            
        except Exception as e:
            print(f"Error applying compression: {e}")
            return False
    
    @staticmethod
    def get_compression_stats(
        original_path: Path,
        compressed_path: Path
    ) -> Dict[str, Any]:
        """
        Get compression statistics for a file.
        
        Args:
            original_path: Path to original file
            compressed_path: Path to compressed file
            
        Returns:
            Dictionary with compression statistics
        """
        try:
            original_size = original_path.stat().st_size
            compressed_size = compressed_path.stat().st_size
            
            compression_ratio = CompressionManager.estimate_compression_ratio(
                original_size, compressed_size
            )
            
            space_saved = original_size - compressed_size
            space_saved_mb = space_saved / (1024 * 1024)
            
            return {
                'original_size_bytes': original_size,
                'compressed_size_bytes': compressed_size,
                'compression_ratio': compression_ratio,
                'space_saved_bytes': space_saved,
                'space_saved_mb': space_saved_mb,
                'compression_percentage': (1 - 1/compression_ratio) * 100
            }
            
        except Exception as e:
            print(f"Error getting compression stats: {e}")
            return {}
