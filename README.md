# Weather Data Downloader

[![CI](https://github.com/USERNAME/weather-data-downloader/workflows/CI/badge.svg)](https://github.com/USERNAME/weather-data-downloader/actions/workflows/ci.yml)
[![Release](https://github.com/USERNAME/weather-data-downloader/workflows/Release/badge.svg)](https://github.com/USERNAME/weather-data-downloader/actions/workflows/release.yml)
[![codecov](https://codecov.io/gh/USERNAME/weather-data-downloader/branch/main/graph/badge.svg)](https://codecov.io/gh/USERNAME/weather-data-downloader)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-yellow.svg)](https://conventionalcommits.org)
[![semantic-release](https://img.shields.io/badge/%20%20%F0%9F%93%A6%F0%9F%9A%80-semantic--release-e10079.svg)](https://github.com/semantic-release/semantic-release)

A scalable and robust Python system for downloading numerical weather prediction data from various models including GFS, ECMWF, and GEM.

## 🎯 Features

- **Multi-Model Support**: Download data from GFS, ECMWF, and GEM models
- **Flexible Download Options**: Download specific date ranges, cycles, and forecast hours
- **🆕 Forecast Days Support**: Use `--forecast-days 0.5` for 12 hours, `--forecast-days 2` for 48 hours
- **🆕 Model Directory Structure**: Full model names (e.g., `gfs.0p25/`) with CLI shortcuts (e.g., `gfs`)
- **Dual Processing Pipeline**: Generates both original and interpolated (hourly) data
- **Universal Configuration**: Spatial bounds, variables, and processing options apply globally
- **Custom File Naming**: Configurable output filenames with date/cycle patterns
- **Storage Optimization**: NetCDF compression with 6x+ compression ratios
- **Spatial Filtering**: Download only specified regions (e.g., South America)
- **Variable Standardization**: Consistent naming across different models
- **Robust Error Handling**: Retry mechanisms and comprehensive logging
- **CLI Interface**: Easy-to-use command-line interface with combined operations
- **Extensible Architecture**: Built following SOLID principles for easy extension

## 🏗️ Architecture

The system follows SOLID principles with a clean, modular architecture:

```
src/
├── core/
│   ├── interfaces/          # Abstract base classes
│   ├── providers/           # Model-specific implementations
│   ├── downloaders/         # Download strategies
│   ├── processors/          # Data processing
│   └── storage/             # Storage management
├── utils/                   # Utility functions
├── cli/                     # Command-line interface
└── models/                  # Data models
```

## 🚀 Quick Start

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd weather-data-downloader
   ```

2. **Install dependencies**:
   ```bash
   poetry install
   ```

3. **Activate virtual environment** (Poetry 2.0+):
   ```bash
   # Option 1: Activate environment (recommended)
   poetry env activate
   source .venv/bin/activate
   
   # Option 2: Use poetry run (always works)
   poetry run wd download gfs
   ```

### Basic Usage

1. **List available models**:
   ```bash
   wd list-models
   ```

2. **Download and process GFS data**:
   ```bash
   # Download and process together (recommended)
   wd download-process gfs -c 00 -f 0,24
   
   # Download for specific date
   wd download-process gfs -d 20250828 -c 00,06
   
   # Download by forecast days (new feature)
   wd download-process gfs -c 00 --forecast-days 0.5   # Half day (12 hours)
   wd download-process gfs -d 20250828 --forecast-days 2  # 2 days (48 hours)
   
   # Download specific forecast range
   wd download-process gfs -c 00 -f 115,117
   
   # Download only (without processing)
   wd download gfs -c 00 -f 0,6
   ```

3. **Process previously downloaded data**:
   ```bash
   # Process specific data
   wd process gfs -c 00 -f 0,24
   
   # Process all available data
   wd process gfs
   ```

4. **Check data status**:
   ```bash
   wd status gfs
   ```

## 🎯 Common Use Cases

### Quick Start Examples
```bash
# Download current weather (12 hours)
wd download-process gfs -c 00 --forecast-days 0.5

# Download specific date (2 days of forecast)  
wd download-process gfs -d 20250828 --forecast-days 2

# Download for machine learning (7 days)
wd download-process gfs -c 00,12 --forecast-days 7

# Download specific forecast range
wd download-process gfs -c 00 -f 115,126
```

### Time-based Downloads
```bash
# Half day (12 hours): --forecast-days 0.5
# One day (24 hours): --forecast-days 1  
# One week (168 hours): --forecast-days 7
# Custom range: -f 0,72 (specific hours)
```

### Date Specifications  
```bash
# Current UTC date (default): No -d flag needed
# Specific date: -d 20250828
# Date with cycles: -d 20250828 -c 00,12
```

## 📋 CLI Commands

### Download-Process Command (Recommended)
```bash
wd download-process <model> [OPTIONS]

Options:
  -d, --date TEXT           Specific date in YYYYMMDD format (default: current UTC date)
  -c, --cycles TEXT         Forecast cycles (e.g., "00,06,12,18")  
  -f, --forecast-range TEXT Forecast hours range (e.g., "0,24", "115,126")
  --forecast-days FLOAT     Number of forecast days (supports decimals: 0.5=12h, 1=24h, 2=48h)

Examples:
  wd download-process gfs -c 00 -f 115,117              # Specific hours
  wd download-process gfs -c 00 --forecast-days 0.5     # Half day (12 hours)
  wd download-process gfs -d 20250828 --forecast-days 2  # Specific date, 2 days
```

### Download Command
```bash
wd download <model> [OPTIONS]

Options:
  -d, --date TEXT           Specific date in YYYYMMDD format (default: current UTC date)
  -c, --cycles TEXT         Forecast cycles (e.g., "00,06,12,18")
  -f, --forecast-range TEXT Forecast hours range (e.g., "0,24", "3,12")
  --forecast-days FLOAT     Number of forecast days (supports decimals: 0.5=12h, 1=24h, 2=48h)
  --process                 Process data after download

Examples:
  wd download gfs -c 00,06 -f 0,24 --process           # Traditional range
  wd download gfs -c 00 --forecast-days 1 --process    # 1 day with processing
```

### Process Command
```bash
wd process <model> [OPTIONS]

Options:
  -d, --date TEXT           Specific date in YYYYMMDD format
  -c, --cycles TEXT         Forecast cycles to process
  -f, --forecast-range TEXT Forecast hours range to process
  --forecast-days FLOAT     Number of forecast days (supports decimals)
  --end-date TEXT           End date for processing range

Examples:
  wd process gfs -c 00 -f 0,24                     # Process specific hours
  wd process gfs -d 20250828 --forecast-days 1     # Process 1 day of data
```

### List Models Command
```bash
wd list-models
```

## ⚙️ Configuration

The system uses two YAML configuration files for maximum flexibility and maintainability:

### **`models_config.yaml`** - Technical Model Characteristics
- **Model specifications** (resolution, base URLs, forecast frequencies)
- **Available cycles** and forecast hour ranges for each cycle
- **Availability delays** (when data becomes available after cycle time)
- **Forecast intervals** with tuples format: `[start, end, frequency]`
- **File formats** (download format, extension, final format)

### **`config.yaml`** - Universal User Preferences
- **Universal settings** applied to all models:
  - `output_dir`: Where to store data (default: "data", configurable to "tmp/data", etc.)
  - `spatial_bounds`: Geographic region (e.g., South America)
  - `processing`: Target frequency, compression settings
  - `download`: Retry logic, concurrency, timeouts
- **Model-specific overrides**:
  - `variables`: Standard variable names (t2m, rh2m, u10m, v10m, hgt)
  - `levels`: Height levels (surface, 2_m_above_ground, 10_m_above_ground)
  - `out_file`: Custom filename prefix

Example configuration:
```yaml
# Universal settings (apply to all models)
output_dir: "data"
spatial_bounds:
  lon_min: -90.0    # South America bounds
  lon_max: -30.0
  lat_min: -60.0
  lat_max: 15.0

processing:
  target_frequency: "1H"  # Always generates both original and interpolated
  compression:
    enabled: true
    level: 5

# Model-specific settings
models:
  gfs.0p25:
    variables: ["t2m", "rh2m", "u10m", "v10m", "hgt"]
    levels: ["surface", "2_m_above_ground", "10_m_above_ground"]
    out_file: "gfs.0p25"  # Results in: gfs.0p25.20250828.00z.nc
```

## 📁 Data Organization

The new optimized data structure organizes files by date and cycle for better organization:

```
{output_dir}/
├── gfs.0p25/               # Full model name (configurable directory)
│   └── 20250828/           # Date folder (YYYYMMDD)
│       └── 00/             # Cycle folder (HH)
│           ├── raw/        # Downloaded GRIB2 files
│           │   ├── gfs.t00z.pgrb2.0p25.f000
│           │   ├── gfs.t00z.pgrb2.0p25.f001
│           │   ├── ...
│           │   └── gfs.t00z.pgrb2.0p25.f012
│           ├── processed/  # Original frequency NetCDF
│           │   └── gfs.0p25.20250828.00z.nc (8.4 MB)
│           └── interpolated/ # Hourly interpolated NetCDF
│               └── gfs.0p25.20250828.00z.nc (8.4 MB)
├── ecmwf.0p25/             # Future: ECMWF data
└── gem.0p1/                # Future: GEM data
```

### File Naming Convention
- **Pattern**: `{out_file}.{date}.{cycle}z.{extension}`
- **Example**: `gfs.0p25.20250828.00z.nc`
- **Configurable**: Modify `out_file` in config.yaml per model

### Dual Output Strategy
- **`processed/`**: Original model frequencies (for scientific analysis & variable calculations)
- **`interpolated/`**: Hourly interpolated data (ready for Machine Learning)
- **Both generated automatically** from every processing run

## 🎯 Current Implementation Status

### ✅ Implemented Features
- **GFS 0.25° Model**: Fully functional download and processing
- **🆕 Forecast Days CLI**: `--forecast-days` option with decimal support (0.5=12h, 1=24h, 2=48h)
- **🆕 Model Directory Mapping**: CLI uses short names (`gfs`) → full directories (`gfs.0p25/`)
- **🆕 Improved Date Handling**: `-d` flag for date (resolves CLI conflicts)
- **Spatial Filtering**: Downloads only specified regions (e.g., South America)
- **Variable Standardization**: Consistent naming (t2m, rh2m, u10m, v10m, hgt)
- **Dual Output**: Always generates both original and interpolated data
- **Smart Cleanup**: Removes existing files before new downloads
- **Universal Configuration**: Spatial bounds and processing options apply globally
- **Robust GRIB Loading**: Handles multiple levels with cfgrib conflict resolution
- **NetCDF Compression**: Achieves 6x+ compression ratios
- **Custom File Naming**: Configurable output patterns with date/cycle

### 🔄 Processing Pipeline
1. **Download**: GRIB2 files filtered by region and variables
2. **Load**: Multi-level GRIB2 files with conflict resolution
3. **Filter**: Keep only configured variables
4. **Standardize**: Convert to universal variable names
5. **Subset**: Apply spatial bounds
6. **Generate Dual Output**:
   - `processed/`: Original frequencies + future variable calculations
   - `interpolated/`: Hourly data for ML applications
7. **Optimize**: NetCDF compression and chunking

## 🔧 Development

### Project Structure
- **Interfaces**: Define contracts for all implementations
- **Providers**: Model-specific data source implementations (GFS implemented)
- **Downloaders**: HTTP/FTP download strategies
- **Processors**: Data processing and interpolation (GRIB2→NetCDF)
- **Storage**: File organization and management
- **Utils**: Common utility functions

### Adding New Models
1. Implement the `WeatherModelProvider` interface
2. Add configuration to `config.yaml`
3. Update the CLI to recognize the new model

### Adding New Features
1. Follow SOLID principles
2. Add comprehensive tests
3. Update documentation
4. Maintain backward compatibility

## 🧪 Testing

Run tests with:
```bash
poetry run pytest
```

## 📚 Documentation

- **API Reference**: See docstrings in source code
- **Examples**: Check the `examples/` directory
- **Configuration**: See `config.yaml` for all options

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes following the coding standards
4. Add tests for new functionality
5. Submit a pull request

## 🤝 Contributing

This project uses [Conventional Commits](https://conventionalcommits.org/) and [Semantic Release](https://semantic-release.gitbook.io/) for automatic versioning and changelog generation.

Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:
- Conventional commit message format
- Development setup
- Testing requirements
- Code style

For interactive commit creation:
```bash
poetry run cz commit
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- NOAA/NOMADS for providing GFS data
- The Python scientific computing community
- Contributors and maintainers

## 🔮 Roadmap

### Phase 1: Core Infrastructure ✅ COMPLETED
- [x] GFS 0.25° data provider with spatial filtering
- [x] Robust GRIB2 to NetCDF processing pipeline
- [x] Dual output strategy (original + interpolated)
- [x] Universal configuration system
- [x] Variable standardization across models
- [x] CLI interface with combined operations

### Phase 2: Model Expansion (Next)
- [ ] ECMWF 0.25° data provider
- [ ] GEM 0.1° data provider  
- [ ] Derived variable calculations (wind speed, potential temperature, etc.)
- [ ] Advanced temporal interpolation (de-accumulation for precipitation)

### Phase 3: Advanced Features
- [ ] Cloud storage support (AWS S3, Google Cloud)
- [ ] Parallel download and processing
- [ ] Cycle completion logic (fill incomplete cycles)
- [ ] Real-time data streaming
- [ ] Data validation and quality control

### Phase 4: Integration & Visualization
- [ ] Web interface for data exploration
- [ ] Machine learning integration examples
- [ ] Advanced visualization tools
- [ ] API for external integrations

## 📞 Support

For questions, issues, or contributions:
- Open an issue on GitHub
- Check the documentation
- Review the examples

---

**Note**: This is a development version. The system is designed to be robust and production-ready, but please test thoroughly in your environment before using for critical applications.
