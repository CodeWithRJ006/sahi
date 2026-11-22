"""Pytest test suite configuration and fixtures for SAHI."""

import pytest
import tempfile
import os
import gc

@pytest.fixture
def temp_db_path():
    """Provides a temporary SQLite database file path cleaned up after test."""
    fd, path = tempfile.mkstemp(suffix=".sqlite3")
    os.close(fd)
    yield path
    # Force garbage collection to release any unclosed sqlite handles on Windows
    gc.collect()
    try:
        if os.path.exists(path):
            os.remove(path)
    except PermissionError:
        pass
