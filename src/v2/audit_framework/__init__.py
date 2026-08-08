"""
Nova Star Capital Audit Framework.

This framework provides a provider-independent institutional audit
pipeline for certified Nova Star Capital releases and baselines.
"""

from .core.constants import (
    AUDIT_FRAMEWORK_NAME,
    AUDIT_FRAMEWORK_VERSION,
    AUDIT_FRAMEWORK_SCHEMA_VERSION,
)

__all__ = [
    "AUDIT_FRAMEWORK_NAME",
    "AUDIT_FRAMEWORK_VERSION",
    "AUDIT_FRAMEWORK_SCHEMA_VERSION",
]
