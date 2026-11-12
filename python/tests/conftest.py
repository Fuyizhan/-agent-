from __future__ import annotations

import atexit
import os
import shutil
import tempfile
from pathlib import Path

TEST_DIR = Path(tempfile.mkdtemp(prefix="contract-review-tests-"))
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{TEST_DIR / 'test.db'}")
os.environ.setdefault("UPLOAD_DIR", str(TEST_DIR / "uploads"))
os.environ.setdefault("JWT_SECRET_KEY", "test-only-jwt-secret-with-at-least-32-characters")
os.environ.setdefault("SEED_ON_STARTUP", "true")
os.environ.setdefault("LLM_PROVIDER", "contract")
os.environ.setdefault("CONTRACT_LLM_API_KEY", "")
os.environ.setdefault("RATE_LIMIT_PER_MINUTE", "1000")

atexit.register(lambda: shutil.rmtree(TEST_DIR, ignore_errors=True))
