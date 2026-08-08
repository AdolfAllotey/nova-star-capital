"""Nova Star Capital Enterprise Architecture inventory package."""

from typing import Any


def build_inventory(*args: Any, **kwargs: Any) -> Any:
    """Load the inventory generator only when called."""
    from .enterprise_component_inventory import (
        build_inventory as implementation,
    )

    return implementation(*args, **kwargs)


__all__ = ["build_inventory"]
