class ReturnError(Exception):
    """Base exception for the returns and RMA domain."""

    pass


class ReturnPolicyViolation(ReturnError):
    """Raised when a return violates return policy (e.g. return window expired, invalid status)."""

    pass


class ReturnConflict(ReturnError):
    """Raised when an invalid state transition or conflict occurs in returns workflow."""

    pass


class ReturnPermissionDenied(ReturnError):
    """Raised when a user attempts an unauthorized RMA operation or IDOR violation."""

    pass
