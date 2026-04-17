# -*- coding: utf-8 -*-
# Copyright (C) 2026 Majid Jazebi
# Web: Geotechzone.com
# All rights reserved.
# This plugin is licensed under GNU GPL v3.
"""
Photo List Management UI Components

Handles the photo list widget, visibility toggling, and preview display.
"""

import os
import platform
from qgis.PyQt.QtCore import Qt, pyqtSignal, QProcess, QTimer
from qgis.PyQt.QtGui import QPixmap
from .qt_compat import AlignCenter, Checked, LeftButton, KeepAspectRatio, SmoothTransformation, CustomContextMenu
from qgis.PyQt.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QCheckBox,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QLineEdit,
    QFormLayout,
    QGroupBox,
    QComboBox,
    QDoubleSpinBox,
)
from qgis.core import QgsVectorLayer, Qgis


class PhotoListItemWidget(QWidget):
    """Custom widget containing checkbox and label for a photo list item."""
    
    # Signal to emit when the checkbox state changes, carrying the Feature ID and new state
    visibilityToggled = pyqtSignal(int, bool)
    
    # Signal to emit when the item is clicked, carrying the photo path
    itemClicked = pyqtSignal(str) 
    
    def __init__(self, feature_id, photo_path, initial_visible, group_name='', label_text='', parent=None):
        super().__init__(parent)
        self.feature_id = feature_id
        self.photo_path = photo_path
        self.base_name = os.path.basename(photo_path)
        self.group_name = group_name
        self.label_text = label_text

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(5, 1, 5, 1)
        self.layout.setSpacing(5)

        # Checkbox for visibility
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(initial_visible)
        self.checkbox.stateChanged.connect(self._on_visibility_change)
        
        # Label for file name
        self.label = QLabel(self.base_name)
        self.label.setToolTip(self.photo_path)
        
        # Label for group name (if available)
        if group_name:
            self.group_label = QLabel(f"[{group_name}]")
            self.group_label.setStyleSheet("color: #0066cc; font-style: italic; font-size: 9pt;")
            self.group_label.setToolTip(f"Group: {group_name}")
        else:
            self.group_label = None
        
        # Label text display
        if label_text:
            self.label_text_label = QLabel(f" | {label_text}")
            self.label_text_label.setStyleSheet("color: #666666; font-size: 9pt;")
            self.label_text_label.setToolTip(f"Label: {label_text}")
        else:
            self.label_text_label = None
        
        self.layout.addWidget(self.checkbox)
        self.layout.addWidget(self.label)
        if self.group_label:
            self.layout.addWidget(self.group_label)
        if self.label_text_label:
            self.layout.addWidget(self.label_text_label)
        self.layout.addStretch()
        
    def _on_visibility_change(self, state):
        """Emits signal when checkbox state changes."""
        from qgis.core import QgsMessageLog, Qgis
        is_visible = state == Checked
        QgsMessageLog.logMessage(f"[VIS DEBUG] Checkbox changed for feature {self.feature_id}: checked={state == Checked}, is_visible={is_visible}", 'Photo Plugin', Qgis.Info)
        self.visibilityToggled.emit(self.feature_id, is_visible)

    def mousePressEvent(self, event):
        """Emits signal when the widget is clicked (for displaying on the right)."""
        if event.button() == LeftButton:
            self.itemClicked.emit(self.photo_path)
        super().mousePressEvent(event)


class PhotoListManager(QWidget):
    """Manages the list of imported photos, visibility, and image display."""
    
    # Signal to request a full update of the layer symbology
    updateRendererRequested = pyqtSignal()
    
    # Signal to request metadata update for a feature
    updateMetadataRequested = pyqtSignal(int, float, float, object)  # feat_id, lon, lat, direction
    
    # Signal emitted when visibility is changed from the list (to sync with Photo Edit Dialog)
    visibilityChangedFromList = pyqtSignal(int, bool)  # feat_id, is_visible
    
    def __init__(self, iface, photo_layer=None, parent=None, date_time_filter=None):
        super().__init__(parent)
        self.iface = iface
        self.layer = photo_layer
        self.date_time_filter = date_time_filter  # Store reference to filter
        self.list_widget = QListWidget() 
        
        self.current_photo_path = None # Store the path of the currently displayed photo
        self.current_feature_id = None # Store the ID of the currently selected feature
        
        # Initialize debounce timer for optimized refresh
        self._refresh_timer = QTimer()
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.timeout.connect(self._do_deferred_refresh)
        self._pending_refresh = False

        self.image_preview = QLabel("Select a photo to see a preview.")
        self.image_preview.setAlignment(AlignCenter)
        self.image_preview.setScaledContents(True)
        self.image_preview.setMinimumSize(250, 150) 
        
        # Single "High Quality" Button for the preview area
        self.hq_button = QPushButton("See High Quality Photo")
        self.hq_button.setToolTip("Open the full-resolution image file in the default viewer.")
        self.hq_button.clicked.connect(self._on_hq_button_click)
        self.hq_button.setEnabled(False) # Start disabled until a photo is selected
        
        # Input fields for editing coordinates and direction
        self.coord_group = QGroupBox("Edit Photo Metadata")
        coord_layout = QFormLayout()
        
        self.lon_edit = QLineEdit()
        self.lon_edit.setPlaceholderText("Longitude")
        coord_layout.addRow("Longitude:", self.lon_edit)
        
        self.lat_edit = QLineEdit()
        self.lat_edit.setPlaceholderText("Latitude")
        coord_layout.addRow("Latitude:", self.lat_edit)
        
        self.direction_edit = QLineEdit()
        self.direction_edit.setPlaceholderText("Direction (degrees)")
        coord_layout.addRow("Direction:", self.direction_edit)
        
        # Photo time field
        self.photo_time_edit = QLineEdit()
        self.photo_time_edit.setPlaceholderText("YYYY:MM:DD HH:MM:SS")
        self.photo_time_edit.setReadOnly(True)  # Display only, not editable here
        coord_layout.addRow("Photo Time:", self.photo_time_edit)
        
        # Label text field
        self.label_text_edit = QLineEdit()
        self.label_text_edit.setPlaceholderText("Label text (shown on map)")
        coord_layout.addRow("Label:", self.label_text_edit)
        
        self.coord_group.setLayout(coord_layout)
        
        # Update button
        self.update_button = QPushButton("Update Metadata")
        self.update_button.setToolTip("Update the selected photo's coordinates and direction.")
        self.update_button.clicked.connect(self._on_update_metadata_click)
        self.update_button.setEnabled(False)  # Start disabled until a photo is selected
        
        # Layout for the new tab content (List on left, Preview/Button on right)
        right_side_layout = QVBoxLayout()
        right_side_layout.addWidget(self.image_preview)
        right_side_layout.addWidget(self.hq_button)
        right_side_layout.addWidget(self.coord_group)
        right_side_layout.addWidget(self.update_button)
        right_side_layout.addStretch()

        main_layout = QHBoxLayout(self)
        main_layout.addWidget(self.list_widget, 2) 
        main_layout.addLayout(right_side_layout, 1) 
        
        self.list_widget.setContextMenuPolicy(CustomContextMenu)

        self.setLayer(photo_layer)

    def setLayer(self, layer):
        """Sets the internal layer reference and attempts to populate the list."""
        self.layer = layer

    def populate_list(self):
        """
        Fills the list widget with photo features.
        Uses the 'visible' attribute to determine initial visibility.
        """
        if not self.layer or not self.layer.isValid():
            self.list_widget.clear()
            self.list_widget.addItem("No photo layer loaded.")
            self.image_preview.clear()
            self.image_preview.setText("Select a photo to see a preview.")
            self.hq_button.setEnabled(False)
            self.current_photo_path = None
            return

        self.list_widget.clear()
        
        hidden_photos = []
        for feature in self.layer.getFeatures():
            feat_id = feature.id()
            photo_path = feature.attribute('path')
            group_name = feature.attribute('group') if self.layer.fields().indexOf('group') >= 0 else ''
            label_text = feature.attribute('label_text') if self.layer.fields().indexOf('label_text') >= 0 else ''
            
            if photo_path:
                
                # Read visibility from the 'visible' attribute, not from selection
                visible_idx = self.layer.fields().indexOf('visible')
                if visible_idx >= 0:
                    initial_visible = feature.attribute('visible')
                    if initial_visible is None:
                        initial_visible = True  # Default to visible if not set
                else:
                    # Fallback: check if feature is selected (selected = hidden)
                    selected_ids = self.layer.selectedFeatureIds()
                    initial_visible = feat_id not in selected_ids
                  
                if not initial_visible:
                    hidden_photos.append(f"{photo_path} (hidden)")
                                                          
                # --- The Custom Widget ---
                item_widget = PhotoListItemWidget(feat_id, photo_path, initial_visible=initial_visible, group_name=group_name, label_text=label_text) 
                item_widget.visibilityToggled.connect(self.toggle_feature_visibility)
                item_widget.itemClicked.connect(self.display_photo_preview)
                
                # The QListWidgetItem acts as a container
                list_item = QListWidgetItem(self.list_widget)
                list_item.setSizeHint(item_widget.sizeHint())
                self.list_widget.addItem(list_item)
                self.list_widget.setItemWidget(list_item, item_widget)
                
        # Debug: Show hidden photos
        if hidden_photos:
            self.iface.messageBar().pushMessage("Info", f"Photos hidden in list: {len(hidden_photos)}", level=Qgis.Info, duration=10)
        
        # After populating, ensure the map is refreshed (this now triggers the rule-based hiding)
        self.updateRendererRequested.emit()
    
    def manually_uncheck_features_by_paths(self, photo_paths):
        """Manually uncheck checkboxes for specific photo paths."""
        paths_set = set(photo_paths)
        for i in range(self.list_widget.count()):
            list_item = self.list_widget.item(i)
            item_widget = self.list_widget.itemWidget(list_item)
            
            if item_widget and isinstance(item_widget, PhotoListItemWidget):
                if item_widget.photo_path in paths_set:
                    item_widget.checkbox.setChecked(False)
    
    def update_checkbox_state(self, feature_id, is_visible):
        """Updates the checkbox state for a specific feature without repopulating the entire list."""
        for i in range(self.list_widget.count()):
            list_item = self.list_widget.item(i)
            item_widget = self.list_widget.itemWidget(list_item)
            
            if item_widget and isinstance(item_widget, PhotoListItemWidget):
                if item_widget.feature_id == feature_id:
                    item_widget.checkbox.blockSignals(True)
                    item_widget.checkbox.setChecked(is_visible)
                    item_widget.checkbox.blockSignals(False)
                    return 

    def _on_hq_button_click(self):
        """Opens the high-quality photo in the system's default viewer."""
        if not self.current_photo_path:
            return

        try:
            # Platform-independent method to open file
            if platform.system() == "Windows":
                os.startfile(self.current_photo_path)
            elif platform.system() == "Darwin":  # macOS
                QProcess.startDetached('open', [self.current_photo_path])
            else:  # Linux/others
                QProcess.startDetached('xdg-open', [self.current_photo_path])
            
        except Exception as e:
            QMessageBox.critical(self.parent(), "Error", f"Could not open file in default viewer: {e}")

    def display_photo_preview(self, photo_path):
        """Displays a scaled preview of the selected image."""
        self.image_preview.setText("Loading image...")
        self.current_photo_path = photo_path # Update current path
        self.hq_button.setEnabled(True)
        
        # Find the feature ID for this photo path and populate coordinate fields
        self.current_feature_id = None
        if self.layer and self.layer.isValid():
            for feature in self.layer.getFeatures():
                if feature.attribute('path') == photo_path:
                    self.current_feature_id = feature.id()
                    self._populate_coordinate_fields(feature)
                    break
        
        # Enable/disable update button based on whether we found a feature
        self.update_button.setEnabled(self.current_feature_id is not None)
        
        try:
            pixmap = QPixmap(photo_path)
            if pixmap.isNull():
                self.image_preview.setText(f"Could not load image: {os.path.basename(photo_path)}")
                self.hq_button.setEnabled(False)
                return

            # Scale the pixmap down to fit the preview area while maintaining aspect ratio
            scaled_pixmap = pixmap.scaled(
                self.image_preview.size(), 
                KeepAspectRatio, 
                SmoothTransformation
            )
            self.image_preview.setPixmap(scaled_pixmap)
            
        except Exception as e:
            self.image_preview.setText(f"Error displaying image: {e}")
            self.hq_button.setEnabled(False)

    def toggle_feature_visibility(self, feature_id, is_visible):
        """
        OPTIMIZED: Toggles visibility using debounced refresh for better performance.
        NOW WITH FILTER CHECK: Reapplies active filter when manual visibility changes.
        """
        if not self.layer or not self.layer.isValid():
            return

        # Start editing once
        if not self.layer.isEditable():
            self.layer.startEditing()
        
        # Get current feature to check icon state
        feature = self.layer.getFeature(feature_id)
        if not feature.isValid():
            return
            
        current_icon = feature.attribute('svg_icon')
        
        # Update visible attribute
        visible_idx = self.layer.fields().indexOf('visible')
        if visible_idx >= 0:
            self.layer.changeAttributeValue(feature_id, visible_idx, is_visible)
        
        # CHECK FILTER STATUS when trying to make photo visible
        passes_filter = True
        if hasattr(self, 'date_time_filter') and self.date_time_filter:
            feature = self.layer.getFeature(feature_id)
            passes_filter = self.date_time_filter.check_single_feature(self.layer, feature)
        
        # Final visibility = manual visibility AND filter status
        actually_visible = is_visible and passes_filter
        
        # Show warning if trying to make visible but filtered out
        if is_visible and not passes_filter:
            if hasattr(self, 'iface') and self.iface:
                photo_time = feature.attribute('photo_time')
                self.iface.messageBar().pushMessage(
                    "Filtered Photo",
                    f"Photo is hidden by active date/time filter (time={photo_time})",
                    level=Qgis.Warning,
                    duration=3
                )
        
        # Handle icon switching based on ACTUAL visibility (considering filter)
        svg_icon_idx = self.layer.fields().indexOf('svg_icon')
        svg_icon_backup_idx = self.layer.fields().indexOf('svg_icon_backup')
        if svg_icon_idx >= 0:
            if actually_visible and current_icon == 'Invisible.svg':
                restored_icon = None
                if svg_icon_backup_idx >= 0:
                    restored_icon = feature.attribute('svg_icon_backup')
                if restored_icon:
                    self.layer.changeAttributeValue(feature_id, svg_icon_idx, restored_icon)
                else:
                    self.layer.changeAttributeValue(feature_id, svg_icon_idx, '0.svg')
            elif not actually_visible and current_icon != 'Invisible.svg':
                if svg_icon_backup_idx >= 0 and current_icon:
                    self.layer.changeAttributeValue(feature_id, svg_icon_backup_idx, current_icon)
                self.layer.changeAttributeValue(feature_id, svg_icon_idx, 'Invisible.svg')
        
        # Update selection state based on ACTUAL visibility (selected = hidden)
        current_selection = list(self.layer.selectedFeatureIds())
        if actually_visible and feature_id in current_selection:
            # Remove from selection (make visible)
            current_selection.remove(feature_id)
        elif not actually_visible and feature_id not in current_selection:
            # Add to selection (make invisible)
            current_selection.append(feature_id)
        
        # Apply selection changes - block signals to prevent on_selection_changed
        # from duplicating the work we already did above
        self.layer.blockSignals(True)
        self.layer.selectByIds(current_selection)
        self.layer.blockSignals(False)
        
        # Commit all changes at once
        if self.layer.isEditable():
            self.layer.commitChanges()
        
        # CRITICAL: Use debounced refresh instead of immediate refresh
        # This batches multiple rapid toggles into a single refresh
        self._pending_refresh = True
        self._refresh_timer.start(100)
        
        # Emit signal to notify other components (e.g., Photo Edit Dialog) about visibility change
        self.visibilityChangedFromList.emit(feature_id, is_visible)
    
    def _do_deferred_refresh(self):
        """Execute the deferred refresh after debounce period."""
        if not self._pending_refresh:
            return
        
        if self.layer and self.layer.isValid():
            self.layer.triggerRepaint()
            self.iface.mapCanvas().refresh()
        
        self._pending_refresh = False

    def _populate_coordinate_fields(self, feature):
        """Populates the coordinate input fields with the feature's current values."""
        if not feature or not feature.isValid():
            self.lon_edit.clear()
            self.lat_edit.clear()
            self.direction_edit.clear()
            self.photo_time_edit.clear()
            return
            
        # Get current values from the feature
        lat = feature.attribute('latitude')
        lon = feature.attribute('longitude')
        direction = feature.attribute('direction')
        photo_time = feature.attribute('photo_time') if self.layer.fields().indexOf('photo_time') >= 0 else ''
        label_text = feature.attribute('label_text') if self.layer.fields().indexOf('label_text') >= 0 else ''
        
        # Populate the fields, handling None values
        self.lat_edit.setText(str(lat) if lat is not None else "")
        self.lon_edit.setText(str(lon) if lon is not None else "")
        self.direction_edit.setText(str(direction) if direction is not None else "")
        self.photo_time_edit.setText(str(photo_time) if photo_time else "")
        self.label_text_edit.setText(label_text if label_text else "")
    
    def set_available_groups(self, groups):
        """Set the list of available groups for the dropdown."""
        current_group = self.group_combo.currentText()
        self.group_combo.blockSignals(True)  # Block signals while updating
        self.group_combo.clear()
        self.group_combo.addItem("")  # Add empty option for no group
        for group in groups:
            self.group_combo.addItem(group)
        
        # Restore previous selection if still available
        if current_group:
            index = self.group_combo.findText(current_group)
            if index >= 0:
                self.group_combo.setCurrentIndex(index)
        
        self.group_combo.blockSignals(False)
    
    def _on_group_changed(self, group_name):
        """Handle group dropdown changes."""
        if self.current_feature_id is not None and self.layer and self.layer.isValid():
            group_field_idx = self.layer.fields().indexOf('group')
            if group_field_idx >= 0:
                if not self.layer.isEditable():
                    self.layer.startEditing()
                
                self.layer.changeAttributeValue(self.current_feature_id, group_field_idx, group_name)
                self.layer.commitChanges()
                
                # Refresh the list to show updated group
                self.populate_list()
                
                from qgis.core import QgsMessageLog, Qgis
                QgsMessageLog.logMessage(
                    f"Updated group for feature {self.current_feature_id} to '{group_name}'",
                    'Photo Plugin', Qgis.Info
                )

    def _on_label_changed(self):
        """Handle label settings changes."""
        if self.current_feature_id is not None and self.layer and self.layer.isValid():
            label_visible_idx = self.layer.fields().indexOf('label_visible')
            label_offset_x_idx = self.layer.fields().indexOf('label_offset_x')
            label_offset_y_idx = self.layer.fields().indexOf('label_offset_y')
            
            if label_visible_idx >= 0 and label_offset_x_idx >= 0 and label_offset_y_idx >= 0:
                if not self.layer.isEditable():
                    self.layer.startEditing()
                
                self.layer.changeAttributeValue(self.current_feature_id, label_visible_idx, self.label_visible_checkbox.isChecked())
                self.layer.changeAttributeValue(self.current_feature_id, label_offset_x_idx, self.label_offset_x_spin.value())
                self.layer.changeAttributeValue(self.current_feature_id, label_offset_y_idx, self.label_offset_y_spin.value())
                self.layer.commitChanges()
                
                # Refresh map to update labels
                self.iface.mapCanvas().refresh()

    def _on_update_metadata_click(self):
        """Handles the update metadata button click."""
        if not self.current_feature_id:
            QMessageBox.warning(self, "No Selection", "Please select a photo first.")
            return
            
        # Validate inputs
        try:
            new_lat = float(self.lat_edit.text().strip())
            new_lon = float(self.lon_edit.text().strip())
            new_direction = float(self.direction_edit.text().strip()) if self.direction_edit.text().strip() else None
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter valid numeric values for coordinates and direction.")
            return
            
        # Validate coordinate ranges
        if not (-90 <= new_lat <= 90):
            QMessageBox.warning(self, "Invalid Latitude", "Latitude must be between -90 and 90 degrees.")
            return
        if not (-180 <= new_lon <= 180):
            QMessageBox.warning(self, "Invalid Longitude", "Longitude must be between -180 and 180 degrees.")
            return
        if new_direction is not None and not (0 <= new_direction <= 360):
            QMessageBox.warning(self, "Invalid Direction", "Direction must be between 0 and 360 degrees.")
            return
            
        # Import layer_manager here to avoid circular imports
        from .layer_manager import LayerManager
        from .symbol_renderer import SymbolRenderer
        
        # Get label text
        new_label_text = self.label_text_edit.text()
        
        # Create layer manager instance (we need to get it from the main plugin)
        # For now, we'll emit a signal that the main plugin can handle
        # This requires adding a signal to request metadata updates
        self.updateMetadataRequested.emit(self.current_feature_id, new_lon, new_lat, new_direction)
        
        # Update label text in the layer
        if self.layer and self.layer.isValid():
            if not self.layer.isEditable():
                self.layer.startEditing()
            label_text_idx = self.layer.fields().indexOf('label_text')
            if label_text_idx >= 0:
                self.layer.changeAttributeValue(self.current_feature_id, label_text_idx, new_label_text)
            if self.layer.isEditable():
                self.layer.commitChanges()
            
            # Refresh the photo list to show updated label
            self.populate_list()
            
            self.iface.mapCanvas().refresh()
