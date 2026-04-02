"""
Metadata source adapters - registry-based extension point.

To add a new source, create a module in this package and decorate the class
with ``@register``.  The adapter becomes available by its ``name`` attribute.
"""

from douban2soul.scraping.adapters.base import BaseMetadataAdapter

_registry: dict[str, type[BaseMetadataAdapter]] = {}


def register(cls: type[BaseMetadataAdapter]) -> type[BaseMetadataAdapter]:
    _registry[cls.name] = cls
    return cls


def get_adapter(name: str) -> BaseMetadataAdapter:
    try:
        return _registry[name]()
    except KeyError:
        available = ", ".join(sorted(_registry)) or "(none)"
        raise ValueError(f"Unknown adapter {name!r}. Available: {available}")


def available_adapters() -> list[str]:
    return sorted(_registry)


# Import adapters so they self-register.
import douban2soul.scraping.adapters.wmdb as _  # noqa: F401, E402
