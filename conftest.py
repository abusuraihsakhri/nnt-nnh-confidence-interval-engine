"""
Pytest configuration and shared fixtures for nnt-nnh-confidence-interval-engine.
"""
import os
import sys
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).parent))

# Set a deterministic test secret for HMAC audit trail
os.environ.setdefault("AUDIT_SECRET_KEY", "test-secret-key-for-pytest-only-do-not-use-in-production")


import pytest
from agents.base import AuditLogger


@pytest.fixture(autouse=True)
def reset_audit_trail():
    """Reset the global audit trail before each test for isolation."""
    AuditLogger.reset()
    yield
    AuditLogger.reset()
