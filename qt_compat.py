# -*- coding: utf-8 -*-
"""
Qt 5 / Qt 6 compatibility shim for enum values that moved into scoped enums.

Usage:
    from .qt_compat import AlignCenter, Horizontal, Checked, ...

Every symbol is resolved once at import time and works on both QGIS 3 (Qt 5)
and QGIS 4 (Qt 6).
"""

from qgis.PyQt.QtCore import Qt, QStandardPaths
from qgis.PyQt.QtGui import QFont
from qgis.PyQt.QtWidgets import QDialogButtonBox, QFrame, QMessageBox


def _resolve(obj, scoped_path, flat_name):
    """Return obj.ScopedEnum.Value (Qt 6) or obj.Value (Qt 5)."""
    parts = scoped_path.split(".")
    try:
        result = obj
        for part in parts:
            result = getattr(result, part)
        return result
    except AttributeError:
        return getattr(obj, flat_name)


# ── Qt.AlignmentFlag ─────────────────────────────────────────────────────────
AlignCenter = _resolve(Qt, "AlignmentFlag.AlignCenter", "AlignCenter")

# ── Qt.Orientation ───────────────────────────────────────────────────────────
Horizontal = _resolve(Qt, "Orientation.Horizontal", "Horizontal")

# ── Qt.CheckState ────────────────────────────────────────────────────────────
Checked = _resolve(Qt, "CheckState.Checked", "Checked")

# ── Qt.AspectRatioMode ───────────────────────────────────────────────────────
KeepAspectRatio = _resolve(Qt, "AspectRatioMode.KeepAspectRatio", "KeepAspectRatio")

# ── Qt.TransformationMode ───────────────────────────────────────────────────
SmoothTransformation = _resolve(Qt, "TransformationMode.SmoothTransformation", "SmoothTransformation")

# ── Qt.CursorShape ──────────────────────────────────────────────────────────
CrossCursor = _resolve(Qt, "CursorShape.CrossCursor", "CrossCursor")

# ── Qt.MouseButton ──────────────────────────────────────────────────────────
LeftButton = _resolve(Qt, "MouseButton.LeftButton", "LeftButton")

# ── Qt.ContextMenuPolicy ────────────────────────────────────────────────────
CustomContextMenu = _resolve(Qt, "ContextMenuPolicy.CustomContextMenu", "CustomContextMenu")

# ── QFrame.Shape / QFrame.Shadow ─────────────────────────────────────────────
HLine = _resolve(QFrame, "Shape.HLine", "HLine")
Sunken = _resolve(QFrame, "Shadow.Sunken", "Sunken")
StyledPanel = _resolve(QFrame, "Shape.StyledPanel", "StyledPanel")

# ── QFont.Weight ─────────────────────────────────────────────────────────────
Bold = _resolve(QFont, "Weight.Bold", "Bold")

# ── QDialogButtonBox.StandardButton ──────────────────────────────────────────
ButtonOk = _resolve(QDialogButtonBox, "StandardButton.Ok", "Ok")
ButtonCancel = _resolve(QDialogButtonBox, "StandardButton.Cancel", "Cancel")

# ── QMessageBox.StandardButton ───────────────────────────────────────────────
MsgYes = _resolve(QMessageBox, "StandardButton.Yes", "Yes")
MsgNo = _resolve(QMessageBox, "StandardButton.No", "No")

# ── QStandardPaths.StandardLocation ─────────────────────────────────────────
DesktopLocation = _resolve(QStandardPaths, "StandardLocation.DesktopLocation", "DesktopLocation")
DocumentsLocation = _resolve(QStandardPaths, "StandardLocation.DocumentsLocation", "DocumentsLocation")
