"""
Tests for Core Storage Service

Run with: pytest apps/core/services/storage/tests/ -v
"""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from ..backends import LocalStorageBackend, ProjectStorage, create_backend
from ..exceptions import FileNotFoundError, FileSizeError, InvalidExtensionError, StorageException
from ..models import (
    FileMetadata,
    ProjectStructure,
    StorageBackend,
    StorageConfig,
    calculate_checksum,
    generate_file_path,
    validate_file_extension,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def local_storage(temp_dir):
    """Create local storage backend for tests."""
    return LocalStorageBackend(
        StorageConfig(base_path=str(temp_dir), max_file_size=1024 * 1024)  # 1MB
    )


@pytest.fixture
def project_storage(temp_dir):
    """Create project storage for tests."""
    return ProjectStorage("test-project", base_path=str(temp_dir))


# =============================================================================
# Model Tests
# =============================================================================


class TestStorageConfig:
    def test_default_values(self):
        config = StorageConfig()
        assert config.backend == StorageBackend.LOCAL
        assert config.auto_create_dirs is True

    def test_custom_values(self):
        config = StorageConfig(backend=StorageBackend.S3, bucket_name="my-bucket")
        assert config.backend == StorageBackend.S3
        assert config.bucket_name == "my-bucket"


class TestFileMetadata:
    def test_from_path(self, temp_dir):
        # Create test file
        test_file = temp_dir / "test.txt"
        test_file.write_text("Hello World")

        metadata = FileMetadata.from_path(test_file, relative_to=temp_dir)

        assert metadata.filename == "test.txt"
        assert metadata.size_bytes == 11
        assert metadata.extension == ".txt"


class TestProjectStructure:
    def test_paths(self, temp_dir):
        structure = ProjectStructure("my-project", temp_dir)

        assert structure.root == temp_dir / "my-project"
        assert structure.chapters == temp_dir / "my-project" / "chapters"
        assert structure.exports == temp_dir / "my-project" / "exports"

    def test_chapter_file(self, temp_dir):
        structure = ProjectStructure("my-project", temp_dir)

        path = structure.chapter_file(1)
        assert path.name == "chapter_01.md"

        path_v2 = structure.chapter_file(1, version=2)
        assert path_v2.name == "chapter_01_v2.md"


class TestHelperFunctions:
    def test_generate_file_path(self):
        path = generate_file_path("photo.jpg", prefix="uploads")
        assert path.startswith("uploads/")
        assert path.endswith(".jpg")

    def test_validate_file_extension(self):
        assert validate_file_extension("doc.pdf", allowed=["pdf", "docx"]) is True
        assert validate_file_extension("doc.exe", allowed=["pdf", "docx"]) is False
        assert validate_file_extension("doc.exe", blocked=["exe"]) is False

    def test_calculate_checksum(self, temp_dir):
        test_file = temp_dir / "test.txt"
        test_file.write_text("Hello")

        checksum = calculate_checksum(test_file)
        assert len(checksum) == 32  # MD5 hex length


# =============================================================================
# Local Storage Backend Tests
# =============================================================================


class TestLocalStorageBackend:
    def test_write_and_read(self, local_storage):
        local_storage.write("test.txt", "Hello World")
        content = local_storage.read_text("test.txt")
        assert content == "Hello World"

    def test_write_bytes(self, local_storage):
        local_storage.write("binary.bin", b"\x00\x01\x02\x03")
        content = local_storage.read("binary.bin")
        assert content == b"\x00\x01\x02\x03"

    def test_write_json(self, local_storage):
        data = {"key": "value", "number": 42}
        local_storage.write_json("data.json", data)
        result = local_storage.read_json("data.json")
        assert result == data

    def test_delete(self, local_storage):
        local_storage.write("delete_me.txt", "content")
        assert local_storage.exists("delete_me.txt")

        local_storage.delete("delete_me.txt")
        assert not local_storage.exists("delete_me.txt")

    def test_delete_missing_ok(self, local_storage):
        # Should not raise
        local_storage.delete("nonexistent.txt", missing_ok=True)

    def test_delete_missing_error(self, local_storage):
        with pytest.raises(FileNotFoundError):
            local_storage.delete("nonexistent.txt")

    def test_exists(self, local_storage):
        assert not local_storage.exists("test.txt")
        local_storage.write("test.txt", "content")
        assert local_storage.exists("test.txt")

    def test_list(self, local_storage):
        local_storage.write("file1.txt", "1")
        local_storage.write("file2.txt", "2")
        local_storage.write("subdir/file3.txt", "3")

        files = local_storage.list()
        assert "file1.txt" in files
        assert "file2.txt" in files

    def test_copy(self, local_storage):
        local_storage.write("original.txt", "content")
        local_storage.copy("original.txt", "copy.txt")

        assert local_storage.exists("original.txt")
        assert local_storage.exists("copy.txt")
        assert local_storage.read_text("copy.txt") == "content"

    def test_move(self, local_storage):
        local_storage.write("source.txt", "content")
        local_storage.move("source.txt", "dest.txt")

        assert not local_storage.exists("source.txt")
        assert local_storage.exists("dest.txt")

    def test_metadata(self, local_storage):
        local_storage.write("test.txt", "Hello World")
        metadata = local_storage.get_metadata("test.txt")

        assert metadata.filename == "test.txt"
        assert metadata.size_bytes == 11

    def test_auto_create_dirs(self, local_storage):
        local_storage.write("deep/nested/path/file.txt", "content")
        assert local_storage.exists("deep/nested/path/file.txt")

    def test_file_size_limit(self, local_storage):
        # Create content larger than 1MB limit
        large_content = "x" * (2 * 1024 * 1024)

        with pytest.raises(FileSizeError):
            local_storage.write("large.txt", large_content)

    def test_extension_validation(self, temp_dir):
        storage = LocalStorageBackend(
            StorageConfig(base_path=str(temp_dir), allowed_extensions=["txt", "md"])
        )

        storage.write("doc.txt", "content")  # OK

        with pytest.raises(InvalidExtensionError):
            storage.write("doc.exe", "content")

    def test_health_check(self, local_storage):
        assert local_storage.health_check() is True


# =============================================================================
# Project Storage Tests
# =============================================================================


class TestProjectStorage:
    def test_save_and_load_chapter(self, project_storage):
        project_storage.save_chapter(1, "Chapter 1 content")
        content = project_storage.load_chapter(1)
        assert content == "Chapter 1 content"

    def test_chapter_with_metadata(self, project_storage):
        metadata = {"title": "The Beginning", "word_count": 100}
        project_storage.save_chapter(1, "Content", metadata=metadata)

        content = project_storage.load_chapter(1)
        assert "title: The Beginning" in content
        assert "Content" in content

    def test_chapter_versioning(self, project_storage):
        project_storage.save_chapter(1, "Version 1", version=1)
        project_storage.save_chapter(1, "Version 2", version=2)

        assert project_storage.load_chapter(1, version=1) is not None
        assert project_storage.load_chapter(1, version=2) is not None

    def test_chapter_exists(self, project_storage):
        assert not project_storage.chapter_exists(1)
        project_storage.save_chapter(1, "content")
        assert project_storage.chapter_exists(1)

    def test_list_chapters(self, project_storage):
        project_storage.save_chapter(1, "Chapter 1")
        project_storage.save_chapter(3, "Chapter 3")
        project_storage.save_chapter(2, "Chapter 2")

        chapters = project_storage.list_chapters()
        assert chapters == [1, 2, 3]

    def test_save_and_load_character(self, project_storage):
        character_data = {"name": "John", "age": 35, "traits": ["brave", "curious"]}
        project_storage.save_character("protagonist", character_data)

        loaded = project_storage.load_character("protagonist")
        assert loaded["name"] == "John"
        assert loaded["age"] == 35

    def test_save_and_load_metadata(self, project_storage):
        metadata = {"title": "My Novel", "genre": "Fiction"}
        project_storage.save_metadata(metadata)

        loaded = project_storage.load_metadata()
        assert loaded["title"] == "My Novel"


# =============================================================================
# Backend Factory Tests
# =============================================================================


class TestCreateBackend:
    def test_create_local(self, temp_dir):
        backend = create_backend(StorageBackend.LOCAL, StorageConfig(base_path=str(temp_dir)))
        assert isinstance(backend, LocalStorageBackend)

    def test_invalid_backend(self):
        with pytest.raises(ValueError):
            create_backend("invalid", StorageConfig())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
