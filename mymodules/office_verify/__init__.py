"""Independent, bounded OOXML readback verification."""

from .errors import OfficeVerifyError
from .models import VerificationBudget, VerificationPolicy, VerificationReport
from .service import verify_output

__all__ = [
    "OfficeVerifyError",
    "VerificationBudget",
    "VerificationPolicy",
    "VerificationReport",
    "verify_output",
]
