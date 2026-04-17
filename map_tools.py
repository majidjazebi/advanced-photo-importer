# -*- coding: utf-8 -*-
# Copyright (C) 2026 Majid Jazebi
# Web: Geotechzone.com
# All rights reserved.
# This plugin is licensed under GNU GPL v3.
"""
Map Tools for Photo Interaction

Handles the map tool for clicking on photos and displaying their metadata.
"""

import os
from qgis.PyQt.QtWidgets import QMessageBox
from qgis.PyQt.QtCore import Qt
from .qt_compat import CrossCursor
from qgis.core import (
    QgsCoordinateTransform,
    QgsCoordinateReferenceSystem,
    QgsPointXY,
    QgsFeatureRequest,
    QgsRectangle,
    QgsProject,
    QgsMessageLog,
    Qgis,
)
from qgis.gui import QgsMapTool, QgsMapToolPan


class OpenPhotoMapTool(QgsMapTool):
    """Map tool for clicking on photo features to view their metadata."""
    
    def __init__(self, canvas, plugin_instance):
        QgsMapTool.__init__(self, canvas)
        self.canvas = canvas
        self.plugin = plugin_instance
        self.cursor = CrossCursor 
    
    def canvasReleaseEvent(self, mouseEvent):
        """Handle map clicks to find the nearest photo feature."""
        
        layer = self.plugin.photo_layer
        if not layer or not layer.isValid():
            QMessageBox.warning(self.canvas.window(), "Warning", "Photo layer not available.")
            self.deactivate_tool() 
            return

        screen_point = mouseEvent.pos()
        map_canvas_point = self.canvas.getCoordinateTransform().toMapCoordinates(screen_point)
        
        try:
            canvas_crs = self.canvas.mapSettings().destinationCrs()
            layer_crs = layer.crs()
            transform = QgsCoordinateTransform(canvas_crs, layer_crs, QgsProject.instance())
            layer_crs_point = transform.transform(map_canvas_point)
            
        except Exception as e:
            QgsMessageLog.logMessage(f"CRS Transformation Error: {e}", 'Photo Plugin', Qgis.Critical)
            QMessageBox.critical(self.canvas.window(), "Error", "Could not transform coordinates for feature search.")
            self.deactivate_tool() 
            return

        # Get tolerance from the plugin instance (set by the dialog)
        tolerance_m = self.plugin.click_tolerance_m
        
        # Calculate the search area extent in layer CRS (degrees/meters)
        if layer.crs().isGeographic():
            # A rough conversion for small distances near the equator
            degree_tolerance = tolerance_m / 111000.0 
        else:
            degree_tolerance = tolerance_m 
        
        search_rect = QgsRectangle(
            layer_crs_point.x() - degree_tolerance,
            layer_crs_point.y() - degree_tolerance,
            layer_crs_point.x() + degree_tolerance,
            layer_crs_point.y() + degree_tolerance
        )

        request = QgsFeatureRequest().setFilterRect(search_rect)

        found_feature = None
        min_distance = float('inf')
        
        # Find the closest feature within tolerance
        for feature in layer.getFeatures(request):
            # Also check if the point is within the specified tolerance distance
            layer_point = QgsPointXY(layer_crs_point)
            feature_point = feature.geometry().asPoint()

            distance = QgsPointXY.distance(layer_point, feature_point)

            if distance < min_distance and distance <= degree_tolerance:
                min_distance = distance
                found_feature = feature
        
        if found_feature:
            # Extract attributes needed for the dialog
            feat_id = found_feature.id()
            photo_path = found_feature.attribute('path')
            lon = found_feature.attribute('longitude')
            lat = found_feature.attribute('latitude')
            direction = found_feature.attribute('direction')
            group_name = found_feature.attribute('group') if layer.fields().indexOf('group') >= 0 else ''
            label_text = found_feature.attribute('label_text') if layer.fields().indexOf('label_text') >= 0 else ''
            photo_time = found_feature.attribute('photo_time') if layer.fields().indexOf('photo_time') >= 0 else ''
            
            # Get label fields
            label_visible = found_feature.attribute('label_visible') if layer.fields().indexOf('label_visible') >= 0 else True
            label_offset_x = found_feature.attribute('label_offset_x') if layer.fields().indexOf('label_offset_x') >= 0 else 0
            label_offset_y = found_feature.attribute('label_offset_y') if layer.fields().indexOf('label_offset_y') >= 0 else 0
            
            # Determine visibility: not selected = visible
            is_visible = feat_id not in layer.selectedFeatureIds()
            
            if photo_path and lon is not None and lat is not None and direction is not None:
                
                self.plugin.photo_edit_dlg.display_photo_and_metadata(
                    feat_id, 
                    photo_path, 
                    lon, 
                    lat, 
                    direction,
                    is_visible,
                    label_text,
                    photo_time
                )
                self.plugin.photo_edit_dlg.show() 
                
                self.plugin.iface.messageBar().pushMessage(
                    "Photo Found", 
                    f"Showing photo details for: {os.path.basename(photo_path)}", 
                    level=Qgis.Info, 
                    duration=3
                )
            else:
                QMessageBox.information(self.canvas.window(), "Information", "Selected point is missing required metadata (path, coordinates, or direction).")
        
        self.deactivate_tool()

    def deactivate_tool(self):
        """Switches the map canvas tool back to the default pan tool, and unchecks the button."""
        pan_tool = QgsMapToolPan(self.canvas)
        self.canvas.setMapTool(pan_tool)
        self.plugin.action_photo.setChecked(False)
