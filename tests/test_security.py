"""
Security-focused tests for nnt-nnh-confidence-interval-engine.
"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from agents.base import (
    PHIGuard,
    AuditLogger,
    SecurityException,
    AuditTrail,
    assert_no_phi,
)


class TestPHIGuard:
    """Tests for the PHI outbound guard functionality."""

    def test_mrn_pattern_detected(self):
        with pytest.raises(SecurityException):
            PHIGuard.assert_no_phi("Patient MRN-994827 blood culture positive")

    def test_ssn_pattern_detected(self):
        with pytest.raises(SecurityException):
            PHIGuard.assert_no_phi("SSN: 123-45-6789")

    def test_phone_number_detected(self):
        with pytest.raises(SecurityException):
            PHIGuard.assert_no_phi("Contact patient at 555-123-4567")

    def test_email_detected(self):
        with pytest.raises(SecurityException):
            PHIGuard.assert_no_phi("Send results to doctor@hospital.org")

    def test_dob_detected(self):
        with pytest.raises(SecurityException):
            PHIGuard.assert_no_phi("DOB: 01/15/1985")

    def test_patient_name_detected(self):
        with pytest.raises(SecurityException):
            PHIGuard.assert_no_phi("Patient John Doe admitted")

    def test_jane_smith_detected(self):
        with pytest.raises(SecurityException):
            PHIGuard.assert_no_phi("Jane Smith lab results ready")

    def test_clean_text_passes(self):
        """Non-PHI text should pass without exception."""
        PHIGuard.assert_no_phi("Analytical assay specimen KEY-001 optimal")
        PHIGuard.assert_no_phi("Target SPECIMEN-ALPHA-77 processed")
        PHIGuard.assert_no_phi("Status: NOMINAL")

    def test_empty_string_passes(self):
        """Empty string should pass without exception."""
        PHIGuard.assert_no_phi("")

    def test_none_handled_gracefully(self):
        """None input should be handled gracefully."""
        assert_no_phi(None)

    def test_redact_phi(self):
        """Test PHI redaction functionality."""
        text = "Patient MRN-994827 and SSN 123-45-6789"
        redacted = PHIGuard.redact_phi(text)
        assert "MRN-994827" not in redacted
        assert "123-45-6789" not in redacted
        assert "[REDACTED_IDENTIFIER]" in redacted


class TestAuditTrail:
    """Tests for the HMAC-SHA256 audit trail."""

    def test_audit_trail_requires_secret_key(self):
        """AuditTrail should raise error without secret key."""
        original_key = os.environ.pop("AUDIT_SECRET_KEY", None)
        AuditLogger.reset()
        try:
            with pytest.raises(RuntimeError, match="AUDIT_SECRET_KEY"):
                AuditTrail()
        finally:
            if original_key:
                os.environ["AUDIT_SECRET_KEY"] = original_key
            AuditLogger.reset()

    def test_audit_trail_with_explicit_key(self):
        """AuditTrail should work with explicitly provided key."""
        trail = AuditTrail(secret_key="test-key-12345")
        entry = trail.log("test_actor", "test_tier", "TEST_EVENT", {"detail": "value"})
        assert "current_hash" in entry
        assert "audit_id" in entry

    def test_audit_trail_integrity(self):
        """Audit trail should maintain integrity across multiple entries."""
        trail = AuditTrail(secret_key="integrity-test-key")
        trail.log("actor1", "tier1", "EVENT_1", {"seq": 1})
        trail.log("actor2", "tier2", "EVENT_2", {"seq": 2})
        trail.log("actor3", "tier3", "EVENT_3", {"seq": 3})
        assert trail.verify_integrity() is True
        assert len(trail.get_trail()) == 3

    def test_audit_trail_tamper_detection(self):
        """Tampered entries should fail integrity check."""
        trail = AuditTrail(secret_key="tamper-test-key")
        trail.log("actor1", "tier1", "EVENT_1", {"seq": 1})
        trail.log("actor2", "tier2", "EVENT_2", {"seq": 2})
        # Tamper with the first entry
        trail.logs[0]["current_hash"] = "TAMPERED_HASH"
        assert trail.verify_integrity() is False

    def test_audit_log_blocks_phi(self):
        """Audit logging should reject PHI-containing payloads."""
        trail = AuditTrail(secret_key="phi-test-key")
        with pytest.raises(SecurityException):
            trail.log("actor", "tier", "EVENT", {"patient": "MRN-12345"})


class TestInputValidation:
    """Count and interval validation, not arbitrary clinical severity labels."""

    def test_invalid_counts_raise(self):
        from nnt_calc import calculate_metrics
        for args in [(-1, 10, 0, 10), (11, 10, 0, 10), (0, 0, 0, 10)]:
            with pytest.raises(ValueError):
                calculate_metrics(*args)

    def test_zero_difference_is_not_a_zero_nnt(self):
        from nnt_calc import calculate_metrics
        result = calculate_metrics(0, 10, 0, 10)
        assert result["number_needed"] is None
        assert result["measure"] == "no_difference"

    def test_clinically_neutral_example(self):
        from nnt_calc import calculate_metrics
        result = calculate_metrics(12, 100, 8, 100)
        assert result["measure"] == "NNT"
        assert result["absolute_risk_reduction"] == pytest.approx(0.04)
