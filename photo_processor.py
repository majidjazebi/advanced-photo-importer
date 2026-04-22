# -*- coding: utf-8 -*-
# Copyright (C) 2026 Majid Jazebi
# Web: Geotechzone.com
# All rights reserved.
# This plugin is licensed under GNU GPL v3.
"""
Photo Processing Manager for Advanced Photo Importer
Handles photo import and processing operations.
"""

import os
from qgis.PyQt.QtWidgets import QApplication
from qgis.core import Qgis
from .progress_status_dialog import ProgressStatusDialog


class PhotoProcessor:
    """Manages photo import and processing operations."""

    def __init__(self, iface, layer_manager, exif_handler, symbol_renderer, group_manager=None):
        self.iface = iface
        self.layer_manager = layer_manager
        self.exif_handler = exif_handler
        self.symbol_renderer = symbol_renderer
        self.group_manager = group_manager

    def _resolve_svg_icon(self, direction_val):
        """Return the correct svg_icon name for a feature being created.

        If a camera icon is selected and direction display is enabled but
        direction_val is None, returns the 'No arrow/CamX.svg' virtual name.
        If direction display is disabled, always returns the no-arrow variant.
        Defaults to None (caller will use '0.svg') when no camera icon is selected.
        """
        selected = self.symbol_renderer.selected_icon
        if not selected:
            return None  # add_point_to_map will default to '0.svg'
        include_dir = self.symbol_renderer.include_direction
        if include_dir and not self.symbol_renderer._direction_is_null(direction_val):
            return selected  # has direction → use normal camera icon with rotation
        # No direction, or direction display is off → use no-arrow variant
        no_arrow = self.symbol_renderer._get_no_arrow_name(selected)
        return no_arrow if no_arrow else selected

    @staticmethod
    def _build_import_summary(total_count, exif_count, imported_count):
        """Build a multi-line, user-friendly import summary."""
        return (
            f"Total files in selection: {total_count}\n"
            f"Files with EXIF/GPS data: {exif_count}\n"
            f"Photos imported: {imported_count}"
        )

    def process_photos_in_list(self, filepaths, dlg, photo_layer, photo_list_manager, create_point_layer_func):
        """Processes a list of photo files or photo data dicts."""
        if not filepaths:
            return

        if isinstance(filepaths[0], dict):
            # It's photos_data from Excel import
            for photo in filepaths:
                is_visible = photo.get('is_visible', True)
                group_name = photo.get('group', '')
                photo_time = photo.get('photo_time', '')
                svg_icon_for_feature = self._resolve_svg_icon(photo['direction'])
                self.layer_manager.add_point_to_map(photo_layer, photo['lat'], photo['lon'], photo['path'], photo['direction'], is_visible, group_name, '', photo_time, svg_icon_filename=svg_icon_for_feature)
            return

        # Get the group name from the dialog
        group_name = dlg.get_group_name() if hasattr(dlg, 'get_group_name') else ''
        
        # Auto-add the group to group manager if it doesn't exist
        if group_name and self.group_manager:
            self.group_manager.add_group(group_name)

        # Always create temporary layer (output layer option removed)
        output_uri = None

        layer = create_point_layer_func(output_uri)
        if not layer:
            return

        if not layer.isEditable():
            layer.startEditing()

        imported_count = 0
        exif_count = 0
        total_count = len(filepaths)
        processed_count = 0
        skipped_no_exif = []
        imported_photos_data = []  # Collect data for Excel update

        processing_message_bar_item = None
        progress_dialog = ProgressStatusDialog("Photo Import Progress", dlg)
        progress_dialog.show()
        QApplication.processEvents()

        for i, filepath in enumerate(filepaths):
            # Pop previous message before pushing new one
            if processing_message_bar_item:
                self.iface.messageBar().popWidget(processing_message_bar_item)
            processing_message_bar_item = self.iface.messageBar().pushMessage(
                "Processing",
                f"File {i+1} of {total_count}: {os.path.basename(filepath)}",
                level=Qgis.Info,
                duration=0
            )
            exif_data = self.exif_handler.extract_gps_and_direction(filepath)
            if exif_data['latitude'] is not None and exif_data['longitude'] is not None:
                exif_count += 1
                photo_time = exif_data.get('photo_time', '')
                svg_icon_for_feature = self._resolve_svg_icon(exif_data['direction'])
                added_feature = self.layer_manager.add_point_to_map(
                    layer,
                    exif_data['latitude'],
                    exif_data['longitude'],
                    filepath,
                    exif_data['direction'],
                    True,
                    group_name,
                    '',
                    photo_time,
                    svg_icon_filename=svg_icon_for_feature
                )
                if added_feature is not None:
                    imported_count += 1

                # Collect data for Excel
                imported_photos_data.append({
                    'path': filepath,
                    'x': exif_data['longitude'],
                    'y': exif_data['latitude'],
                    'direction': exif_data['direction'],
                    'photo_time': photo_time
                })
            else:
                skipped_no_exif.append(filepath)
                progress_dialog.append_skipped_file(filepath)

            processed_count = i + 1
            progress_dialog.update_progress(
                processed_count,
                total_count,
                f"Importing photos... Imported so far: {imported_count}",
            )
            QApplication.processEvents()

        if layer.isEditable():
             layer.commitChanges()

             if output_uri:
                  # Restart editing if using an external layer that needs manual commits
                  layer.startEditing()

        self.symbol_renderer.update_layer_symbol_manually(layer, self.iface)
        self.iface.mapCanvas().refresh()

        summary_text = self._build_import_summary(processed_count, exif_count, imported_count)
        if imported_count > 0:
            if hasattr(dlg, 'set_import_status'):
                dlg.set_import_status(True, f"✔ Import completed.\n{summary_text}")
            expanded_extent = self.layer_manager.get_expanded_extent_for_zoom(self.iface, layer, layer.extent())
            if expanded_extent:
                self.iface.mapCanvas().setExtent(expanded_extent)
                self.iface.mapCanvas().refresh()

            # --- NEW: Update the photo list manager after import ---
            if photo_list_manager:
                photo_list_manager.populate_list()

            # Update Excel file with imported photos
            if imported_photos_data:
                from .excel_manager import ExcelManager
                excel_manager = ExcelManager(self.iface)
                excel_manager._update_excel_file(imported_photos_data)

        else:
             if hasattr(dlg, 'set_import_status'):
                dlg.set_import_status(True, f"⚠ Import finished with no imported photos.\n{summary_text}")

        if processing_message_bar_item:
            self.iface.messageBar().popWidget(processing_message_bar_item)
        if progress_dialog:
            progress_dialog.update_progress(processed_count, total_count, "Finalizing...")
            progress_dialog.set_summary_text(summary_text)
            progress_dialog.finish(
                f"Done. Imported {imported_count} of {processed_count} processed files.",
                skipped_no_exif,
            )
