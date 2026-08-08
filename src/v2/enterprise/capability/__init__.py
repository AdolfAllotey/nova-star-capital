"""NSC Enterprise Capability Management."""

from typing import Any


def build_catalog(*args: Any, **kwargs: Any) -> Any:
    """Load the capability catalog only when called."""
    from .capability_catalog import (
        build_catalog as implementation,
    )

    return implementation(*args, **kwargs)


def generate_catalog(*args: Any, **kwargs: Any) -> Any:
    """Load the catalog generator only when called."""
    from .capability_catalog import (
        generate_catalog as implementation,
    )

    return implementation(*args, **kwargs)


__all__ = [
    "build_catalog",
    "generate_catalog",
]
