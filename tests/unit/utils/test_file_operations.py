"""
Unit tests for file operations utilities.

Tests file management, validation, and utility functions.
"""

import pytest
import hashlib
from pathlib import Path
from unittest.mock import patch, mock_open

from src.utils.file_operations import FileOperations


class TestFileOperations:
    """Test FileOperations functionality"""
    
    def test_ensure_directory_creates_new(self, tmp_path):
        """Test creating new directory"""
        new_dir = tmp_path / "new_directory"
        assert not new_dir.exists()
        
        result = FileOperations.ensure_directory(new_dir)
        
        assert new_dir.exists()
        assert new_dir.is_dir()
        assert result == new_dir
    
    def test_ensure_directory_existing(self, tmp_path):
        """Test ensuring existing directory"""
        existing_dir = tmp_path / "existing"
        existing_dir.mkdir()
        
        result = FileOperations.ensure_directory(existing_dir)
        
        assert existing_dir.exists()
        assert result == existing_dir
    
    def test_ensure_directory_with_parents(self, tmp_path):
        """Test creating nested directories"""
        nested_dir = tmp_path / "parent" / "child" / "grandchild"
        
        result = FileOperations.ensure_directory(nested_dir)
        
        assert nested_dir.exists()
        assert nested_dir.is_dir()
        assert result == nested_dir
    
    def test_safe_remove_file(self, tmp_path):
        """Test safely removing a file"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        assert test_file.exists()
        
        result = FileOperations.safe_remove(test_file)
        
        assert result is True
        assert not test_file.exists()
    
    def test_safe_remove_directory(self, tmp_path):
        """Test safely removing a directory"""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        (test_dir / "file.txt").write_text("content")
        assert test_dir.exists()
        
        result = FileOperations.safe_remove(test_dir)
        
        assert result is True
        assert not test_dir.exists()
    
    def test_safe_remove_nonexistent(self, tmp_path):
        """Test removing non-existent path"""
        nonexistent = tmp_path / "does_not_exist"
        
        result = FileOperations.safe_remove(nonexistent)
        
        # Function returns True even for non-existent paths (not an error)
        assert result is True
    
    def test_get_file_size_existing(self, tmp_path):
        """Test getting size of existing file"""
        test_file = tmp_path / "test.txt"
        content = "test content"
        test_file.write_text(content)
        
        result = FileOperations.get_file_size(test_file)
        
        assert result == len(content.encode())
    
    def test_get_file_size_nonexistent(self, tmp_path):
        """Test getting size of non-existent file"""
        nonexistent = tmp_path / "does_not_exist.txt"
        
        result = FileOperations.get_file_size(nonexistent)
        
        assert result is None
    
    def test_calculate_file_hash_md5(self, tmp_path):
        """Test calculating MD5 hash"""
        test_file = tmp_path / "test.txt"
        content = "test content"
        test_file.write_text(content)
        
        expected_hash = hashlib.md5(content.encode()).hexdigest()
        result = FileOperations.calculate_file_hash(test_file, "md5")
        
        assert result == expected_hash
    
    def test_calculate_file_hash_sha256(self, tmp_path):
        """Test calculating SHA256 hash"""
        test_file = tmp_path / "test.txt"
        content = "test content"
        test_file.write_text(content)
        
        expected_hash = hashlib.sha256(content.encode()).hexdigest()
        result = FileOperations.calculate_file_hash(test_file, "sha256")
        
        assert result == expected_hash
    
    def test_calculate_file_hash_nonexistent(self, tmp_path):
        """Test hash of non-existent file"""
        nonexistent = tmp_path / "does_not_exist.txt"
        
        result = FileOperations.calculate_file_hash(nonexistent)
        
        assert result is None
    
    def test_calculate_file_hash_invalid_algorithm(self, tmp_path):
        """Test invalid hash algorithm"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        
        result = FileOperations.calculate_file_hash(test_file, "invalid_algo")
        
        assert result is None
    
    @pytest.mark.parametrize("filename,expected", [
        ("file.txt", ".txt"),
        ("data.nc", ".nc"),
        ("archive.tar.gz", ".gz"),
        ("no_extension", ""),
        (".hidden", ""),
        ("file.multiple.ext", ".ext"),
    ])
    def test_get_file_extension(self, filename, expected):
        """Test getting file extensions"""
        path = Path(filename)
        result = FileOperations.get_file_extension(path)
        assert result == expected
    
    @pytest.mark.parametrize("filename,expected", [
        ("data.nc", True),
        ("model.netcdf", True),
        ("file.txt", False),
        ("data.grib", False),
        ("data.NC", True),  # Case insensitive
    ])
    def test_is_netcdf_file(self, filename, expected):
        """Test NetCDF file detection"""
        path = Path(filename)
        result = FileOperations.is_netcdf_file(path)
        assert result == expected
    
    def test_backup_file_success(self, tmp_path):
        """Test successful file backup"""
        original = tmp_path / "original.txt"
        content = "original content"
        original.write_text(content)
        
        backup_path = FileOperations.backup_file(original)
        
        assert backup_path is not None
        assert backup_path.exists()
        assert backup_path.read_text() == content
        assert backup_path.name == "original.txt.backup"
    
    def test_backup_file_custom_suffix(self, tmp_path):
        """Test backup with custom suffix"""
        original = tmp_path / "original.txt"
        original.write_text("content")
        
        backup_path = FileOperations.backup_file(original, ".old")
        
        assert backup_path is not None
        assert backup_path.name == "original.txt.old"
    
    def test_backup_file_nonexistent(self, tmp_path):
        """Test backup of non-existent file"""
        nonexistent = tmp_path / "does_not_exist.txt"
        
        result = FileOperations.backup_file(nonexistent)
        
        assert result is None
    
    def test_get_disk_usage_valid_path(self, tmp_path):
        """Test getting disk usage for valid path"""
        result = FileOperations.get_disk_usage(tmp_path)
        
        assert result is not None
        assert isinstance(result, int)
        assert result >= 0
    
    def test_get_disk_usage_invalid_path(self):
        """Test getting disk usage for invalid path"""
        invalid_path = Path("/nonexistent/path/that/does/not/exist")
        
        result = FileOperations.get_disk_usage(invalid_path)
        
        assert result is None


class TestFileOperationsEdgeCases:
    """Test edge cases and error conditions"""
    
    @patch('src.utils.file_operations.shutil.rmtree')
    def test_safe_remove_permission_error(self, mock_rmtree, tmp_path):
        """Test safe remove with permission error"""
        mock_rmtree.side_effect = PermissionError("Access denied")
        
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        
        result = FileOperations.safe_remove(test_dir)
        
        assert result is False
    
    @patch('src.utils.file_operations.Path.unlink')
    def test_safe_remove_file_error(self, mock_unlink, tmp_path):
        """Test safe remove file with error"""
        mock_unlink.side_effect = OSError("Cannot remove")
        
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        
        result = FileOperations.safe_remove(test_file)
        
        assert result is False
    
    @patch('builtins.open', side_effect=IOError("Cannot read file"))
    def test_calculate_hash_io_error(self, mock_open_func, tmp_path):
        """Test hash calculation with IO error"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        
        result = FileOperations.calculate_file_hash(test_file)
        
        assert result is None
    
    @patch('src.utils.file_operations.shutil.copy2')
    def test_backup_file_copy_error(self, mock_copy, tmp_path):
        """Test backup with copy error"""
        mock_copy.side_effect = OSError("Cannot copy")
        
        original = tmp_path / "original.txt"
        original.write_text("content")
        
        result = FileOperations.backup_file(original)
        
        assert result is None
    
    @patch('src.utils.file_operations.shutil.disk_usage')
    def test_get_disk_usage_error(self, mock_disk_usage, tmp_path):
        """Test disk usage with error"""
        mock_disk_usage.side_effect = OSError("Cannot get usage")
        
        result = FileOperations.get_disk_usage(tmp_path)
        
        assert result is None


class TestFileOperationsIntegration:
    """Test integration scenarios"""
    
    def test_full_file_workflow(self, tmp_path):
        """Test complete file operation workflow"""
        # 1. Create directory
        work_dir = tmp_path / "work"
        FileOperations.ensure_directory(work_dir)
        assert work_dir.exists()
        
        # 2. Create file
        test_file = work_dir / "data.nc"
        content = "NetCDF file content"
        test_file.write_text(content)
        
        # 3. Check file properties
        assert FileOperations.is_netcdf_file(test_file)
        assert FileOperations.get_file_extension(test_file) == ".nc"
        assert FileOperations.get_file_size(test_file) == len(content.encode())
        
        # 4. Calculate hash
        file_hash = FileOperations.calculate_file_hash(test_file)
        assert file_hash is not None
        
        # 5. Create backup
        backup_path = FileOperations.backup_file(test_file)
        assert backup_path is not None
        assert backup_path.exists()
        
        # 6. Clean up
        assert FileOperations.safe_remove(backup_path)
        assert FileOperations.safe_remove(test_file)
        assert FileOperations.safe_remove(work_dir)
    
    def test_nested_directory_operations(self, tmp_path):
        """Test operations with nested directories"""
        # Create nested structure
        nested = tmp_path / "level1" / "level2" / "level3"
        FileOperations.ensure_directory(nested)
        
        # Add files at different levels
        (tmp_path / "level1" / "file1.txt").write_text("content1")
        (nested / "file2.txt").write_text("content2")
        
        # Verify structure
        assert nested.exists()
        assert (tmp_path / "level1" / "file1.txt").exists()
        assert (nested / "file2.txt").exists()
        
        # Clean up from root
        result = FileOperations.safe_remove(tmp_path / "level1")
        assert result is True
        assert not (tmp_path / "level1").exists()
    
    def test_file_operations_with_different_types(self, tmp_path):
        """Test operations with different file types"""
        file_types = [
            ("text.txt", "text content"),
            ("data.nc", "netcdf data"),
            ("archive.tar.gz", "archive content"),
            ("script.py", "python code"),
        ]
        
        for filename, content in file_types:
            file_path = tmp_path / filename
            file_path.write_text(content)
            
            # Test operations
            assert FileOperations.get_file_size(file_path) == len(content.encode())
            assert FileOperations.calculate_file_hash(file_path) is not None
            
            # Test NetCDF detection
            expected_netcdf = filename.endswith(('.nc', '.netcdf'))
            assert FileOperations.is_netcdf_file(file_path) == expected_netcdf
            
            # Test backup
            backup = FileOperations.backup_file(file_path)
            assert backup is not None
            assert backup.exists()
            
            # Cleanup
            FileOperations.safe_remove(backup)
            FileOperations.safe_remove(file_path)
