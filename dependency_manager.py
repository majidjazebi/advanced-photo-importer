# -*- coding: utf-8 -*-
# Copyright (C) 2026 Majid Jazebi
# Web: Geotechzone.com
# All rights reserved.
# This plugin is licensed under GNU GPL v3.
"""
Dependency Manager for Advanced Photo Importer.
Uses safe_import to load libraries: system-installed first, bundled fallback second.
Bundled libraries live in the 'api_deps' folder (Isolated Vendoring).
"""

import os
import sys
import importlib

from qgis.core import Qgis, QgsMessageLog

TAG = "Advanced Photo Importer"

# Path to the bundled libraries (api_deps = Advanced Photo Importer Dependencies)
_PLUGIN_DIR = os.path.dirname(__file__)
_VENDORED_PATH = os.path.join(_PLUGIN_DIR, "api_deps")

# Define dependencies: (pip_name, import_name, required, description)
DEPENDENCIES = [
    ("exifread", "exifread", True, "EXIF metadata extraction"),
    ("openpyxl", "openpyxl", False, "Excel export/import"),
]

# Track where each module was loaded from: "system" or "bundled"
_import_sources = {}


def _detect_source(mod):
    """Determine whether a module was loaded from api_deps or the system.

    Checks the module's __file__ (or package __path__) to see if it
    physically resides inside the bundled api_deps folder.
    """
    mod_file = getattr(mod, "__file__", None) or ""
    mod_paths = getattr(mod, "__path__", [])
    check_paths = [mod_file] + list(mod_paths)
    vendored = os.path.normcase(os.path.normpath(_VENDORED_PATH))
    for p in check_paths:
        if p and os.path.normcase(os.path.normpath(p)).startswith(vendored):
            return "bundled"
    return "system"


def safe_import(module_name):
    """Import a module safely: system-installed first, bundled fallback second.

    - If already loaded (sys.modules), returns it.
    - Tries normal import (system / user-installed).
    - Falls back to the bundled api_deps folder using sys.path.append
      (append, not insert, so system packages always take priority).
    - Returns the module, or None if unavailable everywhere.
    - Source is always determined by the module's actual file path, not
      by which import step succeeded (avoids false positives after
      api_deps is added to sys.path).
    """
    # 1. Already loaded by this or another plugin
    if module_name in sys.modules:
        mod = sys.modules[module_name]
        if module_name not in _import_sources:
            _import_sources[module_name] = _detect_source(mod)
        return mod

    # 2. Try normal import (may succeed from system OR from api_deps
    #    if api_deps was already added to sys.path by a previous call)
    try:
        mod = importlib.import_module(module_name)
        _import_sources[module_name] = _detect_source(mod)
        QgsMessageLog.logMessage(
            f"{module_name}: loaded ({_import_sources[module_name]})",
            TAG, Qgis.Info,
        )
        return mod
    except ImportError:
        pass

    # 3. Fallback: append bundled path (only once) and try again
    if os.path.isdir(_VENDORED_PATH) and _VENDORED_PATH not in sys.path:
        sys.path.append(_VENDORED_PATH)

    try:
        mod = importlib.import_module(module_name)
        _import_sources[module_name] = _detect_source(mod)
        QgsMessageLog.logMessage(
            f"{module_name}: loaded ({_import_sources[module_name]})",
            TAG, Qgis.Info,
        )
        return mod
    except ImportError:
        QgsMessageLog.logMessage(
            f"{module_name}: NOT FOUND (neither system nor bundled)",
            TAG, Qgis.Warning,
        )
        return None


def get_import_source(module_name):
    """Return where a module was loaded from: 'system', 'bundled', or ''."""
    return _import_sources.get(module_name, "")


class DependencyManager:
    """Check availability of Python dependencies for the plugin."""

    @staticmethod
    def check(import_name):
        """Return True if a package is importable (system or bundled)."""
        return safe_import(import_name) is not None

    @staticmethod
    def check_all():
        """Return a list of dicts with status for every dependency.

        Each dict: {pip, import_name, required, description, installed, source}
        """
        results = []
        for pip_name, import_name, required, description in DEPENDENCIES:
            mod = safe_import(import_name)
            installed = mod is not None
            source = get_import_source(import_name) if installed else ""
            results.append({
                "pip": pip_name,
                "import_name": import_name,
                "required": required,
                "description": description,
                "installed": installed,
                "source": source,
            })
        return results
