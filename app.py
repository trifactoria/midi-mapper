"""Compatibility ASGI module for the midi-mapper backend.

The implementation lives in backend.main. This shim preserves the existing
`uvicorn app:app` entrypoint and makes `import app` behave like the old
single-file module.
"""

import sys
from importlib import import_module

_main = import_module("backend.main")

sys.modules[__name__] = _main
