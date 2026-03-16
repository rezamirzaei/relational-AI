__all__ = ["__version__"]

try:
    from importlib.metadata import version as _pkg_version

    __version__: str = _pkg_version("relational-fraud-intelligence")
except Exception:  # package not installed in editable mode
    __version__ = "1.0.0"
