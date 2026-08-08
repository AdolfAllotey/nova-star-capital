"""
Provider-independent artifact collection.
"""

from .artifact_collector import (
    InstitutionalArtifactCollector,
)
from .artifact_definitions import (
    ArtifactDefinition,
    build_rc1_artifact_definitions,
)
from .collection_models import (
    CollectionIssue,
    CollectionResult,
)

__all__ = [
    "InstitutionalArtifactCollector",
    "ArtifactDefinition",
    "build_rc1_artifact_definitions",
    "CollectionIssue",
    "CollectionResult",
]
