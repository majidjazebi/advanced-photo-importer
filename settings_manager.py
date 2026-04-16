# -*- coding: utf-8 -*-
# Copyright (C) 2026 Majid Jazebi
# Web: Geotechzone.com
# All rights reserved.
# This plugin is licensed under GNU GPL v3.
"""
Settings Manager for Advanced Photo Importer
Handles plugin settings and configuration.
"""

from qgis.core import Qgis, QgsMessageLog


class SettingsManager:
    """Manages plugin settings and configuration."""

    def __init__(self, iface, symbol_renderer, photo_list_manager=None, label_manager=None):
        self.iface = iface
        self.symbol_renderer = symbol_renderer
        self.photo_list_manager = photo_list_manager
        self.label_manager = label_manager
        self.click_tolerance_m = 5.0

    def update_click_tolerance(self, tolerance):
        """Updates the internal click tolerance value."""
        try:
            self.click_tolerance_m = float(tolerance)
        except ValueError:
            QgsMessageLog.logMessage("Invalid value for click tolerance. Keeping old value.", 'Photo Plugin', Qgis.Warning)

    def apply_settings(self, dlg, photo_layer):
        """Apply all current settings and update the layer renderer."""
        # Apply direction line setting
        if hasattr(dlg, 'checkBox_include_direction'):
            direction_checked = dlg.checkBox_include_direction.isChecked()
            self.symbol_renderer.set_include_direction(direction_checked)

        # Force update the layer renderer and refresh the map
        if photo_layer:
            self.symbol_renderer.update_layer_symbol_manually(photo_layer, self.iface)
            # Force a map refresh
            self.iface.mapCanvas().refresh()

        # Update photo list manager if it exists
        if self.photo_list_manager:
            self.photo_list_manager.populate_list()

        # Show confirmation message
        self.iface.messageBar().pushMessage(
            "Settings Applied",
            "Map display settings have been updated and refreshed",
            level=Qgis.Info,
            duration=3
        )
