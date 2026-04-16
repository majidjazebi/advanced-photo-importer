# -*- coding: utf-8 -*-
# Copyright (C) 2026 Majid Jazebi
# Web: Geotechzone.com
# All rights reserved.
# This plugin is licensed under GNU GPL v3.
"""
Date & Time Filter Module

Handles time-based filtering of photo features without affecting manual visibility.
This module manages the filterVisibility parameter which is completely separate
from the existing visibility parameter.

Architecture: 
- visibility: Manual user control (existing feature, DO NOT MODIFY)
- filterVisibility: Automatic, date-based filter (this module)
- Final visibility: visibility AND filterVisibility
"""

from datetime import datetime
from qgis.PyQt.QtCore import QObject, pyqtSignal
from qgis.core import (
    QgsMessageLog,
    Qgis,
    QgsFeature,
)


class DateTimeFilter(QObject):
    """
    Manages date & time based filtering for photo features.
    
    This class is responsible ONLY for the filterVisibility parameter.
    It never touches the visibility parameter (manual user control).
    """
    
    # Signal emitted when filter is applied or removed
    filterApplied = pyqtSignal()
    filterRemoved = pyqtSignal()
    
    def __init__(self, iface):
        """
        Initialize the DateTimeFilter.
        
        Args:
            iface: QGIS interface object
        """
        super().__init__()
        self.iface = iface
        self.filter_active = False
        self.start_datetime = None
        self.end_datetime = None
        self.original_icons = {}  # Store original svg_icon values before filtering
        
        QgsMessageLog.logMessage(
            "[DATE FILTER] DateTimeFilter module initialized",
            'Photo Plugin', 
            Qgis.Info
        )
    
    def apply_filter(self, photo_layer, start_datetime, end_datetime):
        """
        Apply date & time filter to photo layer.
        
        For each photo:
        - If photo_time is within [start_datetime, end_datetime]: filterVisibility = True
        - If photo_time is outside range: filterVisibility = False
        
        Final visibility = visibility AND filterVisibility
        
        Args:
            photo_layer: The photo layer to filter
            start_datetime: datetime object for filter start
            end_datetime: datetime object for filter end
        
        Returns:
            bool: True if filter was applied successfully
        """
        if not photo_layer or not photo_layer.isValid():
            QgsMessageLog.logMessage(
                "[DATE FILTER] Photo layer is invalid",
                'Photo Plugin',
                Qgis.Warning
            )
            return False
        
        if start_datetime > end_datetime:
            QgsMessageLog.logMessage(
                "[DATE FILTER] Start time is after end time",
                'Photo Plugin',
                Qgis.Warning
            )
            self.iface.messageBar().pushMessage(
                "Filter Error",
                "Start date/time must be before end date/time",
                level=Qgis.Warning,
                duration=5
            )
            return False
        
        self.start_datetime = start_datetime
        self.end_datetime = end_datetime
        self.filter_active = True
        
        QgsMessageLog.logMessage(
            f"[DATE FILTER] Applying filter: {start_datetime} to {end_datetime}",
            'Photo Plugin',
            Qgis.Info
        )
        
        # Get field indices
        photo_time_idx = photo_layer.fields().indexOf('photo_time')
        filter_visibility_idx = photo_layer.fields().indexOf('filterVisibility')
        svg_icon_idx = photo_layer.fields().indexOf('svg_icon')
        visible_idx = photo_layer.fields().indexOf('visible')
        
        if photo_time_idx < 0:
            QgsMessageLog.logMessage(
                "[DATE FILTER] photo_time field not found in layer",
                'Photo Plugin',
                Qgis.Warning
            )
            return False
        
        if filter_visibility_idx < 0:
            QgsMessageLog.logMessage(
                "[DATE FILTER] filterVisibility field not found in layer",
                'Photo Plugin',
                Qgis.Warning
            )
            return False
        
        # Start editing
        if not photo_layer.isEditable():
            photo_layer.startEditing()
        
        filtered_count = 0
        visible_count = 0
        no_time_count = 0
        
        # Process each feature
        for feature in photo_layer.getFeatures():
            photo_time_str = feature['photo_time']
            fid = feature.id()
            current_icon = feature['svg_icon']
            manual_visible = feature['visible'] if visible_idx >= 0 else True
            
            if not photo_time_str:
                # No timestamp - hide by default when filter is active
                photo_layer.changeAttributeValue(fid, filter_visibility_idx, False)
                
                # Change icon to Invisible.svg (only if manual visibility allows)
                if current_icon != 'Invisible.svg':
                    self.original_icons[fid] = current_icon
                    photo_layer.changeAttributeValue(fid, svg_icon_idx, 'Invisible.svg')
                
                no_time_count += 1
                filtered_count += 1
                continue
            
            # Parse photo timestamp
            try:
                photo_datetime = self._parse_photo_time(photo_time_str)
                
                # Check if photo is within date range
                if start_datetime <= photo_datetime <= end_datetime:
                    # Photo is within range - set filterVisibility = True
                    photo_layer.changeAttributeValue(fid, filter_visibility_idx, True)
                    
                    # Restore original icon ONLY if manual visibility is also True
                    if manual_visible:
                        if fid in self.original_icons:
                            original_icon = self.original_icons[fid]
                            photo_layer.changeAttributeValue(fid, svg_icon_idx, original_icon)
                            del self.original_icons[fid]
                        elif current_icon == 'Invisible.svg':
                            # Use svg_icon_backup to restore the correct icon
                            backup_idx = photo_layer.fields().indexOf('svg_icon_backup')
                            restored = None
                            if backup_idx >= 0:
                                backup_val = feature.attribute('svg_icon_backup')
                                if backup_val and backup_val != 'Invisible.svg':
                                    restored = backup_val
                            photo_layer.changeAttributeValue(fid, svg_icon_idx, restored if restored else '0.svg')
                    
                    visible_count += 1
                else:
                    # Photo is outside range - set filterVisibility = False
                    photo_layer.changeAttributeValue(fid, filter_visibility_idx, False)
                    
                    # Change icon to Invisible.svg
                    if current_icon != 'Invisible.svg':
                        self.original_icons[fid] = current_icon
                        photo_layer.changeAttributeValue(fid, svg_icon_idx, 'Invisible.svg')
                    
                    filtered_count += 1
                    
            except ValueError as e:
                # Invalid timestamp format - hide by default
                QgsMessageLog.logMessage(
                    f"[DATE FILTER] Invalid timestamp format for feature {fid}: {photo_time_str}",
                    'Photo Plugin',
                    Qgis.Warning
                )
                photo_layer.changeAttributeValue(fid, filter_visibility_idx, False)
                
                # Change icon to Invisible.svg
                if current_icon != 'Invisible.svg':
                    self.original_icons[fid] = current_icon
                    photo_layer.changeAttributeValue(fid, svg_icon_idx, 'Invisible.svg')
                
                filtered_count += 1
        
        # Commit changes
        photo_layer.commitChanges()
        
        # Single refresh
        photo_layer.triggerRepaint()
        self.iface.mapCanvas().refresh()
        
        # Emit signal
        self.filterApplied.emit()
        
        # Show summary message
        total = photo_layer.featureCount()
        message = f"Filter applied: {visible_count} photos visible, {filtered_count} filtered out"
        if no_time_count > 0:
            message += f" ({no_time_count} without timestamps)"
        
        QgsMessageLog.logMessage(
            f"[DATE FILTER] {message}",
            'Photo Plugin',
            Qgis.Info
        )
        
        self.iface.messageBar().pushMessage(
            "Filter Applied",
            message,
            level=Qgis.Success,
            duration=5
        )
        
        return True
    
    def remove_filter(self, photo_layer):
        """
        Remove the date & time filter.
        
        Sets filterVisibility = True for all photos.
        Photos are visible only if: visibility == True AND filterVisibility == True
        
        ⚠️ IMPORTANT: This does NOT modify the visibility parameter.
        Photos that were manually hidden (visibility = False) remain hidden.
        
        Args:
            photo_layer: The photo layer
        
        Returns:
            bool: True if filter was removed successfully
        """
        if not photo_layer or not photo_layer.isValid():
            QgsMessageLog.logMessage(
                "[DATE FILTER] Photo layer is invalid",
                'Photo Plugin',
                Qgis.Warning
            )
            return False
        
        QgsMessageLog.logMessage(
            "[DATE FILTER] Removing date/time filter",
            'Photo Plugin',
            Qgis.Info
        )
        
        # Get field indices
        filter_visibility_idx = photo_layer.fields().indexOf('filterVisibility')
        svg_icon_idx = photo_layer.fields().indexOf('svg_icon')
        visible_idx = photo_layer.fields().indexOf('visible')
        
        if filter_visibility_idx < 0:
            QgsMessageLog.logMessage(
                "[DATE FILTER] filterVisibility field not found in layer",
                'Photo Plugin',
                Qgis.Warning
            )
            return False
        
        # Start editing
        if not photo_layer.isEditable():
            photo_layer.startEditing()
        
        # Set filterVisibility = True for all photos and restore icons
        backup_idx = photo_layer.fields().indexOf('svg_icon_backup')
        fids_now_visible = []  # Track fids that become visible so we can deselect them
        for feature in photo_layer.getFeatures():
            fid = feature.id()
            manual_visible = feature['visible'] if visible_idx >= 0 else True
            current_icon = feature['svg_icon']
            
            # Set filterVisibility = True
            photo_layer.changeAttributeValue(fid, filter_visibility_idx, True)
            
            # Restore icon only if manually visible
            if manual_visible:
                fids_now_visible.append(fid)
                if current_icon == 'Invisible.svg':
                    # Determine the correct icon to restore to
                    restored = None
                    # 1. Use original_icons (saved when filter was applied)
                    if fid in self.original_icons:
                        restored = self.original_icons[fid]
                    # 2. Fall back to svg_icon_backup field (handles photos that were
                    #    already invisible before the filter, then made visible during filter)
                    if not restored and backup_idx >= 0:
                        backup_val = feature.attribute('svg_icon_backup')
                        if backup_val and backup_val != 'Invisible.svg':
                            restored = backup_val
                    # 3. Last resort
                    if not restored:
                        restored = '0.svg'
                    photo_layer.changeAttributeValue(fid, svg_icon_idx, restored)
        
        # Clear stored original icons
        self.original_icons.clear()
        
        # Deselect features that are now visible so the selection handler
        # doesn't re-hide them on the next selection change
        if fids_now_visible:
            current_selection = list(photo_layer.selectedFeatureIds())
            visible_set = set(fids_now_visible)
            new_selection = [f for f in current_selection if f not in visible_set]
            if len(new_selection) != len(current_selection):
                photo_layer.blockSignals(True)
                photo_layer.selectByIds(new_selection)
                photo_layer.blockSignals(False)
        
        # Commit changes
        photo_layer.commitChanges()
        
        # Clear filter state
        self.filter_active = False
        self.start_datetime = None
        self.end_datetime = None
        
        # Single refresh
        photo_layer.triggerRepaint()
        self.iface.mapCanvas().refresh()
        
        # Emit signal
        self.filterRemoved.emit()
        
        QgsMessageLog.logMessage(
            "[DATE FILTER] Filter removed - all photos restored (respecting manual visibility)",
            'Photo Plugin',
            Qgis.Info
        )
        
        self.iface.messageBar().pushMessage(
            "Filter Removed",
            "Date/time filter removed. All photos restored (respecting manual visibility).",
            level=Qgis.Success,
            duration=4
        )
        
        return True
    
    def _parse_photo_time(self, time_str):
        """
        Parse photo time string to datetime object.
        
        Expected format: "YYYY:MM:DD HH:MM:SS" (EXIF format)
        
        Args:
            time_str: Time string to parse
        
        Returns:
            datetime: Parsed datetime object
        
        Raises:
            ValueError: If time_str cannot be parsed
        """
        # Try EXIF format first: "YYYY:MM:DD HH:MM:SS"
        try:
            return datetime.strptime(time_str, "%Y:%m:%d %H:%M:%S")
        except ValueError:
            pass
        
        # Try ISO format: "YYYY-MM-DD HH:MM:SS"
        try:
            return datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass
        
        # Try date only: "YYYY:MM:DD"
        try:
            return datetime.strptime(time_str, "%Y:%m:%d")
        except ValueError:
            pass
        
        # Try date only: "YYYY-MM-DD"
        try:
            return datetime.strptime(time_str, "%Y-%m-%d")
        except ValueError:
            pass
        
        raise ValueError(f"Cannot parse time string: {time_str}")
    
    def is_filter_active(self):
        """
        Check if filter is currently active.
        
        Returns:
            bool: True if filter is active
        """
        return self.filter_active
    
    def get_filter_range(self):
        """
        Get the current filter date/time range.
        
        Returns:
            tuple: (start_datetime, end_datetime) or (None, None) if no filter active
        """
        if self.filter_active:
            return (self.start_datetime, self.end_datetime)
        return (None, None)
    
    def check_single_feature(self, photo_layer, feature):
        """
        Check if a single feature passes the current filter and update its filterVisibility.
        This is called when manual visibility changes to reapply the filter to that photo.
        
        Args:
            photo_layer: The photo layer
            feature: The feature to check
        
        Returns:
            bool: True if feature passes filter (or no filter active), False if filtered out
        """
        from qgis.core import QgsMessageLog, Qgis
        
        feat_id = feature.id()
        
        # If no filter is active, all features pass
        if not self.filter_active:
            QgsMessageLog.logMessage(
                f"[FILTER CHECK] Feature {feat_id}: No filter active → PASSES",
                'Photo Plugin',
                Qgis.Info
            )
            return True
        
        QgsMessageLog.logMessage(
            f"[FILTER CHECK] Feature {feat_id}: Filter active [{self.start_datetime} to {self.end_datetime}]",
            'Photo Plugin',
            Qgis.Info
        )
        
        photo_time_str = feature.attribute('photo_time')
        if not photo_time_str:
            # No timestamp - fails filter
            QgsMessageLog.logMessage(
                f"[FILTER CHECK] Feature {feat_id}: No photo_time → FAILS FILTER",
                'Photo Plugin',
                Qgis.Warning
            )
            return False
        
        QgsMessageLog.logMessage(
            f"[FILTER CHECK] Feature {feat_id}: photo_time = {photo_time_str}",
            'Photo Plugin',
            Qgis.Info
        )
        
        # Parse photo timestamp
        try:
            photo_datetime = self._parse_photo_time(photo_time_str)
            
            QgsMessageLog.logMessage(
                f"[FILTER CHECK] Feature {feat_id}: Parsed datetime = {photo_datetime}",
                'Photo Plugin',
                Qgis.Info
            )
            
            # Check if photo is within date range
            if self.start_datetime <= photo_datetime <= self.end_datetime:
                QgsMessageLog.logMessage(
                    f"[FILTER CHECK] Feature {feat_id}: Within range → PASSES FILTER",
                    'Photo Plugin',
                    Qgis.Info
                )
                return True
            else:
                QgsMessageLog.logMessage(
                    f"[FILTER CHECK] Feature {feat_id}: Outside range → FAILS FILTER",
                    'Photo Plugin',
                    Qgis.Warning
                )
                return False
                
        except ValueError as e:
            # Invalid timestamp format - fails filter
            QgsMessageLog.logMessage(
                f"[FILTER CHECK] Feature {feat_id}: Invalid timestamp format '{photo_time_str}' → FAILS FILTER ({str(e)})",
                'Photo Plugin',
                Qgis.Warning
            )
            return False
    
    def _get_base_icon_from_direction(self, angle):
        """
        Get base SVG icon filename from direction angle.
        Maps angles to N, NE, E, SE, S, SW, W, NW.
        
        Args:
            angle: Direction angle in degrees
        
        Returns:
            str: Base icon filename (e.g., "N.svg", "NE.svg")
        """
        if angle is None:
            return "N.svg"
        
        # Normalize angle to 0-360 range
        angle = angle % 360
        
        # Round to nearest 45-degree increment
        rounded_angle = round(angle / 45) * 45
        
        # Map to cardinal/intercardinal directions
        direction_map = {
            0: "N.svg",
            45: "NE.svg",
            90: "E.svg",
            135: "SE.svg",
            180: "S.svg",
            225: "SW.svg",
            270: "W.svg",
            315: "NW.svg",
            360: "N.svg"
        }
        
        return direction_map.get(rounded_angle, "N.svg")

