# -*- coding: utf-8 -*-
# Copyright (C) 2026 Majid Jazebi
# Web: Geotechzone.com
# All rights reserved.
# This plugin is licensed under GNU GPL v3.
"""
Feature Manager for Advanced Photo Importer
Handles feature metadata and visibility operations.
"""

from qgis.PyQt.QtWidgets import QMessageBox
from qgis.core import Qgis, QgsMessageLog


class FeatureManager:
    """Manages feature metadata and visibility operations."""

    def __init__(self, iface, layer_manager, photo_list_manager=None, date_time_filter=None):
        self.iface = iface
        self.layer_manager = layer_manager
        self.photo_list_manager = photo_list_manager
        self.date_time_filter = date_time_filter

    def update_feature_metadata(self, photo_layer, feat_id, new_lon, new_lat, new_direction):
        """Delegates to layer_manager to update feature metadata and updates Excel file."""
        success = self.layer_manager.update_feature_metadata(self.iface, photo_layer, feat_id, new_lon, new_lat, new_direction)

        # Update Excel file with the new coordinates/direction
        if photo_layer and photo_layer.isValid() and success:
            try:
                feature = photo_layer.getFeature(feat_id)
                if feature.isValid():
                    photo_path = feature.attribute('path')
                    if photo_path:
                        # Update Excel with the modified data (wrapped in try-except to prevent crashes)
                        try:
                            updated_photo_data = [{
                                'path': photo_path,
                                'x': new_lon,
                                'y': new_lat,
                                'direction': new_direction
                            }]
                            from .excel_manager import ExcelManager
                            excel_manager = ExcelManager(self.iface)
                            excel_manager._update_excel_file(updated_photo_data, photo_layer)
                        except Exception as excel_error:
                            # Don't let Excel errors crash the metadata update
                            QgsMessageLog.logMessage(
                                f"Excel update failed (non-critical): {str(excel_error)}",
                                'Photo Plugin',
                                Qgis.Warning
                            )
                            # Metadata update succeeded, Excel update failed - show subtle warning
                            self.iface.messageBar().pushMessage(
                                "Excel Update Skipped",
                                "Metadata updated successfully, but Excel file could not be updated. Close Excel if it's open.",
                                level=Qgis.Warning,
                                duration=3
                            )
            except Exception as e:
                self.iface.messageBar().pushMessage(
                    "Update Error",
                    f"Failed to update metadata: {str(e)}",
                    level=Qgis.Warning,
                    duration=3
                )

        return success

    def update_feature_visibility(self, photo_layer, feat_id, is_visible, symbol_renderer):
        """OPTIMIZED: Updates visibility with icon restoration and proper cleanup.
        
        Respects both manual visibility AND filter visibility:
        - A photo is only shown if BOTH visibility=True AND filterVisibility=True
        """
        if not photo_layer or not photo_layer.isValid():
            return

        # Start editing once
        if not photo_layer.isEditable():
            photo_layer.startEditing()
        
        # Get current feature
        feature = photo_layer.getFeature(feat_id)
        if not feature.isValid():
            return
        
        current_icon = feature.attribute('svg_icon')
        
        # Update visible attribute (manual visibility)
        visible_idx = photo_layer.fields().indexOf('visible')
        if visible_idx >= 0:
            photo_layer.changeAttributeValue(feat_id, visible_idx, is_visible)
        
        # Determine filter status
        passes_filter = True
        if self.date_time_filter:
            feature = photo_layer.getFeature(feat_id)
            passes_filter = self.date_time_filter.check_single_feature(photo_layer, feature)
        else:
            filter_visibility_idx = photo_layer.fields().indexOf('filterVisibility')
            if filter_visibility_idx >= 0:
                passes_filter = feature.attribute('filterVisibility')
                if passes_filter is None:
                    passes_filter = True
        
        # Final visibility: manual AND filter
        actually_visible = is_visible and passes_filter
        
        # Show warning only when user tries to show a filtered photo
        if is_visible and not passes_filter:
            photo_time = feature.attribute('photo_time')
            self.iface.messageBar().pushMessage(
                "Filtered Photo",
                f"Photo is hidden by active date/time filter (time={photo_time})",
                level=Qgis.Warning,
                duration=3
            )
        
        # Handle icon switching (simplified for rotation system)
        svg_icon_idx = photo_layer.fields().indexOf('svg_icon')
        svg_icon_backup_idx = photo_layer.fields().indexOf('svg_icon_backup')
        if svg_icon_idx >= 0:
            if actually_visible and current_icon == 'Invisible.svg':
                # Try to restore from backup if available, else default to 0.svg
                restored_icon = None
                if svg_icon_backup_idx >= 0:
                    restored_icon = feature.attribute('svg_icon_backup')
                if restored_icon:
                    photo_layer.changeAttributeValue(feat_id, svg_icon_idx, restored_icon)
                else:
                    photo_layer.changeAttributeValue(feat_id, svg_icon_idx, '0.svg')
            elif not actually_visible and current_icon != 'Invisible.svg':
                # Before setting to invisible, save current icon to backup if available
                if svg_icon_backup_idx >= 0 and current_icon:
                    photo_layer.changeAttributeValue(feat_id, svg_icon_backup_idx, current_icon)
                # Set to invisible
                photo_layer.changeAttributeValue(feat_id, svg_icon_idx, 'Invisible.svg')
        
        # Update selection (selected = hidden) - block signals to avoid
        # triggering on_selection_changed which would duplicate our work
        current_selection = list(photo_layer.selectedFeatureIds())
        if actually_visible and feat_id in current_selection:
            current_selection.remove(feat_id)
        elif not actually_visible and feat_id not in current_selection:
            current_selection.append(feat_id)
        photo_layer.blockSignals(True)
        photo_layer.selectByIds(current_selection)
        photo_layer.blockSignals(False)
        
        # Commit changes and close editing
        if photo_layer.isEditable():
            photo_layer.commitChanges()
        
        # Immediate refresh
        photo_layer.triggerRepaint()
        self.iface.mapCanvas().refresh()

    def handle_metadata_update_request(self, photo_layer, feat_id, new_lon, new_lat, new_direction):
        """Handles metadata update requests from the photo list manager."""
        if not photo_layer or not photo_layer.isValid():
            QMessageBox.warning(None, "Error", "No valid photo layer found.")
            return

        # Use the layer manager to update the feature metadata
        success = self.layer_manager.update_feature_metadata(
            self.iface, photo_layer, feat_id, new_lon, new_lat, new_direction
        )

        if success:
            # Refresh the photo list to show updated information
            if self.photo_list_manager:
                self.photo_list_manager.populate_list()
