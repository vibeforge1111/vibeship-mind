"""Mind - File-based memory system for AI coding assistants."""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("vibeship-mind")
except PackageNotFoundError:
    __version__ = "0.0.0-dev"  # Running from source without install
