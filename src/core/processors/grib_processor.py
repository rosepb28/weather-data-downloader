"""
GRIB data processor implementation.

This module provides processing capabilities for GRIB2 files including:
- Loading GRIB2 files using cfgrib/xarray
- Temporal interpolation 
- Variable standardization
- NetCDF conversion with optimization
"""

import xarray as xr
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from loguru import logger

from ..interfaces.data_processor import DataProcessor


class GRIBProcessor(DataProcessor):
    """
    GRIB2 data processor using xarray and cfgrib.
    
    This processor handles GRIB2 files and provides:
    - Loading multiple GRIB2 files as a unified dataset
    - Temporal interpolation (e.g., 3h → 1h)
    - Variable name standardization
    - NetCDF output with compression and optimization
    """
    
    def __init__(self, variable_mapper=None, user_config=None):
        """
        Initialize GRIB processor.
        
        Args:
            variable_mapper: Variable mapper for standardizing names
            user_config: User configuration with spatial bounds, variables, etc.
        """
        self.variable_mapper = variable_mapper
        self.user_config = user_config or {}
    
    def process(
        self, 
        input_files: List[Path], 
        output_path: Path,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Process GRIB2 files to NetCDF.
        
        Args:
            input_files: List of GRIB2 file paths
            output_path: Output NetCDF file path
            **kwargs: Additional processing options
            
        Returns:
            Dictionary with processing metadata
        """
        try:
            logger.info(f"🔄 Processing {len(input_files)} GRIB2 files")
            
            # Load GRIB2 files
            dataset = self._load_grib_files(input_files)
            
            # Validate data
            validated_dataset = self.validate_data(dataset)
            
            # Apply spatial subsetting if configured
            subset_dataset = self.apply_spatial_subsetting(validated_dataset)
            
            # Prepare for variable calculations (placeholder)
            processed_dataset = self.prepare_for_variable_calculation(subset_dataset)
            
            outputs = {}
            
            # Always generate processed output (original frequencies)
            processed_output_path = self._get_processed_output_path(output_path)
            optimized_original = self.optimize_storage(processed_dataset.copy())
            self._save_netcdf(optimized_original, processed_output_path)
            outputs['processed'] = processed_output_path
            logger.success(f"✅ Saved original data: {processed_output_path}")
            
            # Always generate interpolated output (hourly)
            interpolated_dataset = self.interpolate_temporal(processed_dataset.copy())
            interpolated_output_path = self._get_interpolated_output_path(output_path)
            optimized_interpolated = self.optimize_storage(interpolated_dataset)
            self._save_netcdf(optimized_interpolated, interpolated_output_path)
            outputs['interpolated'] = interpolated_output_path
            logger.success(f"✅ Saved interpolated data: {interpolated_output_path}")
            
            # Generate metadata
            main_output = outputs.get('processed') or outputs.get('interpolated')
            metadata = self.get_processing_metadata(processed_dataset, input_files, main_output)
            metadata['outputs'] = outputs
            
            logger.success(f"✅ Processing completed - Generated {len(outputs)} outputs")
            return metadata
            
        except Exception as e:
            logger.error(f"❌ Processing failed: {e}")
            raise
    
    def _load_grib_files(self, input_files: List[Path]) -> xr.Dataset:
        """
        Load GRIB2 files using cfgrib engine.
        
        Args:
            input_files: List of GRIB2 file paths
            
        Returns:
            Unified xarray Dataset
        """
        logger.debug(f"📂 Loading {len(input_files)} GRIB2 files")
        
        # Convert to strings for xarray
        file_paths = [str(f) for f in input_files]
        
        try:
            # First try the simple approach
            try:
                dataset = xr.open_mfdataset(
                    file_paths,
                    engine='cfgrib',
                    combine='by_coords',
                    parallel=True,
                    chunks={'valid_time': 1}  # Chunk by valid_time for memory efficiency
                )
                
                # Rename valid_time to time for consistency, but drop existing time first if it exists
                if 'time' in dataset.coords and 'valid_time' in dataset.dims:
                    # Drop the original time coordinate (constant initialization time)
                    dataset = dataset.drop_vars('time')
                    # Rename valid_time to time
                    dataset = dataset.rename({'valid_time': 'time'})
                elif 'valid_time' in dataset.dims:
                    dataset = dataset.rename({'valid_time': 'time'})
                
                # Standardize coordinate names to ensure consistent dimensions
                dataset = self._standardize_coordinate_names(dataset)
                
                logger.debug(f"📊 Loaded dataset with dimensions: {dict(dataset.dims)}")
                logger.debug(f"📊 Variables: {list(dataset.data_vars)}")
                return dataset
                
            except Exception as e:
                logger.warning(f"⚠️ Standard loading failed: {e}")
                logger.info("🔄 Trying alternative loading approach...")
                
                # Alternative approach: Load files individually with multiple level filters
                datasets = []
                for file_path in input_files:
                    file_datasets = []
                    
                    # Define level filters to load all relevant data
                    level_filters = [
                        {'typeOfLevel': 'surface'},
                        {'typeOfLevel': 'heightAboveGround', 'level': 2},  # 2m variables
                        {'typeOfLevel': 'heightAboveGround', 'level': 10}, # 10m variables
                    ]
                    
                    for level_filter in level_filters:
                        try:
                            ds_level = xr.open_dataset(
                                str(file_path),
                                engine='cfgrib',
                                backend_kwargs={
                                    'filter_by_keys': level_filter,
                                    'errors': 'ignore'
                                }
                            )
                            if len(ds_level.data_vars) > 0:  # Only add if it has variables
                                file_datasets.append(ds_level)
                                logger.debug(f"   ✅ Loaded {file_path.name} ({level_filter})")
                        except Exception as e:
                            logger.debug(f"   ⚠️ Could not load {file_path.name} with filter {level_filter}: {e}")
                            continue
                    
                    # Merge all levels for this file
                    if file_datasets:
                        try:
                            # Merge datasets with different levels (override conflicts)
                            merged_ds = xr.merge(file_datasets, compat='override')
                            datasets.append(merged_ds)
                            logger.debug(f"   🔗 Merged {len(file_datasets)} level datasets for {file_path.name}")
                        except Exception as e:
                            logger.warning(f"   ⚠️ Could not merge levels for {file_path.name}: {e}")
                            # Add them individually as fallback
                            datasets.extend(file_datasets)
                    else:
                        logger.warning(f"   ❌ No data loaded for {file_path.name}")
                
                if not datasets:
                    raise Exception("No GRIB2 files could be loaded successfully")
                
                # Combine datasets along valid_time dimension
                logger.debug(f"📊 Combining {len(datasets)} datasets")
                dataset = xr.concat(datasets, dim='valid_time', coords='minimal', compat='override')
                
                # Sort by valid_time to ensure correct order
                dataset = dataset.sortby('valid_time')
                
                # Rename valid_time to time for consistency, but drop existing time first if it exists
                if 'time' in dataset.coords and 'valid_time' in dataset.dims:
                    # Drop the original time coordinate (constant initialization time)
                    dataset = dataset.drop_vars('time')
                    # Rename valid_time to time
                    dataset = dataset.rename({'valid_time': 'time'})
                elif 'valid_time' in dataset.dims:
                    dataset = dataset.rename({'valid_time': 'time'})
                
                # Standardize coordinate names to ensure consistent dimensions
                dataset = self._standardize_coordinate_names(dataset)
                
                logger.debug(f"📊 Combined dataset with dimensions: {dict(dataset.dims)}")
                logger.debug(f"📊 Variables: {list(dataset.data_vars)}")
                
                # Filter variables to only keep those specified in user config
                dataset = self._filter_config_variables(dataset)
                logger.debug(f"📊 Variables after filtering: {list(dataset.data_vars)}")
                
                # Standardize variable names according to config
                dataset = self._standardize_variable_names(dataset)
                logger.debug(f"📊 Variables after standardization: {list(dataset.data_vars)}")
                
                return dataset
            
        except Exception as e:
            logger.error(f"❌ Failed to load GRIB2 files: {e}")
            raise
    
    def validate_data(self, dataset: xr.Dataset) -> xr.Dataset:
        """
        Validate the loaded dataset.
        
        Args:
            dataset: Input dataset
            
        Returns:
            Validated dataset
        """
        logger.debug("🔍 Validating dataset")
        
        # Check for required dimensions
        required_dims = ['time', 'latitude', 'longitude']
        missing_dims = [dim for dim in required_dims if dim not in dataset.dims]
        
        if missing_dims:
            raise ValueError(f"Missing required dimensions: {missing_dims}")
        
        # Check for data consistency
        if dataset.sizes['time'] == 0:
            raise ValueError("No time steps found in dataset")
        
        # Check for NaN values
        for var_name, var_data in dataset.data_vars.items():
            nan_count = var_data.isnull().sum().compute()
            if nan_count > 0:
                logger.warning(f"⚠️  Variable {var_name} has {nan_count} NaN values")
        
        logger.debug("✅ Dataset validation completed")
        return dataset
    
    def interpolate_temporal(self, dataset: xr.Dataset) -> xr.Dataset:
        """
        Interpolate temporal gaps to create hourly data.
        
        Args:
            dataset: Input dataset
            
        Returns:
            Temporally interpolated dataset
        """
        logger.debug("⏱️  Performing temporal interpolation")
        
        # Get time coordinate
        time_coord = dataset.time
        
        # Check if interpolation is needed
        time_diff = np.diff(time_coord.values.astype('datetime64[h]')).astype(int)
        max_gap = np.max(time_diff) if len(time_diff) > 0 else 1
        
        if max_gap <= 1:
            logger.info("✅ No temporal interpolation needed - data is already at hourly frequency")
            return dataset
        
        logger.debug(f"🔄 Interpolating temporal gaps (max gap: {max_gap}h)")
        
        # Create hourly time grid
        start_time = time_coord.min().values
        end_time = time_coord.max().values
        
        # Generate hourly time steps
        hourly_times = np.arange(
            start_time.astype('datetime64[h]'),
            end_time.astype('datetime64[h]') + np.timedelta64(1, 'h'),
            np.timedelta64(1, 'h')
        )
        
        # Interpolate to hourly grid
        interpolated_dataset = dataset.interp(
            time=hourly_times,
            method='linear',
            kwargs={'fill_value': 'extrapolate'}
        )
        
        logger.debug(f"✅ Interpolated from {len(time_coord)} to {len(hourly_times)} time steps")
        return interpolated_dataset
    
    def _filter_config_variables(self, dataset: xr.Dataset) -> xr.Dataset:
        """
        Filter dataset to only include variables specified in user config.
        
        Args:
            dataset: Input dataset
            
        Returns:
            Dataset with only configured variables
        """
        if 'variables' not in self.user_config:
            logger.debug("🔍 No variable filter configured, keeping all variables")
            return dataset
        
        configured_vars = self.user_config['variables']
        logger.debug(f"🔍 Filtering for configured variables: {configured_vars}")
        
        # Create mapping from GRIB variable names to standard names
        if not self.variable_mapper:
            logger.warning("⚠️ No variable mapper available, keeping all variables")
            return dataset
        
        # Find which dataset variables correspond to configured standard variables
        vars_to_keep = []
        for data_var in dataset.data_vars:
            for std_var in configured_vars:
                try:
                    # Get the GFS code for this standard variable
                    gfs_code = self.variable_mapper.get_model_variable_code(std_var, 'gfs')
                    
                    # Check if this data variable matches (by name similarity)
                    # This is a simple mapping - could be improved
                    var_mappings = {
                        'TMP': ['t', 't2m'],  # Temperature maps to both t and t2m
                        'RH': ['r2'],         # Relative humidity
                        'UGRD': ['u10'],      # U wind component
                        'VGRD': ['v10'],      # V wind component  
                        'HGT': ['orog']       # Height/orography maps to orog only
                    }
                    
                    if gfs_code in var_mappings:
                        if data_var in var_mappings[gfs_code]:
                            # For temperature, prefer t2m over t
                            if std_var == 't2m' and data_var == 't2m':
                                vars_to_keep.append(data_var)
                            elif std_var == 't2m' and data_var == 't':
                                continue  # Skip surface temperature if we want 2m temp
                            elif gfs_code == 'TMP' and data_var == 't' and 't2m' not in dataset.data_vars:
                                vars_to_keep.append(data_var)  # Use t if t2m not available
                            elif gfs_code != 'TMP':
                                vars_to_keep.append(data_var)
                            
                except ValueError:
                    continue
        
        # Remove duplicates
        vars_to_keep = list(set(vars_to_keep))
        
        if not vars_to_keep:
            logger.warning("⚠️ No variables matched configuration, keeping all")
            return dataset
        
        # Filter dataset to only include configured variables
        logger.info(f"✅ Keeping {len(vars_to_keep)} configured variables: {vars_to_keep}")
        filtered_vars = {var: dataset[var] for var in vars_to_keep if var in dataset.data_vars}
        
        # Create new dataset with filtered variables but keep all coordinates
        filtered_dataset = xr.Dataset(
            data_vars=filtered_vars,
            coords=dataset.coords,
            attrs=dataset.attrs
        )
        
        return filtered_dataset

    def _standardize_variable_names(self, dataset: xr.Dataset) -> xr.Dataset:
        """
        Standardize variable names according to the mapping configuration.
        
        Args:
            dataset: Input dataset
            
        Returns:
            Dataset with standardized variable names
        """
        if not self.variable_mapper or 'variables' not in self.user_config:
            logger.debug("🔍 No variable mapper or config available, keeping original names")
            return dataset
        
        # Create mapping from GRIB names to standard names
        name_mapping = {}
        grib_to_standard = {
            't2m': 't2m',    # 2m temperature -> keep as t2m
            'r2': 'rh2m',    # 2m relative humidity -> rh2m  
            'u10': 'u10m',   # 10m U wind -> u10m
            'v10': 'v10m',   # 10m V wind -> v10m
            'orog': 'hgt',   # Orography -> hgt (height)
            't': 't',        # Keep surface temperature as t
        }
        
        # Build mapping for variables that exist in dataset
        for grib_name, std_name in grib_to_standard.items():
            if grib_name in dataset.data_vars and std_name in self.user_config['variables']:
                name_mapping[grib_name] = std_name
        
        if not name_mapping:
            logger.debug("🔍 No variable names to standardize")
            return dataset
        
        logger.info(f"🔄 Standardizing variable names: {name_mapping}")
        
        # Rename variables
        renamed_dataset = dataset.rename(name_mapping)
        
        return renamed_dataset

    def apply_spatial_subsetting(self, dataset: xr.Dataset) -> xr.Dataset:
        """
        Apply spatial subsetting based on user configuration.
        
        Args:
            dataset: Input dataset
            
        Returns:
            Spatially subset dataset
        """
        if 'spatial_bounds' not in self.user_config:
            logger.debug("🌍 No spatial bounds configured, keeping global data")
            return dataset
        
        bounds = self.user_config['spatial_bounds']
        logger.debug(f"🗺️  Applying spatial subsetting: "
                    f"lon [{bounds['lon_min']} to {bounds['lon_max']}], "
                    f"lat [{bounds['lat_min']} to {bounds['lat_max']}]")
        
        try:
            # Handle longitude wrapping if necessary
            lon_min = bounds['lon_min']
            lon_max = bounds['lon_max']
            lat_min = bounds['lat_min']
            lat_max = bounds['lat_max']
            
            # Convert negative longitudes to 0-360 range if needed
            if lon_min < 0:
                lon_min = lon_min + 360
            if lon_max < 0:
                lon_max = lon_max + 360
            
            # Apply subsetting
            subset_ds = dataset.sel(
                longitude=slice(lon_min, lon_max),
                latitude=slice(lat_max, lat_min)  # Note: latitude is usually descending
            )
            
            logger.debug(f"✅ Spatial subsetting completed. "
                        f"New dimensions: {dict(subset_ds.dims)}")
            
            return subset_ds
            
        except Exception as e:
            logger.warning(f"⚠️ Spatial subsetting failed: {e}, keeping original data")
            return dataset

    def prepare_for_variable_calculation(self, dataset: xr.Dataset) -> xr.Dataset:
        """
        Prepare dataset for variable calculations (placeholder).
        
        Args:
            dataset: Input dataset
            
        Returns:
            Prepared dataset
        """
        logger.debug("🧮 Preparing for variable calculations")
        
        # TODO: Implement variable calculations
        # For now, just return the dataset as-is
        
        return dataset
    
    def optimize_storage(self, dataset: xr.Dataset) -> xr.Dataset:
        """
        Optimize dataset for storage.
        
        Args:
            dataset: Input dataset
            
        Returns:
            Optimized dataset with compression settings
        """
        logger.debug("🗜️  Optimizing dataset for storage")
        
        # Apply compression encoding to all variables
        encoding = {}
        for var_name in dataset.data_vars:
            encoding[var_name] = {
                'zlib': True,
                'complevel': 6,
                'shuffle': True,
                'fletcher32': True,
                'chunksizes': self._get_optimal_chunks(dataset[var_name])
            }
        
        # Apply encoding
        for var_name, var_encoding in encoding.items():
            dataset[var_name].encoding.update(var_encoding)
        
        logger.debug(f"✅ Applied compression to {len(encoding)} variables")
        return dataset
    
    def _get_optimal_chunks(self, data_array: xr.DataArray) -> tuple:
        """
        Calculate optimal chunk sizes for NetCDF storage.
        
        Args:
            data_array: Input data array
            
        Returns:
            Optimal chunk sizes tuple
        """
        # Simple chunking strategy: chunk time dimension, keep spatial intact
        chunks = []
        for dim in data_array.dims:
            if dim == 'time':
                chunks.append(min(24, data_array.sizes[dim]))  # 24 hours max
            elif dim in ['latitude', 'longitude']:
                chunks.append(data_array.sizes[dim])  # Keep spatial intact
            else:
                chunks.append(1)  # Other dimensions
        
        return tuple(chunks)
    
    def _get_processed_output_path(self, original_output_path: Path) -> Path:
        """
        Generate output path for processed (original frequency) data.
        
        Args:
            original_output_path: Original output path
            
        Returns:
            Path for processed data
        """
        # Replace 'processed' in path with 'processed' (keeps same if already correct)
        # Change: data/gfs/20250828/00/processed/file.nc -> data/gfs/20250828/00/processed/file.nc
        return original_output_path
    
    def _get_interpolated_output_path(self, original_output_path: Path) -> Path:
        """
        Generate output path for interpolated (hourly) data.
        
        Args:
            original_output_path: Original output path
            
        Returns:
            Path for interpolated data
        """
        # Replace 'processed' with 'interpolated' in path
        # Change: data/gfs/20250828/00/processed/file.nc -> data/gfs/20250828/00/interpolated/file.nc
        parts = list(original_output_path.parts)
        if 'processed' in parts:
            processed_idx = parts.index('processed')
            parts[processed_idx] = 'interpolated'
        
        return Path(*parts)

    def _standardize_coordinate_names(self, dataset: xr.Dataset) -> xr.Dataset:
        """
        Standardize coordinate names to ensure consistency across all models.
        
        Always use: time, latitude, longitude (in that order)
        
        Args:
            dataset: Input dataset with potentially non-standard coordinate names
            
        Returns:
            Dataset with standardized coordinate names
        """
        rename_dict = {}
        
        # Standardize latitude coordinate
        for coord in ['lat', 'lats', 'y']:
            if coord in dataset.coords:
                rename_dict[coord] = 'latitude'
                break
        
        # Standardize longitude coordinate  
        for coord in ['lon', 'lons', 'long', 'x']:
            if coord in dataset.coords:
                rename_dict[coord] = 'longitude'
                break
        
        if rename_dict:
            logger.debug(f"🔄 Standardizing coordinate names: {rename_dict}")
            dataset = dataset.rename(rename_dict)
        
        # Ensure standard dimension order: time, latitude, longitude
        desired_order = ['time', 'latitude', 'longitude']
        available_dims = [dim for dim in desired_order if dim in dataset.dims]
        
        # Transpose all data variables to have consistent dimension order
        if len(available_dims) > 1:
            data_vars = {}
            for var_name, var in dataset.data_vars.items():
                var_dims = [dim for dim in available_dims if dim in var.dims]
                if var_dims and var_dims != list(var.dims[:len(var_dims)]):
                    # Only transpose if order is different
                    other_dims = [dim for dim in var.dims if dim not in var_dims]
                    new_dims = var_dims + other_dims
                    data_vars[var_name] = var.transpose(*new_dims)
                else:
                    data_vars[var_name] = var
            
            if data_vars:
                logger.debug(f"🔄 Reordering dimensions to: {available_dims}")
                dataset = xr.Dataset(data_vars, coords=dataset.coords, attrs=dataset.attrs)
        
        return dataset

    def _save_netcdf(self, dataset: xr.Dataset, output_path: Path) -> None:
        """
        Save dataset to NetCDF file.
        
        Args:
            dataset: Dataset to save
            output_path: Output file path
        """
        logger.debug(f"💾 Saving to NetCDF: {output_path}")
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save with optimal settings
        dataset.to_netcdf(
            output_path,
            format='NETCDF4',
            unlimited_dims=['time'],
            compute=True
        )
        
        # Get file size
        file_size = output_path.stat().st_size / (1024 * 1024)  # MB
        logger.debug(f"✅ Saved NetCDF file: {file_size:.1f} MB")
    
    def get_processing_metadata(
        self, 
        dataset: xr.Dataset, 
        input_files: List[Path], 
        output_path: Path
    ) -> Dict[str, Any]:
        """
        Generate processing metadata.
        
        Args:
            dataset: Processed dataset
            input_files: Input file paths
            output_path: Output file path
            
        Returns:
            Processing metadata dictionary
        """
        # Calculate file sizes
        input_size = sum(f.stat().st_size for f in input_files) / (1024 * 1024)  # MB
        output_size = output_path.stat().st_size / (1024 * 1024)  # MB
        
        metadata = {
            'input_files': len(input_files),
            'input_size_mb': round(input_size, 1),
            'output_size_mb': round(output_size, 1),
            'compression_ratio': round(input_size / output_size, 2) if output_size > 0 else 0,
            'time_steps': len(dataset.time),
            'variables': list(dataset.data_vars),
            'time_range': {
                'start': str(dataset.time.min().values),
                'end': str(dataset.time.max().values)
            },
            'spatial_extent': {
                'lat_min': float(dataset.latitude.min().values),
                'lat_max': float(dataset.latitude.max().values),
                'lon_min': float(dataset.longitude.min().values),
                'lon_max': float(dataset.longitude.max().values)
            }
        }
        
        return metadata
