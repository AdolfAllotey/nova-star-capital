from __future__ import annotations


class AuditFrameworkError(RuntimeError):
    """Base error for the Nova Star Capital Audit Framework."""


class ConfigurationError(AuditFrameworkError):
    """Raised when framework configuration is invalid."""


class ArtifactCollectionError(AuditFrameworkError):
    """Raised when required audit artifacts cannot be collected."""


class BaselineValidationError(AuditFrameworkError):
    """Raised when a release baseline fails integrity validation."""


class ManifestValidationError(AuditFrameworkError):
    """Raised when an audit manifest is invalid."""


class ProviderError(AuditFrameworkError):
    """Raised when an audit provider fails."""


class ReportNormalizationError(AuditFrameworkError):
    """Raised when a provider report cannot be normalized."""
