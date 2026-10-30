# Package namespace for mini_mime_multipart.
#
# Re-exporting parse_multipart and ParseError here lets callers use a single
# import path regardless of which internal module the implementation lives in.

from .core import parse_multipart, ParseError

__all__ = ["parse_multipart", "ParseError"]
