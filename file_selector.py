# -*- coding: utf-8 -*-
# Copyright (C) 2026 Majid Jazebi
# Web: Geotechzone.com
# All rights reserved.
# This plugin is licensed under GNU GPL v3.
"""
File Selection Manager for Advanced Photo Importer
Handles file and folder selection operations.
"""

import os
from qgis.PyQt.QtWidgets import QFileDialog, QMessageBox


class FileSelector:
    """Manages file and folder selection operations."""

    def __init__(self, iface, dlg):
        self.iface = iface
        self.dlg = dlg

    def select_photo(self):
        """Opens a file dialog to select a single photo file."""
        # Check if group name is filled
        if hasattr(self.dlg, 'get_group_name'):
            group_name = self.dlg.get_group_name()
            if not group_name:
                QMessageBox.warning(
                    self.dlg,
                    "Group Name Required",
                    "Please enter a group name before selecting photos."
                )
                return []
        
        file_filter = "JPG/JPEG Files (*.jpg *.jpeg);;All Files (*.*)"
        filepath, _ = QFileDialog.getOpenFileName(
            self.dlg, "Select Photo File", "", file_filter
        )
        if filepath:
            self.dlg.lineEdit_path.setText(filepath)

            # Assuming the dialog has this label
            if hasattr(self.dlg, 'set_import_status'):
                self.dlg.set_import_status(True, "\u2714\u2002Ready \u2014 single file selected. Click Import to proceed.")
            elif hasattr(self.dlg, 'label_coordinate'):
                self.dlg.label_coordinate.setText("Status: Ready to import single file.")

            return [filepath]
        return []

    def select_folder(self):
        """Opens a folder dialog to select a directory containing photos."""
        # Check if group name is filled
        if hasattr(self.dlg, 'get_group_name'):
            group_name = self.dlg.get_group_name()
            if not group_name:
                QMessageBox.warning(
                    self.dlg,
                    "Group Name Required",
                    "Please enter a group name before selecting photos."
                )
                return []
        
        folder_path = QFileDialog.getExistingDirectory(
            self.dlg, "Select Photo Folder", ""
        )
        if folder_path:
            self.dlg.lineEdit_path.setText(folder_path)

            # Check if subfolder scanning is enabled
            include_subfolders = False
            if hasattr(self.dlg, 'checkBox_include_subfolders'):
                include_subfolders = self.dlg.checkBox_include_subfolders.isChecked()

            photo_files = []
            
            if include_subfolders:
                # Recursively scan all subfolders
                for root, dirs, files in os.walk(folder_path):
                    for file in files:
                        if file.lower().endswith(('.jpg', '.jpeg')):
                            photo_files.append(os.path.join(root, file))
                
                # Assuming the dialog has this label
                if hasattr(self.dlg, 'set_import_status'):
                    self.dlg.set_import_status(True, f"\u2714\u2002Ready \u2014 {len(photo_files)} photos found (including subfolders). Click Import to proceed.")
                elif hasattr(self.dlg, 'label_coordinate'):
                    self.dlg.label_coordinate.setText(f"Status: Ready to import folder with subfolders ({len(photo_files)} photos found).")
            else:
                # Only scan the selected folder (not subfolders)
                for item in os.listdir(folder_path):
                    if item.lower().endswith(('.jpg', '.jpeg')):
                        photo_files.append(os.path.join(folder_path, item))
                
                # Assuming the dialog has this label
                if hasattr(self.dlg, 'set_import_status'):
                    self.dlg.set_import_status(True, f"\u2714\u2002Ready \u2014 {len(photo_files)} photos found. Click Import to proceed.")
                elif hasattr(self.dlg, 'label_coordinate'):
                    self.dlg.label_coordinate.setText(f"Status: Ready to import folder ({len(photo_files)} photos found).")

            if photo_files:
                return photo_files
            else:
                QMessageBox.warning(self.dlg, "Warning", "No JPG/JPEG files found in the selected folder.")
                return []
        return []

    def select_output_shapefile(self):
        """Opens a file dialog to select an existing Shapefile for output."""
        file_filter = "Shapefile (*.shp);;All Files (*.*)"
        filepath, _ = QFileDialog.getOpenFileName(
            self.dlg, "Select Output Shapefile", "", file_filter
        )
        if filepath and hasattr(self.dlg, 'lineEdit_output_path'):
            self.dlg.lineEdit_output_path.setText(filepath)

            # Assuming the dialog has a method for updating the display
            if hasattr(self.dlg, 'update_output_path_display'):
                self.dlg.update_output_path_display(filepath)
