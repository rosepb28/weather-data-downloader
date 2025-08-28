# Weather Data Downloader

[![CI](https://github.com/USERNAME/weather-data-downloader/workflows/CI/badge.svg)](https://github.com/USERNAME/weather-data-downloader/actions/workflows/ci.yml)
[![Release](https://github.com/USERNAME/weather-data-downloader/workflows/Release/badge.svg)](https://github.com/USERNAME/weather-data-downloader/actions/workflows/release.yml)
[![codecov](https://codecov.io/gh/USERNAME/weather-data-downloader/branch/main/graph/badge.svg)](https://codecov.io/gh/USERNAME/weather-data-downloader)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-yellow.svg)](https://conventionalcommits.org)
[![semantic-release](https://img.shields.io/badge/%20%20%F0%9F%93%A6%F0%9F%9A%80-semantic--release-e10079.svg)](https://github.com/semantic-release/semantic-release)

A scalable and robust Python system for downloading numerical weather prediction (NWP) data from various models including GFS, ECMWF, and GEM. Built with SOLID principles, comprehensive testing, and automated CI/CD workflows.

## 🎯 Features

### 🌍 **Multi-Model Support**
- **GFS 0.25°**: Global Forecast System (NOMADS)
- **ECMWF 0.25°**: European Centre for Medium-Range Weather Forecasts
- **GEM 0.1°**: Global Environmental Multiscale model (future)

### 📅 **Flexible Download Options**
- **Date Selection**: Download specific dates or date ranges
- **Cycle Control**: Choose forecast cycles (00Z, 06Z, 12Z, 18Z)
- **Forecast Hours**: Specify exact forecast hours or ranges
- **Forecast Days**: Use `--forecast-days 2` for 48 hours, `--forecast-days 0.5` for 12 hours

### 🗂️ **Data Organization & Processing**
- **Standardized Structure**: `data/model_full_name/date/cycle/{raw|processed|interpolated}/`
- **Dual Output**: Original frequency + Hourly interpolated data
- **Temporal Coordinates**: Standardized `time`, `latitude`, `longitude` dimensions
- **NetCDF Compression**: 6x+ compression ratios with optimized storage
- **Variable Mapping**: Consistent naming across different models

### 🎛️ **Advanced Configuration**
- **Universal Settings**: Spatial bounds, variables, processing options
- **Model-Specific Overrides**: Custom variables, levels, output filenames
- **Spatial Filtering**: Download only specified regions (e.g., South America)
- **Custom File Naming**: Configurable output patterns with date/cycle

### 🔧 **CLI Interface & Operations**
- **Unified Commands**: `download`, `process`, `download-process`, `clean`
- **Consistent Flags**: `-d` (date), `-c` (cycles), `-f` (forecast range)
- **Data Cleanup**: Remove raw/processed/interpolated data by date/cycle
- **Status Monitoring**: Track downloaded data availability

### 🏗️ **Robust Architecture**
- **SOLID Principles**: Modular, extensible design
- **Error Handling**: Retry mechanisms and comprehensive logging
- **Memory Optimization**: Chunked processing and lazy loading
- **Testing**: Unit tests with 85%+ coverage requirement
- **CI/CD**: Automated testing, semantic release, and GitHub Actions

## 🏗️ Architecture

The system follows SOLID principles with a clean, modular architecture:

```
src/
├── core/
│   ├── interfaces/          # Abstract base classes
│   ├── providers/           # Model-specific implementations (GFS, ECMWF, GEM)
│   ├── downloaders/         # HTTP download strategies
│   ├── processors/          # GRIB2→NetCDF processing & interpolation
│   ├── mapping/             # Variable name standardization
│   └── subsetting/          # Spatial & temporal filtering
├── utils/                   # Time management, validation, file operations
├── cli/                     # Command-line interface
└── config/                  # Configuration management
```

## 🚀 Quick Start

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/USERNAME/weather-data-downloader.git
   cd weather-data-downloader
   ```

2. **Install dependencies**:
   ```bash
   poetry install
   ```

3. **Activate the environment**:
   ```bash
   poetry shell
   ```

### Basic Usage

```bash
# Download GFS data for current date, all cycles and forecast hours
wd download gfs

# Download specific date and cycle with processing
wd download gfs -d 20240827 -c 00 --process

# Download 7 days of forecast data
wd download gfs -d 20240827 -c 00 --forecast-days 7

# Process existing raw data (requires -f flag)
wd process gfs -d 20240827 -c 00 -f 0,168

# Combined download and process
wd download-process gfs -d 20240827 -c 00 -f 0,24

# Clean up data
wd clean -m gfs -d 20240827 -c 00 --directory raw   # Remove raw data for specific cycle
wd clean -m gfs -d 20240827 -y                      # Remove all data for date
```

## 📚 CLI Commands

### **`download`** - Download weather data
```bash
wd download <model> [OPTIONS]

Options:
  -d, --date TEXT             Date in YYYYMMDD format (defaults to current UTC date)
  -c, --cycles TEXT           Forecast cycles (e.g., "00,06,12,18")
  -f, --forecast-range TEXT   Forecast hours range (e.g., "0,24", "115,126")
  -e, --end-date TEXT         End date for date ranges
  --forecast-days FLOAT       Number of forecast days (alternative to -f)
  --process                   Process data after download
```

**Examples:**
```bash
wd download gfs -d 20240827 -c 00,06 -f 0,12    # Specific date, cycles, and hours
wd download gfs --forecast-days 2                # Download 2 days (48 hours)
wd download gfs -d 20240827 -c 00 --process     # Download and process
```

### **`process`** - Process downloaded GRIB2 data
```bash
wd process <model> [OPTIONS]

Options:
  -d, --date TEXT           Date in YYYYMMDD format (defaults to current UTC date)
  -c, --cycles TEXT         Forecast cycles to process
  -f, --forecast-range TEXT Forecast hours range (REQUIRED)
```

**Examples:**
```bash
wd process gfs -d 20240827 -c 00 -f 0,24        # Process specific range
wd process gfs -c 00 -f 0,168                   # Process 7 days for current date
```

### **`download-process`** - Combined download and process
```bash
wd download-process <model> [OPTIONS]
# Same options as download command
```

### **`clean`** - Remove data
```bash
wd clean [OPTIONS]

Options:
  -m, --model TEXT         Weather model (e.g., gfs) [REQUIRED]
  -d, --date TEXT          Date in YYYYMMDD format [REQUIRED]
  -c, --cycles TEXT        Forecast cycles to clean (e.g., "00,06,12,18")
  --directory [raw|processed|interpolated]  Specific directory type to clean
  -y, --confirm            Skip confirmation prompt
```

**Examples:**
```bash
wd clean -m gfs -d 20240827                     # Delete everything under gfs.0p25/20240827/
wd clean -m gfs -d 20240827 -c 00               # Delete everything under gfs.0p25/20240827/00/
wd clean -m gfs -d 20240827 -c 00 --directory raw  # Delete only raw data for specific cycle
```

### **`list-models`** - Show available models
```bash
wd list-models                                   # Display all configured models
```

## ⚙️ Configuration

### **Universal Configuration** (`config.yaml`)
```yaml
# Universal settings (apply to all models)
output_dir: "data"
spatial_bounds:
  min_lat: -60.0
  max_lat: 15.0
  min_lon: -90.0
  max_lon: -30.0

processing:
  compression_level: 6
  chunking: true

download:
  max_retries: 3
  timeout: 300

# Model-specific overrides
models:
  gfs:
    variables: ["t2m", "rh2m", "u10m", "v10m", "hgt"]
    levels: ["surface", "2m", "10m"]
    out_file: "gfs.0p25"
```

### **Model Technical Configuration** (`models_config.yaml`)
```yaml
models:
  gfs:
    full_name: "gfs.0p25"
    description: "GFS 0.25 Degree"
    resolution: "0.25°"
    base_url: "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25_1hr.pl"
    available_cycles: [0, 6, 12, 18]
    max_forecast_hours: 384
    cycle_forecast_ranges:
      0: [[0, 120, 1], [123, 384, 3]]   # 0-120h every 1h, 123-384h every 3h
      6: [[0, 120, 1], [123, 384, 3]]
      12: [[0, 120, 1], [123, 384, 3]]
      18: [[0, 120, 1], [123, 384, 3]]
```

### **Variable Mapping** (`variables_mapping.yaml`)
```yaml
# Standardize variable names across models
standard_variables:
  t2m: "2-meter temperature"
  rh2m: "2-meter relative humidity"
  u10m: "10-meter U wind component"
  v10m: "10-meter V wind component"
  hgt: "Surface height"

# Model-specific mappings
models:
  gfs:
    t2m: "TMP"
    rh2m: "RH"
    u10m: "UGRD"
    v10m: "VGRD"
    hgt: "HGT"
```

## 📁 Data Organization

```
data/
└── gfs.0p25/                    # Full model name
    └── 20240827/                # Date (YYYYMMDD)
        └── 00/                  # Cycle (HH)
            ├── raw/             # Original GRIB2 files
            │   ├── gfs.t00z.pgrb2.0p25.f000
            │   ├── gfs.t00z.pgrb2.0p25.f001
            │   └── ...
            ├── processed/       # NetCDF at original frequency
            │   └── gfs.0p25.20240827.00z.nc
            └── interpolated/    # NetCDF with hourly interpolation
                └── gfs.0p25.20240827.00z.nc
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Run all tests with coverage
poetry run pytest --cov=src --cov-report=html

# Run specific test categories
poetry run pytest -m unit                        # Unit tests only
poetry run pytest -m integration                 # Integration tests only
poetry run pytest tests/unit/cli/                # CLI tests

# Run with coverage requirement (85%+)
poetry run pytest --cov=src --cov-fail-under=85
```

## 🔄 Development Workflow

### **Git Branching Strategy**
- `main`: Stable releases only
- `develop`: Active development
- `feature/*`: New features and bug fixes

### **Conventional Commits**
Use structured commit messages:
```bash
feat: add ECMWF provider support
fix: resolve temporal coordinate issue in GRIB processor
docs: update CLI usage examples
test: add unit tests for variable mapping
```

### **Pre-commit Hooks**
```bash
# Install pre-commit hooks
poetry run pre-commit install

# Run manually
poetry run pre-commit run --all-files
```

### **Interactive Commits**
```bash
# Use commitizen for guided commits
poetry run cz commit
```

## 🚀 Contributing

1. **Fork and Clone**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/weather-data-downloader.git
   cd weather-data-downloader
   ```

2. **Create Feature Branch**:
   ```bash
   git checkout develop
   git checkout -b feature/your-feature-name
   ```

3. **Install Development Dependencies**:
   ```bash
   poetry install --with dev,test
   ```

4. **Make Changes and Test**:
   ```bash
   poetry run pytest --cov=src --cov-fail-under=85
   poetry run flake8 src/
   ```

5. **Commit with Conventional Commits**:
   ```bash
   poetry run cz commit
   ```

6. **Push and Create PR**:
   ```bash
   git push origin feature/your-feature-name
   # Create pull request to develop branch
   ```

## 📈 Current Status

### ✅ **Completed Features**
- [x] **GFS 0.25° Provider**: Full NOMADS integration with dynamic configuration
- [x] **Robust Data Processing**: GRIB2 → NetCDF with temporal interpolation (3h/6h → 1h)
- [x] **Comprehensive CLI**: Unified commands with consistent flag order (-d, -c, -f)
- [x] **Flexible Data Management**: Advanced `clean` command (by model/date/cycle/type)
- [x] **Configuration System**: Universal + model-specific settings with YAML
- [x] **Variable Standardization**: Consistent naming across different models
- [x] **Spatial Subsetting**: Regional data extraction (e.g., South America)
- [x] **Storage Optimization**: NetCDF compression (6x+ ratios) with chunking
- [x] **Coordinate Standards**: Consistent `time`, `latitude`, `longitude` dimensions
- [x] **Testing Framework**: Unit tests with 85%+ coverage requirement
- [x] **Automated CI/CD**: GitHub Actions, semantic release, pre-commit hooks
- [x] **Production Ready**: Error handling, retry mechanisms, comprehensive logging

### 🎯 **Project Status: COMPLETED** ✅
The weather data downloader system is **fully functional and production-ready**! 
All core requirements have been successfully implemented and tested.

### 🔮 **Future Enhancements** (Next Projects)
- [ ] Status command implementation (minor addition)
- [ ] ECMWF and GEM provider development
- [ ] Advanced interpolation and variable calculation algorithms

### 🎯 **Future Roadmap**
- [ ] **Visualization Interface**: Interactive web/desktop app for data exploration
- [ ] **Machine Learning Pipeline**: Model training on downloaded datasets
- [ ] **Real-time Monitoring**: Automated downloads with scheduling
- [ ] **Cloud Storage**: Support for S3, GCS, and other cloud backends
- [ ] **Performance Optimization**: Async downloads and parallel processing

## 📊 Example Output

### **Successful Download & Processing (7 Days)**
```bash
$ wd download-process gfs -d 20250827 -c 12 -f 0,168

📋 Download Plan:
   Model: gfs (gfs.0p25)
   Date: 20250827
   Cycles: 12
   Forecast Hours: 0-168 (137 files)

✅ Download completed: 137 files (561.7 MB)

📊 Processing 137 GRIB2 files → NetCDF
🔄 Standardizing coordinate names and dimension order
✅ Spatial subsetting: 721×1440 → 301×241 (South America)
📊 Combined dataset with dimensions: {'latitude': 301, 'longitude': 241, 'time': 137}
✅ Saved original data: gfs.0p25.20250827.12z.nc (86.8 MB)
✅ Interpolated from 137 to 169 time steps (hourly)
✅ Saved interpolated data: gfs.0p25.20250827.12z.nc (134.3 MB)
📦 Compression: 561.7 MB → 86.8 MB (ratio: 6.47x)

🎉 Processing completed successfully!
```

### **Data Verification**
```python
import xarray as xr

# Load processed data (7 days of forecast)
ds = xr.open_dataset('data/gfs.0p25/20250827/12/interpolated/gfs.0p25.20250827.12z.nc')

print(f"Dimensions: {dict(ds.dims)}")
# Dimensions: {'time': 169, 'latitude': 301, 'longitude': 241}

print(f"Variables: {list(ds.data_vars.keys())}")
# Variables: ['t2m', 'rh2m', 'u10m', 'v10m', 'hgt']

print(f"Time range: {ds.time.values[0]} to {ds.time.values[-1]}")
# Time range: 2025-08-27T12:00:00 to 2025-09-03T12:00:00

print(f"Coordinate order: {list(ds.dims)}")
# Coordinate order: ['time', 'latitude', 'longitude']

print(f"Total hours: {len(ds.time)} (7 days fully interpolated)")
# Total hours: 169 (7 days fully interpolated)
```

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **NOAA/NOMADS**: For providing free access to GFS data
- **ECMWF**: For numerical weather prediction data
- **Environment Canada**: For GEM model data
- **xarray/cfgrib**: For excellent NetCDF and GRIB handling libraries

---

**Built with ❤️ for the meteorological and data science communities**