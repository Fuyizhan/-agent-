from __future__ import annotations

import pytest

from src.api.upload_guard import UploadValidationError, sanitize_filename, validate_upload


def test_sanitize_filename_blocks_paths():
    assert sanitize_filename("../../contract.txt") == "contract.txt"


def test_accepts_utf8_text():
    assert validate_upload("contract.txt", "合同正文".encode("utf-8")) == "contract.txt"


def test_rejects_disguised_pdf():
    with pytest.raises(UploadValidationError):
        validate_upload("contract.pdf", b"not a pdf")


def test_rejects_unknown_extension():
    with pytest.raises(UploadValidationError):
        validate_upload("contract.exe", b"binary")
