"""
Main CLI application for the weather data downloader.

This module provides the main CLI commands using Click framework.
"""

import click
import sys
import yaml
import shutil
from pathlib import Path
from typing import Optional, List
from datetime import datetime, timezone
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..core.providers import GFSProvider
from ..core.mapping import YAMLVariableMapper
from ..utils.time_management import TimeRangeManager, CycleManager, ForecastManager
from ..utils.validation import DataValidator
from loguru import logger

# ============================================================================
# CONFIGURATION CONSTANTS
# ============================================================================

# Output filename pattern - modify this to change how files are named
# Pattern: {out_file}.{date}.{cycle}z.{extension}
# Example: gfs.0p25.20250828.00z.nc
OUTPUT_FILENAME_PATTERN = "{out_file}.{date}.{cycle}z.{extension}"

# Date and cycle suffix pattern - used throughout the system  
DATE_CYCLE_SUFFIX = "{date}.{cycle}z"

# Model command name to full model name mapping
MODEL_NAME_MAPPING = {
    'gfs': 'gfs.0p25',
    'ecmwf': 'ecmwf.0p25', 
    'gem': 'gem.0p1'
}

# Configure loguru for better output
logger.remove()  # Remove default handler
logger.add(
    sys.stderr,  # Use stderr for better colors
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="DEBUG",  # Default level
    colorize=True
)

def get_full_model_name(model_command: str) -> str:
    """
    Convert CLI model command to full model name.
    
    Args:
        model_command: CLI model name (e.g., 'gfs')
        
    Returns:
        Full model name (e.g., 'gfs.0p25')
    """
    return MODEL_NAME_MAPPING.get(model_command.lower(), model_command)

def calculate_forecast_hours_from_days(days: float, model_config: dict) -> List[int]:
    """
    Calculate forecast hours for a given number of days based on model configuration.
    
    Args:
        days: Number of days to generate forecast hours for (supports decimals, e.g., 0.5 for 12h)
        model_config: Model configuration with cycle_forecast_ranges
        
    Returns:
        List of forecast hours for the specified number of days
    """
    max_hours = int(days * 24)
    
    # Get all available forecast hours from model config
    all_forecast_hours = []
    cycle_forecast_ranges = model_config.get('cycle_forecast_ranges', {})
    
    # Use the first cycle's ranges as reference (usually all cycles have same ranges)
    first_cycle = list(cycle_forecast_ranges.keys())[0] if cycle_forecast_ranges else '00'
    ranges = cycle_forecast_ranges.get(first_cycle, [])
    
    for range_def in ranges:
        start, end, frequency = range_def
        for hour in range(start, min(end + 1, max_hours + 1), frequency):
            if hour <= max_hours:
                all_forecast_hours.append(hour)
    
    # Remove duplicates and sort
    forecast_hours = sorted(list(set(all_forecast_hours)))
    
    logger.info(f"📅 Generated {len(forecast_hours)} forecast hours for {days} day(s): {forecast_hours[0]}-{forecast_hours[-1]}h")
    return forecast_hours

def cleanup_existing_files(model: str, date: str, cycle: str, forecast_hours: List[int], variable_mapper) -> None:
    """
    Clean up existing files before downloading to avoid duplicates.
    
    Args:
        model: Weather model name
        date: Date in YYYYMMDD format
        cycle: Forecast cycle
        forecast_hours: List of forecast hours to clean
        variable_mapper: Variable mapper instance
    """
    try:
        # Get model configuration for file extension
        model_config = variable_mapper.get_model_config(model)
        file_extension = model_config.get('file_extension', '.grb2')
        
        # Load user config to get output directory
        with open("config.yaml", "r") as f:
            user_config = yaml.safe_load(f)
        output_dir = user_config.get('output_dir', 'data')
        
        # Convert command model name to full model name and build directory path
        full_model_name = get_full_model_name(model)
        base_dir = Path(output_dir) / full_model_name / date / cycle / "raw"
        
        # Clean raw files
        raw_cleaned = []
        if base_dir.exists():
            # Find and remove existing raw files for the specified forecast hours
            for forecast_hour in forecast_hours:
                # Pattern for existing files (with and without extensions)
                patterns = [
                    f"gfs.t{cycle}z.pgrb2.0p25.f{forecast_hour:03d}.{date}.nc",
                    f"gfs.t{cycle}z.pgrb2.0p25.f{forecast_hour:03d}.{date}.grb2",
                    f"gfs.t{cycle}z.pgrb2.0p25.f{forecast_hour:03d}.{date}.grib2",
                    f"gfs.t{cycle}z.pgrb2.0p25.f{forecast_hour:03d}.{date}",  # Old format with date
                    f"gfs.t{cycle}z.pgrb2.0p25.f{forecast_hour:03d}"  # New format without date
                ]
                
                for pattern in patterns:
                    for existing_file in base_dir.glob(pattern):
                        if existing_file.exists():
                            existing_file.unlink()
                            raw_cleaned.append(existing_file.name)
        
        # Clean processed files (both original and interpolated)
        processed_cleaned = []
        processed_base = Path(output_dir) / full_model_name / date / cycle
        for subdir in ["processed", "interpolated"]:
            processed_dir = processed_base / subdir
            if processed_dir.exists():
                # Remove existing NetCDF files (they will be regenerated)
                # Use model config to get the output filename prefix
                model_user_config = user_config.get('models', {}).get(model.lower(), {})
                out_file = model_user_config.get('out_file', model.lower())
                
                # Generate expected filename using the pattern
                expected_filename = OUTPUT_FILENAME_PATTERN.format(
                    out_file=out_file,
                    date=date,
                    cycle=cycle,
                    extension="nc"
                )
                
                patterns = [
                    expected_filename,
                    f"gfs.{date}.{cycle}z.nc",  # Legacy pattern
                    f"{model.lower()}.{date}.{cycle}z.nc"  # Legacy pattern
                ]
                
                for pattern in patterns:
                    for existing_file in processed_dir.glob(pattern):
                        if existing_file.exists():
                            existing_file.unlink()
                            processed_cleaned.append(f"{subdir}/{existing_file.name}")
        
        # Log cleanup results
        total_cleaned = len(raw_cleaned) + len(processed_cleaned)
        if total_cleaned > 0:
            logger.info(f"🧹 Cleaned up {total_cleaned} existing files")
            if raw_cleaned:
                logger.debug(f"    Raw files: {len(raw_cleaned)}")
                for file in raw_cleaned:
                    logger.debug(f"      • {file}")
            if processed_cleaned:
                logger.debug(f"    Processed files: {len(processed_cleaned)}")
                for file in processed_cleaned:
                    logger.debug(f"      • {file}")
        else:
            logger.debug("✅ No existing files to clean")
            logger.debug(f"📁 Creating new directory: {base_dir}")
            
    except Exception as e:
        logger.error(f"❌ Error during cleanup: {e}")


console = Console()


def process_downloaded_files(
    model: str, 
    dates_list: List[str], 
    cycles_list: List[str], 
    forecast_hours: List[int],
    variable_mapper,
    user_config: dict = None
) -> bool:
    """
    Process downloaded GRIB2 files to NetCDF.
    
    Args:
        model: Weather model name
        dates_list: List of dates
        cycles_list: List of cycles
        forecast_hours: List of forecast hours
        variable_mapper: Variable mapper instance
        
    Returns:
        True if processing successful, False otherwise
    """
    try:
        from ..core.processors import GRIBProcessor
        
        # Get user configuration for this model + universal settings
        model_key = f"{model.lower()}.0p25"  # Adjust based on resolution
        model_user_config = {}
        if user_config and 'models' in user_config and model_key in user_config['models']:
            model_user_config = user_config['models'][model_key].copy()
        
        # Add universal settings to model config
        if user_config:
            # Add spatial bounds from universal config
            if 'spatial_bounds' in user_config:
                model_user_config['spatial_bounds'] = user_config['spatial_bounds']
            # Add processing options from universal config
            if 'processing' in user_config:
                model_user_config['processing'] = user_config['processing']
            # Add universal variables and levels if not specified per model
            if 'variables' in user_config and 'variables' not in model_user_config:
                model_user_config['variables'] = user_config['variables']
            if 'levels' in user_config and 'levels' not in model_user_config:
                model_user_config['levels'] = user_config['levels']
        
        # Initialize processor
        processor = GRIBProcessor(variable_mapper=variable_mapper, user_config=model_user_config)
        
        # Process each date/cycle combination
        for date in dates_list:
            for cycle in cycles_list:
                logger.info(f"🔄 Processing {model} {date} {cycle}Z")
                
                # Find input GRIB2 files  
                full_model_name = get_full_model_name(model)
                input_dir = Path(user_config.get('output_dir', 'data')) / full_model_name / date / cycle / "raw"
                if not input_dir.exists():
                    logger.warning(f"⚠️  No input directory found: {input_dir}")
                    continue
                
                # Get all GRIB2 files for the requested forecast hours
                input_files = []
                for forecast_hour in forecast_hours:
                    filename = f"gfs.t{cycle}z.pgrb2.0p25.f{forecast_hour:03d}"
                    file_path = input_dir / filename
                    
                    if file_path.exists():
                        input_files.append(file_path)
                        # logger.debug(f"📂 Found: {filename}")  # Too verbose for many files
                    else:
                        logger.warning(f"⚠️  Missing: {filename}")
                
                if not input_files:
                    logger.error(f"❌ No GRIB2 files found for {date}/{cycle}")
                    continue
                
                # Create output path using custom filename pattern
                out_file = model_user_config.get('out_file', model.lower())
                output_filename = OUTPUT_FILENAME_PATTERN.format(
                    out_file=out_file,
                    date=date,
                    cycle=cycle,
                    extension="nc"
                )
                
                output_dir = Path(user_config.get('output_dir', 'data')) / full_model_name / date / cycle / "processed"
                output_file = output_dir / output_filename
                
                logger.info(f"📊 Processing {len(input_files)} GRIB2 files → {output_file}")
                
                # Process files
                metadata = processor.process(input_files, output_file)
                
                # Log results
                logger.info(f"✅ Processed {metadata['time_steps']} time steps")
                logger.info(f"📦 Compression: {metadata['input_size_mb']} MB → {metadata['output_size_mb']} MB (ratio: {metadata['compression_ratio']}x)")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Processing failed: {e}")
        return False


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """
    Weather Data Downloader - Download and process numerical weather prediction data.
    
    This tool allows you to download weather data from various models including GFS,
    and process the raw data into optimized formats.
    """
    pass


@cli.command()
@click.argument('model', type=str)
@click.option('--date', '-d', help='Date in YYYYMMDD format (defaults to current UTC date)')
@click.option('--cycles', '-c', help='Forecast cycles to download (e.g., "00,06,12,18")')
@click.option('--forecast-range', '-f', help='Forecast hours range (e.g., "0,0" for single step, "0,3" for range)')
@click.option('--end-date', '-e', help='End date in YYYYMMDD format')
@click.option('--forecast-days', type=float, help='Number of forecast days to download (alternative to -f, supports decimals like 0.5 for 12h)')
@click.option('--process', is_flag=True, help='Process data after download')
def download(model: str, date: Optional[str], cycles: Optional[str], forecast_range: Optional[str], end_date: Optional[str], forecast_days: Optional[float], process: bool):
    """
    Download weather data for a specific model.
    
    MODEL: Name of the weather model (e.g., gfs)
    
    Examples:
        wd download gfs                                    # Día actual, todos los ciclos y forecast hours
        wd download gfs -d 20240827                       # Día específico, todos los ciclos y forecast hours
        wd download gfs -c 00,06                          # Solo ciclos 00Z y 06Z
        wd download gfs -f 0,24                           # Solo forecast hours 0h a 24h
        wd download gfs -d 20240827 -c 00,06 -f 0,12     # Combinado
        wd download gfs --process                         # Download and process in one step
    """
    _download_implementation(model, cycles, date, end_date, forecast_range, forecast_days, process)


@cli.command(name='download-process')
@click.argument('model', type=str)
@click.option('--date', '-d', help='Date in YYYYMMDD format (defaults to current UTC date)')
@click.option('--cycles', '-c', help='Forecast cycles (e.g., "00,06,12,18")')
@click.option('--forecast-range', '-f', help='Forecast hours range (e.g., "0,0" for single step, "0,3" for range)')
@click.option('--end-date', '-e', help='End date in YYYYMMDD format')
@click.option('--forecast-days', type=float, help='Number of forecast days to download (alternative to -f, supports decimals like 0.5 for 12h)')
def download_process(model: str, date: Optional[str], cycles: Optional[str], forecast_range: Optional[str], end_date: Optional[str], forecast_days: Optional[float]):
    """
    Combined download and process command.
    
    MODEL: Name of the weather model (e.g., gfs)
    
    Examples:
        wd download-process gfs -c 00 -f 115,126         # Download and process specific data
    """
    logger.info("🚀 Starting combined download and process workflow")
    _download_implementation(model, cycles, date, end_date, forecast_range, forecast_days, process=True)


def _download_implementation(model: str, cycles: Optional[str], date: Optional[str], end_date: Optional[str], forecast_range: Optional[str], forecast_days: Optional[float], process: bool):
    """
    Implementation of download functionality.
    
    MODEL: Name of the weather model (e.g., gfs)
    """
    try:
        # Validate model name
        if not DataValidator.validate_model_name(model):
            logger.error(f"Invalid model name '{model}'")
            return
        
        # Initialize variable mapper first
        try:
            mapping_file = Path("variables_mapping.yaml")
            variable_mapper = YAMLVariableMapper(mapping_file)
        except Exception as e:
            console.print(f"[red]Error: Could not load variable mapper: {e}[/red]")
            return
        
        # Parse cycles - if not specified, use all from config
        if cycles:
            try:
                cycles_list = CycleManager.parse_cycles(cycles)
            except ValueError as e:
                console.print(f"[red]Error: {e}[/red]")
                return
        else:
            # Get cycles from model config
            cycles_list = variable_mapper.get_cycles_for_model(model.lower())
        
        # Import datetime for time operations
        from datetime import datetime, timezone
        
        # Validate cycle availability for current time
        if not date and not end_date:  # Only check for current date
            current_utc = datetime.now(timezone.utc)
            current_hour = current_utc.hour
            
            # Check which cycles are available based on current UTC time
            available_cycles = []
            for cycle in cycles_list:
                cycle_hour = int(cycle)
                # GFS cycles are typically available 4-6 hours after the cycle time
                # For example, 00Z cycle is available around 06Z
                if current_hour >= (cycle_hour + 4) % 24:
                    available_cycles.append(cycle)
                else:
                    console.print(f"[yellow]Warning: Cycle {cycle}Z not yet available (current UTC: {current_hour:02d}Z)[/yellow]")
            
            if not available_cycles:
                console.print(f"[red]Error: No cycles available for current time (UTC: {current_hour:02d}Z)[/red]")
                console.print(f"[blue]Available cycles will be: {', '.join(cycles_list)}Z starting at {(min(int(c) for c in cycles_list) + 4) % 24:02d}Z[/blue]")
                return
            
            cycles_list = available_cycles
            console.print(f"[green]Available cycles for current time: {', '.join(cycles_list)}[/green]")
        
        # Parse date range
        if date and end_date:
            try:
                start_dt, end_dt = TimeRangeManager.parse_date_range(date, end_date)
                dates_list = TimeRangeManager.generate_date_sequence(date, end_date)
                logger.info(f"📅 Using specified date range: {date} to {end_date}")
            except ValueError as e:
                logger.error(f"❌ Error: {e}")
                return
        elif date:
            dates_list = [date]
        else:
            # Use current UTC date
            utc_now = datetime.now(timezone.utc)
            current_date = utc_now.strftime("%Y%m%d")
            dates_list = [current_date]
            logger.info(f"📅 Using current UTC date: {current_date}")
        
        # Parse forecast range/days - if neither specified, use all from config
        forecast_hours = []
        
        # Validate that only one of forecast_range or forecast_days is specified
        if forecast_range and forecast_days:
            console.print(f"[red]Error: Cannot specify both --forecast-range and --forecast-days. Use one or the other.[/red]")
            return
        
        if forecast_range:
            try:
                # Get model configuration for proper forecast hour generation
                # We need to initialize variable_mapper first
                try:
                    mapping_file = Path("variables_mapping.yaml")
                    temp_variable_mapper = YAMLVariableMapper(mapping_file)
                    model_config = temp_variable_mapper.get_model_config(model.lower())
                except Exception:
                    model_config = None  # Fallback to default behavior
                
                forecast_hours = ForecastManager.parse_forecast_range(forecast_range, model_config)
            except ValueError as e:
                console.print(f"[red]Error: {e}[/red]")
                return
        elif forecast_days:
            try:
                # Calculate forecast hours based on number of days
                mapping_file = Path("variables_mapping.yaml")
                temp_variable_mapper = YAMLVariableMapper(mapping_file)
                model_config = temp_variable_mapper.get_model_config(model.lower())
                forecast_hours = calculate_forecast_hours_from_days(forecast_days, model_config)
            except Exception as e:
                console.print(f"[red]Error calculating forecast hours for {forecast_days} days: {e}[/red]")
                return
        else:
            # Use all forecast hours from model config
            forecast_hours = variable_mapper.get_forecast_hours_for_model(model.lower())
        
        # Validate forecast hours availability for current time
        if not date and not end_date:  # Only check for current date
            current_utc = datetime.now(timezone.utc)
            current_hour = current_utc.hour
            
            # TODO: Implement proper availability logic based on model config
            # For now, allow all forecast hours to proceed
            console.print(f"[yellow]Warning: Availability validation temporarily disabled for testing[/yellow]")
            console.print(f"[green]Proceeding with all requested forecast hours: {', '.join(map(str, forecast_hours))}[/green]")
        
        # Display download plan
        console.print(f"\n[bold]Download Plan:[/bold]")
        console.print(f"Model: {model}")
        console.print(f"Cycles: {', '.join(cycles_list)}")
        console.print(f"Dates: {', '.join(dates_list)}")
        console.print(f"Forecast Hours: {', '.join(map(str, forecast_hours))}")
        console.print(f"Process after download: {process}")
        
        # Show current UTC time for reference
        current_utc = datetime.now(timezone.utc)
        console.print(f"[dim]Current UTC time: {current_utc.strftime('%Y-%m-%d %H:%M:%S')}Z[/dim]")
        
        # Confirm with user
        if not click.confirm("\nProceed with download?"):
            console.print("[yellow]Download cancelled.[/yellow]")
            return
        
        # Initialize variable mapper
        try:
            mapping_file = Path("variables_mapping.yaml")
            variable_mapper = YAMLVariableMapper(mapping_file)
        except Exception as e:
            console.print(f"[yellow]Warning: Could not load variable mapper: {e}[/yellow]")
            variable_mapper = None
        
        # Load user configuration
        try:
            config_file = Path("config.yaml")
            with open(config_file, 'r') as f:
                user_config = yaml.safe_load(f)
        except Exception as e:
            logger.warning(f"Could not load user config: {e}")
            user_config = {}
        
        # Initialize provider (for now, only GFS is supported)
        if model.lower() == 'gfs':
            # Get model configuration to pass to provider
            model_config = variable_mapper.get_model_config(model.lower())
            
            # Merge user config for this model with model config
            model_key = f"{model.lower()}.0p25"  # Adjust based on resolution
            if 'models' in user_config and model_key in user_config['models']:
                # Merge user preferences with model technical specs
                combined_config = {**model_config, **user_config['models'][model_key]}
            else:
                combined_config = model_config
                logger.warning(f"No user configuration found for {model_key}, using defaults")
            
            # Always add universal settings to the combined config
            if 'spatial_bounds' in user_config:
                combined_config['spatial_bounds'] = user_config['spatial_bounds']
            # Add processing options from universal config
            if 'processing' in user_config:
                combined_config['processing'] = user_config['processing']
            # Add universal variables and levels if not specified per model
            if 'variables' in user_config and 'variables' not in combined_config:
                combined_config['variables'] = user_config['variables']
            if 'levels' in user_config and 'levels' not in combined_config:
                combined_config['levels'] = user_config['levels']
            
            provider = GFSProvider(config=combined_config, variable_mapper=variable_mapper)
        else:
            logger.error(f"Model '{model}' is not yet supported.")
            return
        
        # Display provider info
        metadata = provider.get_metadata()
        console.print(f"\n[bold]Model Information:[/bold]")
        console.print(f"Name: {metadata['model_name']}")
        console.print(f"Resolution: {metadata['resolution']}°")
        console.print(f"Data Source: {metadata['data_source']}")
        
        # Initialize HTTP downloader
        from ..core.downloaders import HTTPDataDownloader
        
        # Create downloader with progress callback
        def progress_callback(progress, downloaded, total):
            if total > 0:
                percentage = (downloaded / total) * 100
                progress.update(task, description=f"Downloading... {percentage:.1f}%")
        
        downloader = HTTPDataDownloader(
            max_retries=3,
            timeout=30,
            progress_callback=progress_callback
        )
        
        # Clean up existing files before downloading
        logger.info("🧹 CLEANUP PHASE")
        for date in dates_list:
            for cycle in cycles_list:
                cleanup_existing_files(model, date, cycle, forecast_hours, variable_mapper)
        
        # Prepare download specifications
        logger.info("📋 PREPARATION PHASE")
        logger.debug(f"Preparing downloads for {len(dates_list)} dates, {len(cycles_list)} cycles, {len(forecast_hours)} forecast hours")
        downloads = []
        
        for date in dates_list:
            for cycle in cycles_list:
                for forecast_hour in forecast_hours:
                    try:
                        # Get variables from user config or use defaults
                        variables_to_download = None
                        if 'models' in user_config and model_key in user_config['models']:
                            variables_to_download = user_config['models'][model_key].get('variables', None)
                        
                        # Generate URL for this combination
                        url = provider.get_download_url(
                            date=date,
                            cycle=cycle,
                            forecast_hour=forecast_hour,
                            variables=variables_to_download,
                            levels=None  # Use defaults for now
                        )
                        
                        # Create destination path
                        # Generate filename exactly as provided by source (without date)
                        filename = f"gfs.t{cycle}z.pgrb2.0p25.f{forecast_hour:03d}"
                        full_model_name = get_full_model_name(model)
                        destination = Path(user_config.get('output_dir', 'data')) / full_model_name / date / cycle / "raw"
                        
                        downloads.append({
                            'url': url,
                            'destination': destination,
                            'filename': filename
                        })
                        
                        logger.debug(f"🔗 Generated URL for {date}/{cycle}Z/f{forecast_hour:03d}h → {filename}")
                        
                    except Exception as e:
                        logger.error(f"❌ Error preparing download for {date}/{cycle}/f{forecast_hour}: {e}")
                        continue
        
        logger.info(f"✅ Prepared {len(downloads)} downloads successfully")
        
        # Display download plan
        logger.info("📥 DOWNLOAD PHASE")
        logger.debug(f"Downloading {len(downloads)} files")
        for download in downloads:
            logger.debug(f"  • {download['filename']}")
        
        # Execute downloads
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Preparing downloads...", total=len(downloads))
            
            # Download files
            results = downloader.download_multiple_files(downloads)
            
            # Count successes and failures
            successful = sum(1 for success in results.values() if success)
            failed = len(results) - successful
            
            if failed == 0:
                progress.update(task, description="All downloads completed!")
                logger.success(f"🎉 Download completed successfully! {successful} files downloaded")
            else:
                progress.update(task, description="Downloads completed with errors")
                logger.warning(f"⚠️  Download completed with {failed} failures. {successful} files downloaded successfully")
        
        if process:
            logger.info("🔄 PROCESSING PHASE")
            logger.info("Processing downloaded GRIB2 files to NetCDF")
            
            # Process the downloaded files
            success = process_downloaded_files(model, dates_list, cycles_list, forecast_hours, variable_mapper, user_config)
            
            if success:
                logger.success("🎉 Processing completed successfully!")
            else:
                logger.error("❌ Processing failed")
    
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        # Show help if requested
        if '--help' in sys.argv or '-h' in sys.argv:
            click.echo(cli.get_help())


@cli.command()
@click.argument('model', type=str)
@click.option('--cycles', '-c', help='Forecast cycles to process (e.g., "00,06,12,18")')
@click.option('--date', '-d', help='Date in YYYYMMDD format (defaults to current UTC date)')
@click.option('--forecast-range', '-f', required=True, help='Forecast hours range (e.g., "0,0" for single step, "0,3" for range)')
def process(model: str, cycles: Optional[str], date: Optional[str], forecast_range: str):
    """
    Process previously downloaded weather data.
    
    MODEL: Name of the weather model to process (e.g., gfs)
    
    Examples:
        wd process gfs -c 00 -d 20250827 -f 0,3            # Process specific date, cycle and forecast range (0-3h)
        wd process gfs -c 00 -f 0,168                       # Process specific cycle for current date (7 days)
        wd process gfs -d 20250827 -f 0,3                   # Process specific date and forecast range
    
    Note: The -f (forecast-range) flag is required to specify which forecast hours to process.
    """
    try:
        # Validate model name
        if not DataValidator.validate_model_name(model):
            logger.error(f"Invalid model name '{model}'")
            return
        
        logger.info(f"🔄 Processing data for model: {model}")
        
        # Initialize variable mapper
        try:
            mapping_file = Path("variables_mapping.yaml")
            variable_mapper = YAMLVariableMapper(mapping_file)
        except Exception as e:
            logger.error(f"Could not load variable mapper: {e}")
            return
        
        # Load user configuration
        try:
            config_file = Path("config.yaml")
            with open(config_file, 'r') as f:
                user_config = yaml.safe_load(f)
        except Exception as e:
            logger.warning(f"Could not load user config: {e}")
            user_config = {}
        
        # Parse cycles - if not specified, find all available in data directory
        if cycles:
            try:
                cycles_list = CycleManager.parse_cycles(cycles)
            except ValueError as e:
                logger.error(f"Error parsing cycles: {e}")
                return
        else:
            # Find all available cycles in data directory
            full_model_name = get_full_model_name(model)
            model_dir = Path("data") / full_model_name
            cycles_list = []
            if model_dir.exists():
                for date_dir in model_dir.iterdir():
                    if date_dir.is_dir():
                        for cycle_dir in date_dir.iterdir():
                            if cycle_dir.is_dir() and cycle_dir.name not in cycles_list:
                                cycles_list.append(cycle_dir.name)
            cycles_list.sort()
            if not cycles_list:
                logger.error(f"No downloaded data found for model '{model}'")
                return
        
        # Parse date - if not specified, use current UTC date
        if date:
            dates_list = [date]
            logger.info(f"Using specified date: {date}")
        else:
            # Use current UTC date
            utc_now = datetime.now(timezone.utc)
            current_date = utc_now.strftime("%Y%m%d")
            dates_list = [current_date]
            logger.info(f"Using current UTC date: {current_date}")
        
        # Parse forecast range (now required)
        try:
            model_config = variable_mapper.get_model_config(model.lower())
            forecast_hours = ForecastManager.parse_forecast_range(forecast_range, model_config)
        except ValueError as e:
            logger.error(f"Error parsing forecast range: {e}")
            return
        
        # Display processing plan
        logger.info(f"📋 Processing Plan:")
        logger.info(f"   Model: {model}")
        logger.info(f"   Cycles: {', '.join(cycles_list)}")
        logger.info(f"   Dates: {', '.join(dates_list)}")
        logger.info(f"   Forecast Hours: {', '.join(map(str, forecast_hours))}")
        
        # Confirm with user
        if not click.confirm("\nProceed with processing?"):
            logger.warning("Processing cancelled.")
            return
        
        # Process the files
        logger.info("🔄 PROCESSING PHASE")
        logger.info("Processing GRIB2 files to NetCDF")
        
        success = process_downloaded_files(model, dates_list, cycles_list, forecast_hours, variable_mapper, user_config)
        
        if success:
            logger.success("🎉 Processing completed successfully!")
        else:
            logger.error("❌ Processing failed")
    
    except Exception as e:
        logger.error(f"Error: {e}")
        # Show help if requested
        if '--help' in sys.argv or '-h' in sys.argv:
            click.echo(cli.get_help())


@cli.command()
@click.argument('model', type=str)
def status(model: str):
    """
    Show status of downloaded data for a specific model.
    
    MODEL: Name of the weather model (e.g., gfs)
    
    Examples:
        weather-downloader status gfs
    """
    try:
        # Validate model name
        if not DataValidator.validate_model_name(model):
            console.print(f"[red]Error: Invalid model name '{model}'[/red]")
            return
        
        console.print(f"[bold]Status for model: {model}[/bold]")
        
        # TODO: Implement status checking logic
        console.print("[yellow]Status checking not yet implemented.[/yellow]")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        # Show help if requested
        if '--help' in sys.argv or '-h' in sys.argv:
            click.echo(cli.get_help())


@cli.command()
@click.option('--model', '-m', required=True, help='Weather model (e.g., gfs)')
@click.option('--date', '-d', required=True, help='Date in YYYYMMDD format')
@click.option('--cycles', '-c', help='Forecast cycles to clean (e.g., "00,06,12,18"). If not specified, cleans all cycles for the date.')
@click.option('--directory', type=click.Choice(['raw', 'processed', 'interpolated']), help='Specific directory type to clean. If not specified, cleans all directories.')
@click.option('--confirm', '-y', is_flag=True, help='Skip confirmation prompt')
def clean(model: str, date: str, cycles: Optional[str], directory: Optional[str], confirm: bool):
    """
    Clean (delete) downloaded or processed data.
    
    Examples:
        wd clean -m gfs -d 20250828                        # Delete everything under gfs.0p25/20250828/
        wd clean -m gfs -d 20250828 -c 00                  # Delete everything under gfs.0p25/20250828/00/
        wd clean -m gfs -d 20250828 -c 00 --directory raw  # Delete only raw data for specific date/cycle
    """
    try:
        # Date is now required, no default needed
        
        # Get full model name
        full_model_name = get_full_model_name(model)
        
        # Build target path based on specified options
        base_path = Path("data") / full_model_name / date
        
        if not base_path.exists():
            logger.error(f"No data found for {model} on {date}")
            return
        
        # Determine what to clean
        dirs_to_clean = []
        total_size = 0
        
        if cycles:
            # Clean specific cycles: clean -m gfs -d 20250828 -c 00
            try:
                cycles_list = CycleManager.parse_cycles(cycles)
            except ValueError as e:
                logger.error(f"Error parsing cycles: {e}")
                return
            
            for cycle in cycles_list:
                cycle_path = base_path / cycle
                if cycle_path.exists():
                    if directory:
                        # Clean specific directory within cycle
                        target_dir = cycle_path / directory
                        if target_dir.exists():
                            dir_size = sum(f.stat().st_size for f in target_dir.glob('**/*') if f.is_file())
                            total_size += dir_size
                            dirs_to_clean.append((target_dir, dir_size))
                    else:
                        # Clean entire cycle directory
                        dir_size = sum(f.stat().st_size for f in cycle_path.glob('**/*') if f.is_file())
                        total_size += dir_size
                        dirs_to_clean.append((cycle_path, dir_size))
        else:
            # Clean entire date: clean -m gfs -d 20250828
            if directory:
                # Clean specific directory type across all cycles
                for cycle_dir in base_path.iterdir():
                    if cycle_dir.is_dir() and cycle_dir.name.isdigit():
                        target_dir = cycle_dir / directory
                        if target_dir.exists():
                            dir_size = sum(f.stat().st_size for f in target_dir.glob('**/*') if f.is_file())
                            total_size += dir_size
                            dirs_to_clean.append((target_dir, dir_size))
            else:
                # Clean entire date directory
                dir_size = sum(f.stat().st_size for f in base_path.glob('**/*') if f.is_file())
                total_size += dir_size
                dirs_to_clean.append((base_path, dir_size))
        
        if not dirs_to_clean:
            logger.info(f"No data found to clean for {model} {date}")
            return
        
        # Show what will be deleted
        logger.info(f"🗑️  CLEANUP PLAN:")
        logger.info(f"   Model: {model} ({full_model_name})")
        logger.info(f"   Date: {date}")
        if cycles:
            logger.info(f"   Cycles: {cycles}")
        else:
            logger.info(f"   Cycles: ALL")
        if directory:
            logger.info(f"   Directory: {directory}")
        else:
            logger.info(f"   Directory: ALL")
        logger.info(f"   Total size: {total_size / (1024*1024):.1f} MB")
        logger.info(f"   Paths to delete:")
        
        for target_dir, size in dirs_to_clean:
            logger.info(f"     • {target_dir} ({size / (1024*1024):.1f} MB)")
        
        # Confirmation
        if not confirm:
            response = click.prompt("\nProceed with cleanup? [y/N]", default="n")
            if response.lower() not in ['y', 'yes']:
                logger.info("Cleanup cancelled")
                return
        
        # Perform cleanup
        logger.info("🧹 Starting cleanup...")
        success_count = 0
        
        for target_dir, size in dirs_to_clean:
            try:
                shutil.rmtree(target_dir)
                logger.info(f"✅ Deleted: {target_dir}")
                success_count += 1
            except Exception as e:
                logger.error(f"❌ Failed to delete {target_dir}: {e}")
        
        if success_count == len(dirs_to_clean):
            logger.success(f"🎉 Cleanup completed! Deleted {success_count} directories ({total_size / (1024*1024):.1f} MB)")
        else:
            logger.warning(f"⚠️  Partial cleanup: {success_count}/{len(dirs_to_clean)} directories deleted")
            
    except Exception as e:
        logger.error(f"❌ Error during cleanup: {e}")


@cli.command()
def list_models():
    """List all available weather models."""
    try:
        console.print("[bold]Available Weather Models:[/bold]")
        
        # Create a table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Model", style="cyan")
        table.add_column("Description", style="white")
        table.add_column("Resolution", style="green")
        table.add_column("Status", style="yellow")
        
        # Load model configurations
        try:
            models_config_path = Path("models_config.yaml")
            with open(models_config_path, 'r') as f:
                models_config = yaml.safe_load(f)
            
            # Add models from configuration
            for model_key, model_config in models_config['models'].items():
                model_name = model_key.split('.')[0]
                description = model_config['name']
                resolution = f"{model_config['resolution']}°"
                status = "Available" if model_name == "gfs" else "Coming Soon"
                
                table.add_row(
                    model_name,
                    description,
                    resolution,
                    status
                )
        except Exception as e:
            console.print(f"[yellow]Warning: Could not load models config: {e}[/yellow]")
            # Fallback to hardcoded models
            table.add_row("gfs", "Global Forecast System", "0.25°", "Available")
            table.add_row("ecmwf", "European Centre for Medium-Range Weather Forecasts", "0.25°", "Coming Soon")
            table.add_row("gem", "Global Environmental Multiscale Model", "0.1°", "Coming Soon")
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@cli.command()
@click.option('--disk-usage', is_flag=True, help='Show detailed disk usage analysis')
def status(disk_usage: bool):
    """
    Show status of downloaded data with available dates and cycles.
    
    Examples:
        wd status                           # Show all available dates/cycles
        wd status --disk-usage              # Include detailed disk usage
    """
    try:
        data_dir = Path("data")
        
        if not data_dir.exists():
            logger.info("📊 STATUS: No data directory found")
            logger.info("💡 Run a download command first: wd download gfs")
            return
        
        _show_available_data(data_dir)
        
        if disk_usage:
            _show_disk_usage(data_dir)
            
    except Exception as e:
        logger.error(f"Error getting status: {e}")


def _show_available_data(data_dir: Path):
    """Show available dates and cycles for all models."""
    logger.info("📊 WEATHER DATA STATUS")
    logger.info("=" * 30)
    
    if not list(data_dir.iterdir()):
        logger.info("📁 No data found")
        return
    
    total_size = 0
    total_files = 0
    
    for model_dir in data_dir.iterdir():
        if model_dir.is_dir():
            logger.info(f"\n🌍 {model_dir.name.upper()}:")
            
            # Collect all date/cycle combinations
            date_cycles = {}
            model_size = 0
            model_files = 0
            
            for date_dir in model_dir.iterdir():
                if date_dir.is_dir() and date_dir.name.isdigit():
                    date_name = date_dir.name
                    cycles = []
                    
                    for cycle_dir in date_dir.iterdir():
                        if cycle_dir.is_dir() and cycle_dir.name.isdigit():
                            cycle_name = cycle_dir.name
                            
                            # Check if data exists and what type
                            has_raw = (cycle_dir / "raw").exists() and any((cycle_dir / "raw").iterdir())
                            has_processed = (cycle_dir / "processed").exists() and any((cycle_dir / "processed").iterdir())
                            has_interpolated = (cycle_dir / "interpolated").exists() and any((cycle_dir / "interpolated").iterdir())
                            
                            # Count files and size for this cycle
                            cycle_files = 0
                            cycle_size = 0
                            for file_path in cycle_dir.rglob('*'):
                                if file_path.is_file():
                                    cycle_files += 1
                                    cycle_size += file_path.stat().st_size
                            
                            model_files += cycle_files
                            model_size += cycle_size
                            
                            # Determine status icon
                            if has_interpolated:
                                status = "✅"  # Complete processing
                            elif has_processed:
                                status = "🔄"  # Partially processed
                            elif has_raw:
                                status = "📥"  # Raw data only
                            else:
                                status = "❌"  # No data
                            
                            cycles.append(f"{cycle_name}Z{status}")
                    
                    if cycles:
                        date_cycles[date_name] = cycles
            
            # Display dates and cycles
            if date_cycles:
                for date_name in sorted(date_cycles.keys()):
                    cycles_str = " ".join(sorted(date_cycles[date_name]))
                    logger.info(f"   📅 {date_name}: {cycles_str}")
                
                logger.info(f"   📊 Total: {model_files} files, {model_size / (1024*1024):.1f} MB")
            else:
                logger.info("   📁 No data found")
            
            total_files += model_files
            total_size += model_size
    
    if total_size > 0:
        logger.info(f"\n📊 TOTAL SUMMARY: {total_files} files, {total_size / (1024*1024):.1f} MB")
        logger.info("📖 Legend: ✅=Complete 🔄=Processed 📥=Raw only ❌=No data")


def _show_disk_usage(data_dir: Path):
    """Show disk usage analysis."""
    logger.info("\n💾 DISK USAGE ANALYSIS")
    logger.info("=" * 30)
    
    usage_by_type = {'raw': 0, 'processed': 0, 'interpolated': 0}
    files_by_type = {'raw': 0, 'processed': 0, 'interpolated': 0}
    
    for file_path in data_dir.rglob('*'):
        if file_path.is_file():
            size = file_path.stat().st_size
            parent_name = file_path.parent.name
            
            if parent_name in usage_by_type:
                usage_by_type[parent_name] += size
                files_by_type[parent_name] += 1
    
    total_size = sum(usage_by_type.values())
    
    if total_size == 0:
        logger.info("📁 No data files found")
        return
    
    logger.info("📁 Storage by Type:")
    for data_type, size in usage_by_type.items():
        if size > 0:
            percentage = (size / total_size) * 100
            size_mb = size / (1024*1024)
            files = files_by_type[data_type]
            logger.info(f"   • {data_type.capitalize()}: {size_mb:.1f} MB ({percentage:.1f}%) - {files} files")
    
    logger.info(f"\n📊 Total: {total_size / (1024*1024):.1f} MB")





if __name__ == '__main__':
    cli()
