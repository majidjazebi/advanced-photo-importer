# -*- coding: utf-8 -*-
# Copyright (C) 2026 Majid Jazebi
# Web: Geotechzone.com
# All rights reserved.
# This plugin is licensed under GNU GPL v3.
"""
UI Manager for Advanced Photo Importer
Handles dialog and UI-related operations.
"""

from qgis.PyQt.QtWidgets import QMessageBox


class UIManager:
    """Manages dialog and UI-related operations."""

    def __init__(self, iface, dlg, photo_list_manager):
        self.iface = iface
        self.dlg = dlg
        self.photo_list_manager = photo_list_manager

    def handle_tab_change(self, index, photo_layer):
        """Handles tab changes in the main dialog."""
        # Assuming 'Imported Photos' is tab index 1
        if index == 1 and self.photo_list_manager:
            if photo_layer and photo_layer.isValid():
                self.photo_list_manager.setLayer(photo_layer)
            else:
                self.photo_list_manager.setLayer(None)
            self.photo_list_manager.populate_list()

    def activate_open_photo_tool(self, checked, photo_layer, open_photo_tool):
        """Activates or deactivates the map tool for viewing photos."""
        if checked:
            if not photo_layer or not photo_layer.isValid():
                QMessageBox.information(self.iface.mainWindow(), "Info", "Please import a photo first to create the layer.")
                # Get the action and set it to unchecked
                # This would need to be passed or accessed differently
                return False

            self.iface.mapCanvas().setMapTool(open_photo_tool)
            return True
        else:
            from qgis.gui import QgsMapToolPan
            pan_tool = QgsMapToolPan(self.iface.mapCanvas())
            self.iface.mapCanvas().setMapTool(pan_tool)
            return True
