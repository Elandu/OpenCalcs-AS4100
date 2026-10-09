"""Compatibility import for ``opencalcs_as4100.design_actions``."""

import sys as _sys
from importlib import import_module as _import_module

_sys.modules[__name__] = _import_module("engcalcs_as4100.design_actions")
