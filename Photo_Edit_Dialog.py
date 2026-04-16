# -*- coding: utf-8 -*-
# Copyright (C) 2026 Majid Jazebi
# Web: Geotechzone.com
# All rights reserved.
# This plugin is licensed under GNU GPL v3.
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QDialog, 
    QVBoxLayout, 
    QHBoxLayout, 
    QLabel, 
    QLineEdit, 
    QPushButton, 
    QGroupBox, 
    QGridLayout, 
    QDialogButtonBox,
    QMessageBox # <-- ADDED MISSING IMPORT
)
from qgis.PyQt.QtGui import QPixmap, QImage, QDesktopServices 
from qgis.PyQt.QtCore import Qt, pyqtSignal, QUrl, QCoreApplication
import os

class PhotoEditDialog(QDialog):

    # Define the signal to send updated metadata back to the main plugin
    metadata_updated = pyqtSignal(int, float, float, float) # feat_id, lon, lat, direction
    visibility_changed = pyqtSignal(int, bool) # feat_id, is_visible
    label_text_updated = pyqtSignal(int, str) # feat_id, label_text
    photo_time_updated = pyqtSignal(int, str) # feat_id, photo_time

    def __init__(self, parent=None):
        super(PhotoEditDialog, self).__init__(parent)
        
        self.current_feat_id = -1
        self.current_photo_path = ""
        self.setWindowTitle(self.tr("Edit Photo Metadata"))
        
        # --- UI ELEMENTS ---
        
        self.photo_label = QLabel(self.tr("Photo Preview"))
        self.photo_label.setAlignment(Qt.AlignCenter)
        self.photo_label.setFixedSize(300, 200) # Fixed size for preview
        self.photo_label.setStyleSheet("border: 1px solid gray;")
        
        # Metadata fields
        self.line_lon = QLineEdit()
        self.line_lat = QLineEdit()
        self.line_dir = QLineEdit()
        self.line_photo_time = QLineEdit()  # NEW: Photo time field
        self.line_photo_time.setPlaceholderText(self.tr("YYYY:MM:DD HH:MM:SS"))
        
        # Label text field
        self.line_label = QLineEdit()
        self.line_label.setPlaceholderText(self.tr("Label text (shown on map)"))
        
        # Visibility checkbox
        self.chk_visible = QCheckBox(self.tr("Visible"))
        self.chk_visible.setChecked(True)  # Default to visible
        self.chk_visible.stateChanged.connect(self._on_visibility_changed)
        
        # NEW: Button to open the high-quality original photo
        self.btn_open_original = QPushButton(self.tr("See High quality Photo"))
        self.btn_open_original.clicked.connect(self.open_original_photo)
        
        # Button Box (OK/Cancel)
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        
        # Rename the 'Ok' button to 'Update' for clarity in this context
        self.update_button = self.buttonBox.button(QDialogButtonBox.Ok)
        self.update_button.setText(self.tr("Update"))
        
        # Connect signals
        # IMPORTANT: Connect to self.update_and_stay_open instead of self.accept or self.done
        self.buttonBox.accepted.connect(self.update_and_stay_open) 
        self.buttonBox.rejected.connect(self.reject)
        
        # --- LAYOUT ---
        
        # Group Box for Metadata
        meta_group = QGroupBox(self.tr("Coordinates & Direction"))
        meta_layout = QGridLayout()
        meta_layout.addWidget(QLabel(self.tr("Longitude:")), 0, 0)
        meta_layout.addWidget(self.line_lon, 0, 1)
        meta_layout.addWidget(QLabel(self.tr("Latitude:")), 1, 0)
        meta_layout.addWidget(self.line_lat, 1, 1)
        meta_layout.addWidget(QLabel(self.tr("Direction (0-360°):")), 2, 0)
        meta_layout.addWidget(self.line_dir, 2, 1)
        meta_layout.addWidget(QLabel(self.tr("Photo Time:")), 3, 0)
        meta_layout.addWidget(self.line_photo_time, 3, 1)
        meta_layout.addWidget(QLabel(self.tr("Label:")), 4, 0)
        meta_layout.addWidget(self.line_label, 4, 1)
        meta_layout.addWidget(self.chk_visible, 5, 0, 1, 2)  # Span 2 columns
        meta_group.setLayout(meta_layout)
        
        # Main Layout
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.photo_label)
        main_layout.addWidget(self.btn_open_original) # NEW BUTTON
        main_layout.addWidget(meta_group)
        main_layout.addWidget(self.buttonBox)
        
        self.setLayout(main_layout)

    def tr(self, message):
        """Get the translation for a string using Qt translation API."""
        return QCoreApplication.translate('PhotoEditDialog', message)

    def display_photo_and_metadata(self, feat_id, path, lon, lat, direction, is_visible=True, label_text='', photo_time=''):
        """Loads and displays the photo preview and metadata."""
        self.current_feat_id = feat_id
        self.current_photo_path = path
        
        # Set Metadata
        self.line_lon.setText(str(lon))
        self.line_lat.setText(str(lat))
        self.line_dir.setText(str(direction))
        self.line_photo_time.setText(str(photo_time) if photo_time else '')  # NEW
        self.chk_visible.setChecked(is_visible)
        self.line_label.setText(label_text if label_text else os.path.basename(path))
        
        # Load Photo Preview
        if os.path.exists(path):
            try:
                pixmap = QPixmap(path)
                if not pixmap.isNull():
                    # Scale the pixmap to fit the label size while maintaining aspect ratio
                    scaled_pixmap = pixmap.scaled(self.photo_label.size(), 
                                                  Qt.KeepAspectRatio, 
                                                  Qt.SmoothTransformation)
                    self.photo_label.setPixmap(scaled_pixmap)
                    self.photo_label.setText("") # Clear "Photo Preview" text
                else:
                    self.photo_label.setText(self.tr("Could not load image file."))
            except Exception as e:
                self.photo_label.setText(self.tr(f"Error loading image: {e}"))
        else:
            self.photo_label.setText(self.tr("File not found."))
            
    def open_original_photo(self):
        """
        Opens the high-quality original photo file using the system's default 
        image viewer/browser.
        """
        if self.current_photo_path and os.path.exists(self.current_photo_path):
            try:
                # Use QDesktopServices to open the file with the default application
                QDesktopServices.openUrl(QUrl.fromLocalFile(self.current_photo_path))
            except Exception as e:
                # Handle cases where the default application fails to launch
                QMessageBox.critical(self, self.tr("Open Error"), self.tr(f"Failed to open photo: {e}"))
        else:
            QMessageBox.warning(self, self.tr("Open Error"), self.tr("Photo file path is invalid or empty."))

    def update_and_stay_open(self):
        """
        Handles the 'Update' button click: emits the signal but keeps the 
        dialog open for further edits.
        """
        try:
            # 1. Validate and Parse Input
            new_lon = float(self.line_lon.text())
            new_lat = float(self.line_lat.text())
            new_direction = float(self.line_dir.text())

            # 2. Emit Signal to Main Plugin
            if self.current_feat_id != -1:
                self.metadata_updated.emit(
                    self.current_feat_id, 
                    new_lon, 
                    new_lat, 
                    new_direction
                )
                # Also emit label text update
                new_label = self.line_label.text()
                
                # Emit photo time update
                new_photo_time = self.line_photo_time.text()
                self.photo_time_updated.emit(self.current_feat_id, new_photo_time)
                self.label_text_updated.emit(self.current_feat_id, new_label)
            
            # NOTE: DO NOT CALL self.accept() or self.close()
            # The dialog stays open as requested.

        except ValueError:
            QMessageBox.critical(self, self.tr("Input Error"), self.tr("Please enter valid numerical values for Longitude, Latitude, and Direction."))
        except Exception as e:
            QMessageBox.critical(self, self.tr("Update Error"), self.tr(f"An unexpected error occurred: {e}"))
            
    def _on_visibility_changed(self, state):
        """Handle visibility checkbox state changes."""
        if self.current_feat_id != -1:
            is_visible = state == Qt.Checked
            self.visibility_changed.emit(self.current_feat_id, is_visible)
    
    def update_visibility_checkbox(self, feat_id, is_visible):
        """
        Updates the visibility checkbox state without triggering the signal.
        Used to sync the checkbox when visibility changes from external sources.
        """
        if self.current_feat_id == feat_id:
            # Block signals to prevent recursive updates
            self.chk_visible.blockSignals(True)
            self.chk_visible.setChecked(is_visible)
            self.chk_visible.blockSignals(False)
            
    def reject(self):
        """Overrides reject to close the window gracefully."""
        super(PhotoEditDialog, self).reject()