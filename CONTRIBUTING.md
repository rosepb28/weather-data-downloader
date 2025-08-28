# Contributing to Weather Data Downloader

## Conventional Commits

This project uses [Conventional Commits](https://conventionalcommits.org/) for automatic versioning and changelog generation.

### Commit Message Format

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Types

- **feat**: A new feature
- **fix**: A bug fix
- **docs**: Documentation only changes
- **style**: Changes that do not affect the meaning of the code
- **refactor**: A code change that neither fixes a bug nor adds a feature
- **perf**: A code change that improves performance
- **test**: Adding missing tests or correcting existing tests
- **build**: Changes that affect the build system or external dependencies
- **ci**: Changes to our CI configuration files and scripts
- **chore**: Other changes that don't modify src or test files

### Examples

```bash
feat: add ECMWF data provider support
fix: resolve GRIB loading conflict with mixed levels
docs: update CLI examples in README
test: add unit tests for GFS provider
ci: setup semantic release workflow
perf: optimize NetCDF compression settings
refactor: simplify variable mapping logic
```

### Using Commitizen

For interactive commit creation:

```bash
poetry run cz commit
```

### Development Setup

1. Install pre-commit hooks:
```bash
poetry run pre-commit install
```

2. Run tests:
```bash
poetry run pytest
```

3. Check linting:
```bash
poetry run flake8 src/
```
