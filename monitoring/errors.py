"""Shared error and status vocabulary for the monitoring engine."""
from __future__ import annotations

from enum import Enum


class ErrorCode(str, Enum):
    """Why a check did not produce a healthy result.

    The split matters for alerting: ``fails_check`` codes say something about
    the device or network, while the others say something about *our* setup
    and must never be reported as the device being DOWN.
    """

    TIMEOUT = "TIMEOUT"                  # no answer within timeout/retries
    UNREACHABLE = "UNREACHABLE"          # connection refused / no route
    AUTH_FAILED = "AUTH_FAILED"          # wrong user/key/community, bad digest, decrypt error
    PROTOCOL_ERROR = "PROTOCOL_ERROR"    # agent answered with an SNMP error-status
    UNAVAILABLE = "UNAVAILABLE"          # object not provided by this device
    CONFIG_ERROR = "CONFIG_ERROR"        # our config is invalid
    SECRET_MISSING = "SECRET_MISSING"    # referenced env var is not set
    DEPENDENCY_MISSING = "DEPENDENCY_MISSING"  # e.g. pysnmp not installed
    NOT_ALLOWED = "NOT_ALLOWED"          # target outside allowlist
    LIMIT_EXCEEDED = "LIMIT_EXCEEDED"    # walk results/duration bound hit
    INTERNAL = "INTERNAL"                # unexpected local failure

    @property
    def fails_check(self) -> bool:
        return self in _DEVICE_SIDE


_DEVICE_SIDE = frozenset({
    ErrorCode.TIMEOUT,
    ErrorCode.UNREACHABLE,
    ErrorCode.AUTH_FAILED,
    ErrorCode.PROTOCOL_ERROR,
})


class CheckStatus(str, Enum):
    UP = "UP"
    DOWN = "DOWN"
    UNKNOWN = "UNKNOWN"  # we could not judge (our setup is broken); never alerts as DOWN


class MonitorError(Exception):
    """Exception carrying a classified ErrorCode and a secret-free message."""

    def __init__(self, code: ErrorCode, message: str = ""):
        super().__init__(message or code.value)
        self.code = code
        self.message = message or code.value


def status_for(code: ErrorCode | None) -> CheckStatus:
    if code is None:
        return CheckStatus.UP
    return CheckStatus.DOWN if code.fails_check else CheckStatus.UNKNOWN
