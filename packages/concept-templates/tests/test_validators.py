"""Tests for concept_templates.validators."""

from __future__ import annotations

import pytest

from concept_templates.validators import (
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE_BYTES,
    FileValidationError,
    validate_upload_file,
)


class TestValidateUploadFile:
    def test_should_accept_pdf(self):
        validate_upload_file("doc.pdf", size_bytes=1000)

    def test_should_accept_docx(self):
        validate_upload_file("doc.docx", size_bytes=1000)

    def test_should_accept_dxf(self):
        validate_upload_file("plan.dxf", size_bytes=1000)

    def test_should_accept_dwg(self):
        validate_upload_file("plan.dwg", size_bytes=1000)

    def test_should_accept_jpg(self):
        validate_upload_file("photo.jpg", size_bytes=1000)

    def test_should_accept_png(self):
        validate_upload_file("img.png", size_bytes=1000)

    def test_should_accept_csv(self):
        validate_upload_file("data.csv", size_bytes=100)

    def test_should_reject_exe(self):
        with pytest.raises(FileValidationError, match="nicht erlaubt"):
            validate_upload_file("virus.exe", size_bytes=1000)

    def test_should_reject_zip(self):
        with pytest.raises(FileValidationError, match="nicht erlaubt"):
            validate_upload_file("archive.zip", size_bytes=1000)

    def test_should_reject_py(self):
        with pytest.raises(FileValidationError, match="nicht erlaubt"):
            validate_upload_file("script.py", size_bytes=1000)

    def test_should_reject_no_extension(self):
        with pytest.raises(FileValidationError, match="nicht erlaubt"):
            validate_upload_file("noext", size_bytes=1000)

    def test_should_be_case_insensitive_extension(self):
        validate_upload_file("DOC.PDF", size_bytes=1000)
        validate_upload_file("plan.DXF", size_bytes=1000)

    def test_should_reject_oversized_file(self):
        with pytest.raises(FileValidationError, match="zu groß"):
            validate_upload_file(
                "big.pdf",
                size_bytes=MAX_FILE_SIZE_BYTES + 1,
            )

    def test_should_accept_exactly_max_size(self):
        validate_upload_file("ok.pdf", size_bytes=MAX_FILE_SIZE_BYTES)

    def test_should_accept_valid_mime_type(self):
        validate_upload_file(
            "doc.pdf",
            size_bytes=1000,
            content_type="application/pdf",
        )

    def test_should_warn_on_unexpected_mime(self, caplog):
        validate_upload_file(
            "doc.pdf",
            size_bytes=1000,
            content_type="application/x-shellscript",
        )
        assert "Unexpected MIME type" in caplog.text

    def test_should_not_warn_without_mime(self, caplog):
        validate_upload_file("doc.pdf", size_bytes=1000, content_type="")
        assert "Unexpected MIME type" not in caplog.text


class TestConstants:
    def test_should_have_max_50mb(self):
        assert MAX_FILE_SIZE_BYTES == 50 * 1024 * 1024

    def test_should_include_common_extensions(self):
        for ext in [".pdf", ".docx", ".dxf", ".dwg", ".jpg", ".png"]:
            assert ext in ALLOWED_EXTENSIONS

    def test_should_be_frozen(self):
        assert isinstance(ALLOWED_EXTENSIONS, frozenset)
