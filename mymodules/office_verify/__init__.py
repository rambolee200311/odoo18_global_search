"""Independent, bounded OOXML readback verification."""

from .errors import OfficeVerifyError
from .models import CandidateValidationReport, VerificationBudget, VerificationPolicy, VerificationReport
from .service import verify_candidate_output, verify_candidate_output_with_metrics, verify_created_output_with_metrics, verify_output

__all__ = [
    "OfficeVerifyError",
    "CandidateValidationReport",
    "VerificationBudget",
    "VerificationPolicy",
    "VerificationReport",
    "verify_output",
    "verify_candidate_output",
    "verify_candidate_output_with_metrics",
    "verify_created_output_with_metrics",
]
