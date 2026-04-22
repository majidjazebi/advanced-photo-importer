# -*- coding: utf-8 -*-
# Copyright (C) 2026 Majid Jazebi
# Web: Geotechzone.com
# All rights reserved.
# This plugin is licensed under GNU GPL v3.
"""
Advanced Photo Importer - QGIS Plugin
Main plugin handler that coordinates photo import, visualization, and editing.
"""

from qgis.PyQt.QtCore import (
    QSettings,
    QTranslator,
    QCoreApplication,
    QDateTime,
)
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import (
    QAction,
    QFileDialog,
    QMessageBox,
    QToolBar,
)
import os.path
import os
import json
import warnings
from datetime import datetime

# Excel import/export (optional — required only for Excel export/import features)
from .dependency_manager import safe_import

_openpyxl = safe_import("openpyxl")
EXCEL_AVAILABLE = _openpyxl is not None

if EXCEL_AVAILABLE:
    from openpyxl import Workbook, load_workbook
    from openpyxl.styles import Font, Alignment

# QGIS Core Imports
from qgis.core import (
    QgsMessageLog,
    Qgis,
    QgsProject,
    QgsMapLayer,
)

# Initialize Qt resources from file resources.py
try:
    from .resources import *
except ImportError:
    pass

# Import the code for the dialogs
from .Advanced_Photo_Importer_dialog import AdvancedPhotoImporterDialog
from .Photo_Edit_Dialog import PhotoEditDialog

# Import modular components
from .photo_list_widgets import PhotoListManager
from .map_tools import OpenPhotoMapTool
from .qt_compat import DocumentsLocation
from .symbol_renderer import SymbolRenderer
from .exif_handler import ExifHandler
from .layer_manager import LayerManager
from .excel_manager import ExcelManager
from .file_selector import FileSelector
from .photo_processor import PhotoProcessor
from .settings_manager import SettingsManager
from .feature_manager import FeatureManager
from .ui_manager import UIManager
from .label_manager import LabelManager
from .date_time_filter import DateTimeFilter


# --------------------------------------------------------------------------------------
# --- MAIN PLUGIN CLASS ---
# --------------------------------------------------------------------------------------

class AdvancedPhotoImporter:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor."""
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)

        self.mandatory_icons_dir = os.path.join(self.plugin_dir, 'icons', '1-Mandatory')
        self.camera_icons_dir = os.path.join(self.plugin_dir, 'icons', '2-Cameras')

        self.see_photo_icon_path = os.path.join(self.mandatory_icons_dir, 'see_photo.svg')
        self.upload_photos_icon_path = os.path.join(self.mandatory_icons_dir, 'upload_photos.svg')
        self.default_symbol_path = os.path.join(self.mandatory_icons_dir, '0.svg')

        # Initialize modular components
        self.symbol_renderer = SymbolRenderer(self.mandatory_icons_dir, self.default_symbol_path, self.camera_icons_dir)
        self.exif_handler = ExifHandler()
        self.layer_manager = LayerManager(self.symbol_renderer)
        self.excel_manager = ExcelManager(self.iface, main_plugin=self)
        self.label_manager = LabelManager(self.iface)
        self.date_time_filter = DateTimeFilter(self.iface)  # NEW: Date & Time Filter module

        self.click_tolerance_m = 5.0
        self.layer_save_path = None  # NEW: Layer save location

        self.photo_toolbar = None

        # --- NEW DIALOG INSTANCE ---
        self.photo_edit_dlg = PhotoEditDialog()
        self.photo_edit_dlg.metadata_updated.connect(self.update_feature_metadata)
        self.photo_edit_dlg.visibility_changed.connect(self.update_feature_visibility)
        self.photo_edit_dlg.label_text_updated.connect(self.update_feature_label_text)
        self.photo_edit_dlg.photo_time_updated.connect(self.update_feature_photo_time)
        # ---------------------------

        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'AdvancedPhotoImporter_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            QCoreApplication.installTranslator(self.translator)

        self.actions = []
        self.menu = self.tr(u'&Advanced Photo Importer')
        self.first_start = None
        self.photo_layer = None
        self.open_photo_tool = None
        self.dlg = None
        self.photo_list_manager = None

    def tr(self, message):
        """Get the translation for a string using Qt translation API."""
        return QCoreApplication.translate('AdvancedPhotoImporter', message)

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None,
        checkable=False,
        toolbar_target=None):
        """Add an action, handling placement in menus, toolbars, or a specific QToolBar."""
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)
        action.setCheckable(checkable)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if toolbar_target:
            toolbar_target.addAction(action)
        elif add_to_toolbar:
            self.iface.addToolBarIcon(action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        # 1. Dialog action (in Plugins Menu and Plugins Toolbar)
        icon_path_dialog = ':/plugins/advanced_photo_importer/icon.png'
        self.action_dialog = self.add_action(
            icon_path_dialog,
            text=self.tr(u'Link Photos to point'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # Find the QGIS main map navigation toolbar
        main_toolbar = self.iface.mainWindow().findChild(QToolBar, "mActionPan")

        if not main_toolbar:
            main_toolbar = self.iface.addToolBar(self.tr('Photo Tools'))

        self.photo_toolbar = main_toolbar

        # 2. Upload Photos Action (Opens Dialog)
        icon_path_upload = self.upload_photos_icon_path
        self.action_upload = self.add_action(
            icon_path_upload,
            text=self.tr(u'Upload Photos'),
            callback=self.run,
            add_to_menu=False,
            add_to_toolbar=False,
            parent=self.iface.mainWindow(),
            toolbar_target=self.photo_toolbar)

        # 3. See Photo action
        icon_path_photo = self.see_photo_icon_path
        self.action_photo = self.add_action(
            icon_path_photo,
            text=self.tr(u'See Photo'),
            callback=self.activate_open_photo_tool,
            add_to_menu=False,
            add_to_toolbar=False,
            checkable=True,
            parent=self.iface.mainWindow(),
            toolbar_target=self.photo_toolbar)

        # Export and Import actions removed from toolbar (still available in dialog)
        
        self.open_photo_tool = OpenPhotoMapTool(self.iface.mapCanvas(), self)

        self.first_start = True
        
        # Connect to layer styleChanged signal to sync label settings
        QgsProject.instance().layerWillBeRemoved.connect(self._on_layer_removed)

    def _on_layer_removed(self, layer_id):
        """Clear photo list and disconnect from signals when photo layer is removed."""
        try:
            # Check if the removed layer is our photo layer
            if hasattr(self, 'photo_layer') and self.photo_layer is not None:
                try:
                    if self.photo_layer.id() == layer_id:
                        # Disconnect from styleChanged signal
                        self.photo_layer.styleChanged.disconnect(self._sync_label_settings_from_layer)
                        
                        # Clear the photo list
                        if hasattr(self, 'dlg') and self.dlg and hasattr(self.dlg, 'listWidget_photos'):
                            self.dlg.listWidget_photos.clear()
                            QgsMessageLog.logMessage(
                                "[LAYER] Photo layer deleted - cleared photo list",
                                'Photo Plugin',
                                Qgis.Info
                            )
                        
                        # Reset photo_layer reference
                        self.photo_layer = None
                        self.layer_save_path = None
                        
                except (RuntimeError, TypeError, AttributeError):
                    # Layer object has already been deleted or is invalid
                    pass
        except Exception as e:
            # Catch any other unexpected errors and keep plugin responsive
            QgsMessageLog.logMessage(
                f"[LAYER] Unexpected error in _on_layer_removed: {e}",
                'Photo Plugin',
                Qgis.Warning
            )
    
    def _sync_label_settings_from_layer(self):
        """Sync label settings from layer properties to plugin dialog."""
        if not self.photo_layer or not self.photo_layer.isValid():
            return
        
        # Restore plugin-specific settings from layer custom properties
        if hasattr(self, 'dlg') and self.dlg:
            # Restore click tolerance
            tolerance = self.photo_layer.customProperty('photo_plugin_tolerance')
            if tolerance is not None and hasattr(self.dlg, 'spinBox_tolerance'):
                self.dlg.spinBox_tolerance.setValue(int(float(tolerance)))
                self.click_tolerance_m = float(tolerance)
            
            # Restore icon size
            icon_size = self.photo_layer.customProperty('photo_plugin_icon_size')
            if icon_size is not None and hasattr(self.dlg, 'spinBox_icon_size'):
                self.dlg.spinBox_icon_size.setValue(int(icon_size))
            
            # Restore show direction
            show_direction = self.photo_layer.customProperty('photo_plugin_show_direction')
            if show_direction is not None and hasattr(self.dlg, 'checkBox_show_direction'):
                is_checked = show_direction in ['true', 'True', True, 1, '1']
                self.dlg.checkBox_show_direction.setChecked(is_checked)
                self.symbol_renderer.set_include_direction(is_checked)
            
            # Restore icon appearance
            icon_appearance = self.photo_layer.customProperty('photo_plugin_icon_appearance')
            if icon_appearance and hasattr(self.dlg, 'comboBox_icon_appearance'):
                combo = self.dlg.comboBox_icon_appearance
                for i in range(combo.count()):
                    if combo.itemData(i) == icon_appearance:
                        combo.setCurrentIndex(i)
                        break
        
        # Get labeling settings from the layer
        labeling = self.photo_layer.labeling()
        if not labeling or not hasattr(self.dlg, 'spinBox_font_size'):
            return
        
        try:
            from qgis.core import QgsVectorLayerSimpleLabeling
            if isinstance(labeling, QgsVectorLayerSimpleLabeling):
                settings = labeling.settings()
                text_format = settings.format()
                
                # Update dialog with layer settings
                font = text_format.font()
                self.dlg.spinBox_font_size.setValue(text_format.size())
                
                if hasattr(self.dlg, 'checkBox_font_bold'):
                    self.dlg.checkBox_font_bold.setChecked(font.bold())
                
                if hasattr(self.dlg, 'font_color'):
                    color = text_format.color()
                    self.dlg.font_color = color
                    self.dlg.pushButton_font_color.setStyleSheet(f"background-color: {color.name()};")
                
                if hasattr(self.dlg, 'slider_font_opacity'):
                    opacity = int(text_format.opacity() * 100)
                    self.dlg.slider_font_opacity.setValue(opacity)
                
                # Update buffer settings
                buffer_settings = text_format.buffer()
                if buffer_settings.enabled():
                    if hasattr(self.dlg, 'spinBox_buffer_size'):
                        self.dlg.spinBox_buffer_size.setValue(buffer_settings.size())
                    
                    if hasattr(self.dlg, 'buffer_color'):
                        buffer_color = buffer_settings.color()
                        self.dlg.buffer_color = buffer_color
                        self.dlg.pushButton_buffer_color.setStyleSheet(f"background-color: {buffer_color.name()};")
                    
                    if hasattr(self.dlg, 'slider_buffer_opacity'):
                        buffer_opacity = int(buffer_settings.opacity() * 100)
                        self.dlg.slider_buffer_opacity.setValue(buffer_opacity)
                
                # Update label manager
                self.label_manager.update_label_style(
                    font_size=text_format.size(),
                    font_bold=font.bold(),
                    font_color=text_format.color(),
                    buffer_size=buffer_settings.size() if buffer_settings.enabled() else None,
                    buffer_color=buffer_settings.color() if buffer_settings.enabled() else None
                )
                
                QgsMessageLog.logMessage(
                    "Label settings synced from layer properties to plugin dialog",
                    'Photo Plugin',
                    Qgis.Info
                )
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Failed to sync label settings: {str(e)}",
                'Photo Plugin',
                Qgis.Warning
            )

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""

        if hasattr(self, 'action_photo') and self.action_photo:
            if self.photo_toolbar:
                self.photo_toolbar.removeAction(self.action_photo)
            if self.action_photo in self.actions: self.actions.remove(self.action_photo)

        if hasattr(self, 'action_upload') and self.action_upload:
            if self.photo_toolbar:
                self.photo_toolbar.removeAction(self.action_upload)
            if self.action_upload in self.actions: self.actions.remove(self.action_upload)

        if hasattr(self, 'action_dialog') and self.action_dialog:
             self.iface.removePluginMenu(
                 self.tr(u'&Advanced Photo Importer'),
                 self.action_dialog)
             self.iface.removeToolBarIcon(self.action_dialog)
             if self.action_dialog in self.actions: self.actions.remove(self.action_dialog)

        if self.iface.mapCanvas().mapTool() == self.open_photo_tool:
             self.iface.mapCanvas().unsetMapTool(self.open_photo_tool)

        if self.photo_toolbar and self.photo_toolbar.windowTitle() == self.tr('Photo Tools'):
            self.iface.mainWindow().removeToolBar(self.photo_toolbar)

    def update_click_tolerance(self, tolerance):
        """Updates the internal click tolerance value."""
        try:
            if hasattr(self, 'settings_manager'):
                self.settings_manager.update_click_tolerance(tolerance)
            else:
                # Fallback if settings_manager not initialized yet
                try:
                    self.click_tolerance_m = float(tolerance)
                except ValueError:
                    from qgis.core import Qgis, QgsMessageLog
                    QgsMessageLog.logMessage("Invalid value for click tolerance. Keeping old value.", 'Photo Plugin', Qgis.Warning)
        except RuntimeError:
            QgsMessageLog.logMessage("[TOLERANCE] Layer has been deleted, skipping tolerance update", 'Photo Plugin', Qgis.Warning)
    
    def update_icon_size(self, size_percentage):
        """Updates the icon size based on percentage."""
        try:
            if not self.photo_layer or not self.photo_layer.isValid():
                self.iface.messageBar().pushMessage(
                    "Warning",
                    "No photo layer available. Please import photos first.",
                    level=Qgis.Warning,
                    duration=3
                )
                return
        except RuntimeError:
            return
        
        self.symbol_renderer.set_icon_size_percentage(size_percentage)
        self.symbol_renderer.update_layer_symbol_manually(self.photo_layer, self.iface)
    
    def update_icon_appearance(self, icon_filename):
        """Updates the icon appearance by changing all photo icons to the selected camera SVG."""
        try:
            if not self.photo_layer or not self.photo_layer.isValid():
                self.iface.messageBar().pushMessage(
                    "Warning",
                    "No photo layer available. Please import photos first.",
                    level=Qgis.Warning,
                    duration=3
                )
                return
        except RuntimeError:
            return
        
        # Remember the selected camera icon for future imports
        self.symbol_renderer.selected_icon = icon_filename
        
        # Start editing
        if not self.photo_layer.isEditable():
            self.photo_layer.startEditing()
        
        # Get the base name without extension (e.g., 'Cam1' from 'Cam1.svg')
        base_icon_name = os.path.splitext(icon_filename)[0]
        
        # Update all features to use the new icon
        svg_icon_idx = self.photo_layer.fields().indexOf('svg_icon')
        svg_icon_backup_idx = self.photo_layer.fields().indexOf('svg_icon_backup')
        if svg_icon_idx < 0:
            QgsMessageLog.logMessage("[ICON APPEARANCE] svg_icon field not found", 'Photo Plugin', Qgis.Warning)
            return
        
        # Determine the no-arrow variant name once (None if unavailable for this icon type)
        no_arrow_name = self.symbol_renderer._get_no_arrow_name(icon_filename)
        include_direction = self.symbol_renderer.include_direction

        def _choose_icon(direction_val):
            """Return the correct svg_icon value: no-arrow variant when direction is absent
            or direction display is disabled, otherwise the normal camera icon."""
            if no_arrow_name and (self.symbol_renderer._direction_is_null(direction_val) or not include_direction):
                return no_arrow_name  # e.g. 'No arrow/Cam1.svg'
            return icon_filename      # e.g. 'Cam1.svg'

        updated_count = 0
        for feature in self.photo_layer.getFeatures():
            current_icon = feature.attribute('svg_icon')
            direction_val = feature.attribute('direction')
            fid = feature.id()
            icon_to_store = _choose_icon(direction_val)
            # If feature is visible, update its svg_icon and backup
            if current_icon and current_icon != 'Invisible.svg':
                self.photo_layer.changeAttributeValue(fid, svg_icon_idx, icon_to_store)
                if svg_icon_backup_idx >= 0:
                    self.photo_layer.changeAttributeValue(fid, svg_icon_backup_idx, icon_to_store)
                updated_count += 1
            else:
                # If feature is currently invisible, update only the backup so it restores
                # to the correct (no-arrow or full) icon when made visible again
                if svg_icon_backup_idx >= 0:
                    self.photo_layer.changeAttributeValue(fid, svg_icon_backup_idx, icon_to_store)
        
        # Commit changes
        self.photo_layer.commitChanges()
        
        # Update the renderer to use the new icon
        self.symbol_renderer.update_layer_symbol_manually(self.photo_layer, self.iface)
        
        # Refresh map
        self.iface.mapCanvas().refresh()
        
        QgsMessageLog.logMessage(f"[ICON APPEARANCE] Updated {updated_count} features to {icon_filename}", 'Photo Plugin', Qgis.Info)
        self.iface.messageBar().pushMessage(
            "Success",
            f"Icon appearance updated to {base_icon_name} ({updated_count} photos)",
            level=Qgis.Success,
            duration=3
        )
    
    def apply_all_settings(self, photo_layer=None):
        """Unified method to apply all settings: tolerance, icon size, and label styling."""
        # Handle the case where photo_layer might be a bool from clicked signal
        if isinstance(photo_layer, bool):
            photo_layer = None
        
        # Use provided layer or fall back to self.photo_layer
        target_layer = photo_layer if photo_layer is not None else self.photo_layer
        
        # If a layer was provided, update self.photo_layer before applying settings
        if photo_layer is not None:
            self.photo_layer = photo_layer
        
        # If target_layer is still None or invalid, try to get it from QGIS project
        if target_layer is None or not target_layer.isValid():
            layers = QgsProject.instance().mapLayersByName("Photo Locations")
            if layers:
                target_layer = layers[0]
                self.photo_layer = target_layer
            else:
                self.iface.messageBar().pushMessage(
                    "Warning",
                    "No photo layer found. Please import photos first.",
                    level=Qgis.Warning,
                    duration=3
                )
                return
        
        # Disconnect styleChanged signal at the START to prevent sync-back during ANY operation
        try:
            if target_layer and target_layer.isValid():
                try:
                    target_layer.styleChanged.disconnect(self._sync_label_settings_from_layer)
                except (TypeError, RuntimeError):
                    pass
        except (RuntimeError, AttributeError):
            pass
        
        # Apply click tolerance
        if hasattr(self.dlg, 'spinBox_tolerance'):
            tolerance = float(self.dlg.spinBox_tolerance.value())
            self.update_click_tolerance(tolerance)
        
        # Apply show direction setting BEFORE renderer updates so it affects rotation
        if hasattr(self.dlg, 'checkBox_show_direction'):
            try:
                show_direction = self.dlg.checkBox_show_direction.isChecked()
                self.symbol_renderer.set_include_direction(show_direction)
            except Exception as e:
                QgsMessageLog.logMessage(
                    f"[SETTINGS] Failed to apply show direction setting: {e}",
                    'Photo Plugin',
                    Qgis.Warning
                )
        
        # Apply icon size
        if hasattr(self.dlg, 'spinBox_icon_size'):
            icon_size = self.dlg.spinBox_icon_size.value()
            self.update_icon_size(icon_size)
        
        # Apply icon appearance
        if hasattr(self.dlg, 'comboBox_icon_appearance'):
            icon_file = self.dlg.comboBox_icon_appearance.currentData()
            if icon_file:
                self.update_icon_appearance(icon_file)
        
        # Apply label styling
        self.apply_label_styling()
        
        # Save plugin settings to layer custom properties
        if self.photo_layer and self.photo_layer.isValid():
            if hasattr(self.dlg, 'spinBox_tolerance'):
                self.photo_layer.setCustomProperty('photo_plugin_tolerance', self.dlg.spinBox_tolerance.value())
            if hasattr(self.dlg, 'spinBox_icon_size'):
                self.photo_layer.setCustomProperty('photo_plugin_icon_size', self.dlg.spinBox_icon_size.value())
            if hasattr(self.dlg, 'checkBox_show_direction'):
                self.photo_layer.setCustomProperty('photo_plugin_show_direction', self.dlg.checkBox_show_direction.isChecked())
            if hasattr(self.dlg, 'comboBox_icon_appearance'):
                icon_file = self.dlg.comboBox_icon_appearance.currentData()
                if icon_file:
                    self.photo_layer.setCustomProperty('photo_plugin_icon_appearance', icon_file)
        
        self.iface.messageBar().pushMessage(
            "Success",
            "All settings applied successfully",
            level=Qgis.Success,
            duration=3
        )
    
    def _detect_existing_photo_layer(self):
        """Detect and reconnect to existing photo layer in the project."""
        for layer_id, layer in QgsProject.instance().mapLayers().items():
            if layer.type() == QgsMapLayer.VectorLayer:
                fields = layer.fields()
                has_path = fields.indexOf('path') >= 0
                has_svg_icon = fields.indexOf('svg_icon') >= 0
                has_direction = fields.indexOf('direction') >= 0
                
                if has_path and has_svg_icon and has_direction:
                    self.photo_layer = layer
                    
                    layer_source = layer.source()
                    if layer.providerType() != 'memory':
                        if '|' in layer_source:
                            self.layer_save_path = layer_source.split('|')[0]
                        else:
                            self.layer_save_path = layer_source
                        
                        if hasattr(self, 'dlg') and self.dlg and hasattr(self.dlg, 'lineEdit_save_location'):
                            self.dlg.lineEdit_save_location.setText(self.layer_save_path)
                    
                    self.symbol_renderer.update_layer_symbol_manually(layer, self.iface)
                    
                    self.iface.messageBar().pushMessage(
                        "Photo Layer Detected",
                        f"Reconnected to existing layer: {layer.name()} ({layer.featureCount()} photos)",
                        level=Qgis.Success,
                        duration=5
                    )
                    break

    def run(self):
        """Run method that performs all the real work and shows the dialog."""
        
        # --- DETECT EXISTING PHOTO LAYER ON FIRST RUN (before dialog creation) ---
        if self.first_start is True:
            self._detect_existing_photo_layer()

        if self.first_start is True:
            self.first_start = False

            self.dlg = AdvancedPhotoImporterDialog(plugin_dir=self.plugin_dir,
                                                 parent=self.iface.mainWindow(),
                                                 initial_tolerance=self.click_tolerance_m)

            # --- INITIALIZE PHOTO LIST MANAGER ---
            self.photo_list_manager = PhotoListManager(self.iface, self.photo_layer, self.dlg, self.date_time_filter)
            
            def safe_update_renderer():
                try:
                    if self.photo_layer and self.photo_layer.isValid():
                        self.symbol_renderer.update_layer_symbol_manually(self.photo_layer, self.iface)
                except RuntimeError:
                    pass  # Layer has been deleted
            
            self.photo_list_manager.updateRendererRequested.connect(safe_update_renderer)
            self.photo_list_manager.updateMetadataRequested.connect(self._on_update_metadata_requested)
            self.photo_list_manager.visibilityChangedFromList.connect(self._on_visibility_changed_from_list)

            # --- INITIALIZE MODULAR MANAGERS ---
            self.file_selector = FileSelector(self.iface, self.dlg)
            self.photo_processor = PhotoProcessor(self.iface, self.layer_manager, self.exif_handler, self.symbol_renderer)
            self.settings_manager = SettingsManager(self.iface, self.symbol_renderer, self.photo_list_manager, self.label_manager)
            self.feature_manager = FeatureManager(self.iface, self.layer_manager, self.photo_list_manager, self.date_time_filter)
            self.ui_manager = UIManager(self.iface, self.dlg, self.photo_list_manager)
            
            # DEBUG: Verify date_time_filter connection
            QgsMessageLog.logMessage(
                f"[INIT DEBUG] feature_manager.date_time_filter is {'CONNECTED' if self.feature_manager.date_time_filter else 'NULL'}",
                'Photo Plugin',
                Qgis.Critical if not self.feature_manager.date_time_filter else Qgis.Info
            )
            if self.feature_manager.date_time_filter:
                QgsMessageLog.logMessage(
                    f"[INIT DEBUG] date_time_filter.filter_active = {self.feature_manager.date_time_filter.filter_active}",
                    'Photo Plugin',
                    Qgis.Info
                )
            self.iface.messageBar().pushMessage(
                "Debug Init",
                f"date_time_filter: {'CONNECTED' if self.feature_manager.date_time_filter else 'NULL'}",
                level=Qgis.Critical if not self.feature_manager.date_time_filter else Qgis.Info,
                duration=5
            )

            # --- INSERT THE PHOTO LIST MANAGER INTO THE DIALOG'S NEW TAB ---
            if hasattr(self.dlg, 'imported_photos_main_layout') and self.dlg.imported_photos_main_layout:
                 # Clear the placeholder label first
                 item = self.dlg.imported_photos_main_layout.takeAt(0)
                 if item and item.widget():
                      item.widget().deleteLater()

                 # Add the actual PhotoListManager widget
                 self.dlg.imported_photos_main_layout.addWidget(self.photo_list_manager)

            # --- CONNECT EXISTING SIGNALS ---
            self.dlg.pushButton_browse.clicked.connect(self.select_photo)
            if hasattr(self.dlg, 'pushButton_browseFolder'):
                self.dlg.pushButton_browseFolder.clicked.connect(self.select_folder)
            
            # Connect save location button (NEW)
            if hasattr(self.dlg, 'pushButton_browse_save_location'):
                self.dlg.pushButton_browse_save_location.clicked.connect(self.select_layer_save_location)

            if hasattr(self.dlg, 'pushButton_browse_output'):
                self.dlg.pushButton_browse_output.clicked.connect(self.select_output_shapefile)

            if hasattr(self.dlg, 'apply_tolerance_clicked'):
                self.dlg.apply_tolerance_clicked.connect(self.update_click_tolerance)

            # Connect export/import signals
            if hasattr(self.dlg, 'export_plugin_state_clicked'):
                self.dlg.export_plugin_state_clicked.connect(self.export_plugin_state)
            if hasattr(self.dlg, 'import_plugin_state_clicked'):
                self.dlg.import_plugin_state_clicked.connect(self.import_plugin_state)
            
            # Connect label styling button
            if hasattr(self.dlg, 'pushButton_apply_label_style'):
                self.dlg.pushButton_apply_label_style.clicked.connect(self.apply_label_styling)
            
            # Connect apply all settings button (CRITICAL - was missing!)
            if hasattr(self.dlg, 'pushButton_apply_all_settings'):
                QgsMessageLog.logMessage("[BUTTON CONNECT] Connecting pushButton_apply_all_settings", 'Photo Plugin', Qgis.Info)
                self.dlg.pushButton_apply_all_settings.clicked.connect(self.apply_all_settings)
                QgsMessageLog.logMessage("[BUTTON CONNECT] Successfully connected pushButton_apply_all_settings", 'Photo Plugin', Qgis.Info)
            else:
                QgsMessageLog.logMessage("[BUTTON CONNECT] ERROR: pushButton_apply_all_settings not found in dialog!", 'Photo Plugin', Qgis.Critical)
            
            # Connect Advanced Setting button
            if hasattr(self.dlg, 'pushButton_advanced_label'):
                self.dlg.pushButton_advanced_label.clicked.connect(self.open_advanced_label_settings)
            
            # Connect date/time filter buttons (NEW)
            if hasattr(self.dlg, 'pushButton_apply_filter'):
                self.dlg.pushButton_apply_filter.clicked.connect(self.apply_date_time_filter)
                QgsMessageLog.logMessage("[BUTTON CONNECT] Connected pushButton_apply_filter", 'Photo Plugin', Qgis.Info)
            
            if hasattr(self.dlg, 'pushButton_remove_filter'):
                self.dlg.pushButton_remove_filter.clicked.connect(self.remove_date_time_filter)
                QgsMessageLog.logMessage("[BUTTON CONNECT] Connected pushButton_remove_filter", 'Photo Plugin', Qgis.Info)

            # --- NEW: Connect tab change to populate list ---
            if hasattr(self.dlg, 'tab_widget'):
                 # Assuming 'Imported Photos' is tab index 2
                 self.dlg.tab_widget.currentChanged.connect(self.handle_tab_change)
            
            # --- SHOW SAVE LOCATION INFO ---
            if hasattr(self.dlg, 'lineEdit_save_location'):
                if self.layer_save_path:
                    # Show the detected or set save path
                    self.dlg.lineEdit_save_location.setText(self.layer_save_path)
                else:
                    # Show placeholder message
                    self.dlg.lineEdit_save_location.setPlaceholderText("Click 'Choose Save Location...' to select where to save photos")
            # --- UPDATE IMPORT STATUS LABEL ---
            if hasattr(self.dlg, 'set_import_status'):
                self.dlg.set_import_status(bool(self.layer_save_path))
            
            # --- UPDATE PHOTO LIST IF LAYER WAS DETECTED ---
            if self.photo_layer and self.photo_layer.isValid():
                QgsMessageLog.logMessage("[RUN] Photo layer exists, updating photo list and syncing settings", 'Photo Plugin', Qgis.Info)
                self.photo_list_manager.setLayer(self.photo_layer)
                self.photo_list_manager.populate_list()
                
                # Sync settings from detected layer to dialog controls
                self._sync_label_settings_from_layer()
                QgsMessageLog.logMessage("[RUN] Settings synced from layer to dialog", 'Photo Plugin', Qgis.Info)

        self.dlg.show()
        self.dlg.exec()

    def handle_tab_change(self, index):
         """Handles tab changes in the main dialog."""
         # Check if photo_layer is valid and not deleted
         valid_layer = None
         if self.photo_layer:
             try:
                 if self.photo_layer.isValid():
                     valid_layer = self.photo_layer
             except RuntimeError:
                 # C++ object has been deleted
                 self.photo_layer = None
         
         self.ui_manager.handle_tab_change(index, valid_layer)

    def update_feature_metadata(self, feat_id, new_lon, new_lat, new_direction):
        """Delegates to feature_manager to update feature metadata."""
        self.feature_manager.update_feature_metadata(self.photo_layer, feat_id, new_lon, new_lat, new_direction)

    def update_feature_visibility(self, feat_id, is_visible):
        """Updates the visibility of a feature and syncs the checkbox in the Imported Photos tab."""
        self.feature_manager.update_feature_visibility(self.photo_layer, feat_id, is_visible, self.symbol_renderer)
        
        # Sync the checkbox state in the Imported Photos tab
        if self.photo_list_manager:
            self.photo_list_manager.update_checkbox_state(feat_id, is_visible)
    
    def _on_visibility_changed_from_list(self, feat_id, is_visible):
        """
        Handler for when visibility is changed from the Imported Photos tab.
        Updates the Photo Edit Dialog if it's open and showing the same feature.
        """
        if self.photo_edit_dlg and self.photo_edit_dlg.isVisible():
            self.photo_edit_dlg.update_visibility_checkbox(feat_id, is_visible)
    
    def update_feature_label_text(self, feat_id, label_text):
        """Updates the label text of a feature."""
        try:
            if not self.photo_layer or not self.photo_layer.isValid():
                QgsMessageLog.logMessage("[UPDATE LABEL] No valid photo layer found", 'Photo Plugin', Qgis.Warning)
                self.iface.messageBar().pushMessage(
                    "Error",
                    "No valid photo layer found. Please import photos first.",
                    level=Qgis.Critical,
                    duration=3
                )
                return
        except RuntimeError:
            QgsMessageLog.logMessage("[UPDATE LABEL] Photo layer has been deleted", 'Photo Plugin', Qgis.Critical)
            self.iface.messageBar().pushMessage(
                "Error",
                "Photo layer has been deleted. Please import photos again.",
                level=Qgis.Critical,
                duration=3
            )
            self.photo_layer = None
            return
        
        if not self.photo_layer.isEditable():
            self.photo_layer.startEditing()
        
        label_text_idx = self.photo_layer.fields().indexOf('label_text')
        if label_text_idx >= 0:
            self.photo_layer.changeAttributeValue(feat_id, label_text_idx, label_text)
        
        if self.photo_layer.isEditable():
            self.photo_layer.commitChanges()
        
        # Refresh the photo list to show updated label text
        if self.photo_list_manager:
            self.photo_list_manager.populate_list()
        
        self.iface.mapCanvas().refresh()
    
    def update_feature_photo_time(self, feat_id, photo_time):
        """Updates the photo time of a feature."""
        try:
            if not self.photo_layer or not self.photo_layer.isValid():
                return
        except RuntimeError:
            QgsMessageLog.logMessage("[UPDATE TIME] Photo layer has been deleted", 'Photo Plugin', Qgis.Warning)
            self.photo_layer = None
            return
        
        if not self.photo_layer.isEditable():
            self.photo_layer.startEditing()
        
        photo_time_idx = self.photo_layer.fields().indexOf('photo_time')
        if photo_time_idx >= 0:
            self.photo_layer.changeAttributeValue(feat_id, photo_time_idx, photo_time)
        
        if self.photo_layer.isEditable():
            self.photo_layer.commitChanges()
        
        # Refresh the photo list to show updated label text
        if self.photo_list_manager:
            self.photo_list_manager.populate_list()
        
        self.iface.mapCanvas().refresh()

    def apply_settings(self):
        """Apply all current settings and update the layer renderer."""
        self.settings_manager.apply_settings(self.dlg, self.photo_layer)

    def select_output_shapefile(self):
        """Opens a file dialog to select an existing Shapefile for output."""
        self.file_selector.select_output_shapefile()
    
    def select_layer_save_location(self):
        """Opens a file dialog to select where to save the layer file."""
        file_filter = "GeoPackage (*.gpkg);;Shapefile (*.shp);;All Files (*.*)"
        filepath, selected_filter = QFileDialog.getSaveFileName(
            self.dlg,
            "Choose Layer Save Location",
            "",
            file_filter
        )
        
        if filepath:
            # Ensure proper extension
            if selected_filter.startswith("GeoPackage") and not filepath.lower().endswith('.gpkg'):
                filepath += '.gpkg'
            elif selected_filter.startswith("Shapefile") and not filepath.lower().endswith('.shp'):
                filepath += '.shp'
            
            self.layer_save_path = filepath
            if hasattr(self.dlg, 'lineEdit_save_location'):
                self.dlg.lineEdit_save_location.setText(filepath)
            if hasattr(self.dlg, 'set_import_status'):
                self.dlg.set_import_status(True)
            
            self.iface.messageBar().pushMessage(
                "Save Location Set",
                f"Layer will be saved to: {os.path.basename(filepath)}",
                level=Qgis.Success,
                duration=3
            )
    
    def check_layer_save_location(self):
        """Check if layer save location is set. Returns True if set, False otherwise."""
        if not self.layer_save_path:
            QMessageBox.warning(
                self.dlg,
                "Save Location Required",
                "Please choose where to save the layer first.\n\n"
                "Go to the 'Upload' tab and click 'Choose Save Location...' to select "
                "where to save your photo layer (e.g., in your project reference folder)."
            )
            return False
        return True

    def activate_open_photo_tool(self, checked):
        """Activates or deactivates the map tool for viewing photos."""
        # Detect existing photo layer if not already set
        if not self.photo_layer and checked:
            self._detect_existing_photo_layer()
        
        success = self.ui_manager.activate_open_photo_tool(checked, self.photo_layer, self.open_photo_tool)
        if not success and hasattr(self, 'action_photo'):
            self.action_photo.setChecked(False)
    
    def _auto_generate_save_path(self):
        """Auto-generates a save path for the photo layer."""
        import os
        from qgis.core import QgsProject
        
        # Try to use project directory first
        project = QgsProject.instance()
        if project.fileName():
            project_dir = os.path.dirname(project.fileName())
            save_path = os.path.join(project_dir, "photo_locations.gpkg")
        else:
            # No project saved - use user's Documents folder
            from qgis.PyQt.QtCore import QStandardPaths
            docs_dir = QStandardPaths.writableLocation(DocumentsLocation)
            save_path = os.path.join(docs_dir, "QGIS_Photos", "photo_locations.gpkg")
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        QgsMessageLog.logMessage(
            f"[AUTO SAVE] Generated save path: {save_path}",
            'Photo Plugin',
            Qgis.Info
        )
        
        self.iface.messageBar().pushMessage(
            "Layer Save Location",
            f"Photo layer will be saved to: {os.path.basename(save_path)}",
            level=Qgis.Info,
            duration=5
        )
        
        return save_path
    
    def _get_auto_save_path_preview(self):
        """Get a preview of where the layer will be auto-saved without creating it."""
        import os
        from qgis.core import QgsProject
        
        project = QgsProject.instance()
        if project.fileName():
            project_dir = os.path.dirname(project.fileName())
            return os.path.join(project_dir, "photo_locations.gpkg")
        else:
            from qgis.PyQt.QtCore import QStandardPaths
            docs_dir = QStandardPaths.writableLocation(DocumentsLocation)
            return os.path.join(docs_dir, "QGIS_Photos", "photo_locations.gpkg")

    def create_point_layer(self, output_uri=None):
        """Delegates to layer_manager to create or open a photo layer."""
        # Use the layer save path if provided
        if not output_uri:
            if self.layer_save_path:
                output_uri = self.layer_save_path
            else:
                # No save path set - this should not happen as we check before calling
                QgsMessageLog.logMessage("[CREATE LAYER] ERROR: No save path set!", 'Photo Plugin', Qgis.Critical)
                return None
        
        self.photo_layer = self.layer_manager.create_point_layer(
            self.iface,
            self.photo_layer,
            self.photo_list_manager,
            output_uri
        )
        
        # Connect styleChanged signal to sync label settings
        if self.photo_layer and self.photo_layer.isValid():
            try:
                # Disconnect first to avoid duplicate connections
                self.photo_layer.styleChanged.disconnect(self._sync_label_settings_from_layer)
            except (TypeError, RuntimeError, AttributeError):
                QgsMessageLog.logMessage(
                    "[CREATE LAYER] styleChanged disconnect skipped (not connected or layer invalid)",
                    'Photo Plugin',
                    Qgis.Info
                )
            self.photo_layer.styleChanged.connect(self._sync_label_settings_from_layer)
        
        return self.photo_layer

    def add_point_to_map(self, lat, lon, photo_path, direction_angle=None, is_visible=True):
        """Delegates to layer_manager to add a point feature."""
        return self.layer_manager.add_point_to_map(self.photo_layer, lat, lon, photo_path, direction_angle, is_visible)

    def process_photos_in_list(self, filepaths):
        """Processes a list of photo files."""
        self.photo_processor.process_photos_in_list(
            filepaths, self.dlg, self.photo_layer, self.photo_list_manager, self.create_point_layer
        )

    def select_photo(self):
        """Opens a file dialog to select a single photo file."""
        # Check if save location is set, if not prompt user
        if not self.layer_save_path:
            QMessageBox.information(
                self.dlg,
                "Save Location Required",
                "Please choose where to save the photo layer first.\n\n"
                "This ensures your photos are saved to disk and not lost when you close QGIS."
            )
            self.select_layer_save_location()
            # If user cancelled, return
            if not self.layer_save_path:
                return
        
        filepaths = self.file_selector.select_photo()
        if filepaths:
            self.process_photos_in_list(filepaths)
            # Apply labeling automatically after upload
            if hasattr(self.dlg, 'checkBox_show_label') and self.dlg.checkBox_show_label.isChecked():
                self.label_manager.apply_labeling(self.photo_layer, enable_labels=True)

    def select_folder(self):
        """Opens a folder dialog to select a directory containing photos."""
        # Check if save location is set, if not prompt user
        if not self.layer_save_path:
            QMessageBox.information(
                self.dlg,
                "Save Location Required",
                "Please choose where to save the photo layer first.\n\n"
                "This ensures your photos are saved to disk and not lost when you close QGIS."
            )
            self.select_layer_save_location()
            # If user cancelled, return
            if not self.layer_save_path:
                return
        
        filepaths = self.file_selector.select_folder()
        if filepaths:
            self.process_photos_in_list(filepaths)
            # Apply labeling automatically after upload
            if hasattr(self.dlg, 'checkBox_show_label') and self.dlg.checkBox_show_label.isChecked():
                self.label_manager.apply_labeling(self.photo_layer, enable_labels=True)

    def _on_update_metadata_requested(self, feat_id, new_lon, new_lat, new_direction):
        """Handles metadata update requests from the photo list manager."""
        self.feature_manager.handle_metadata_update_request(self.photo_layer, feat_id, new_lon, new_lat, new_direction)
    
    def open_advanced_label_settings(self):
        """Open the QGIS layer labeling properties dialog."""
        if not self.photo_layer or not self.photo_layer.isValid():
            self.iface.messageBar().pushMessage(
                "Warning",
                "No photo layer available. Please import photos first.",
                level=Qgis.Warning,
                duration=3
            )
            return
        
        # Open the layer styling panel to the Labels tab
        self.iface.showLayerProperties(self.photo_layer)
        
        # Message to user
        self.iface.messageBar().pushMessage(
            "Info",
            "Opening layer properties. Navigate to the 'Labels' tab for advanced settings.",
            level=Qgis.Info,
            duration=3
        )

    def export_plugin_state(self):
        """Export all photos from the imported photos tab to Excel with visibility status."""
        # Ensure dialog is initialized before exporting (needed to export label settings)
        if self.dlg is None:
            QgsMessageLog.logMessage("[EXPORT] Dialog not initialized - label settings won't be exported", 'Photo Plugin', Qgis.Warning)
        
        self.excel_manager.export_plugin_state(self.photo_layer, self.dlg)

    def import_plugin_state(self):
        """Import photos from an Excel file and create a new layer."""
        
        # Ask user to select save location for imported layer
        if not self.layer_save_path:
            # Prompt user to choose save location first
            QMessageBox.information(
                self.dlg if self.dlg else self.iface.mainWindow(),
                "Save Location Required",
                "Please choose where to save the photo layer first.\n\n"
                "This ensures your photos are saved to disk and not lost when you close QGIS."
            )
            
            file_filter = "GeoPackage (*.gpkg);;Shapefile (*.shp);;All Files (*.*)"
            filepath, selected_filter = QFileDialog.getSaveFileName(
                self.iface.mainWindow() if not self.dlg else self.dlg,
                "Choose Save Location for Imported Photos",
                "",
                file_filter
            )
            
            if not filepath:
                # User cancelled
                QgsMessageLog.logMessage("[IMPORT] User cancelled save location selection", 'Photo Plugin', Qgis.Info)
                return
            
            # Ensure proper extension
            if selected_filter.startswith("GeoPackage") and not filepath.lower().endswith('.gpkg'):
                filepath += '.gpkg'
            elif selected_filter.startswith("Shapefile") and not filepath.lower().endswith('.shp'):
                filepath += '.shp'
            
            self.layer_save_path = filepath
            if hasattr(self.dlg, 'lineEdit_save_location'):
                self.dlg.lineEdit_save_location.setText(self.layer_save_path)
        
        # CRITICAL: Disconnect styleChanged from old layer to prevent interference
        try:
            if self.photo_layer and self.photo_layer.isValid():
                self.photo_layer.styleChanged.disconnect(self._sync_label_settings_from_layer)
                QgsMessageLog.logMessage("[IMPORT] Disconnected styleChanged from old layer", 'Photo Plugin', Qgis.Info)
        except (RuntimeError, AttributeError, TypeError):
            # Layer has been deleted or never existed
            QgsMessageLog.logMessage("[IMPORT] Old layer already deleted or doesn't exist", 'Photo Plugin', Qgis.Info)
            pass
        
        # Ensure dialog is initialized before importing (needed for settings to be applied)
        if self.dlg is None:
            QgsMessageLog.logMessage("[IMPORT] Dialog not initialized yet, initializing now...", 'Photo Plugin', Qgis.Info)
            # Initialize dialog and all components
            self.dlg = AdvancedPhotoImporterDialog(plugin_dir=self.plugin_dir,
                                                 parent=self.iface.mainWindow(),
                                                 initial_tolerance=self.click_tolerance_m)

            # Initialize photo list manager
            self.photo_list_manager = PhotoListManager(self.iface, self.photo_layer, self.dlg, self.date_time_filter)
            
            def safe_update_renderer():
                try:
                    if self.photo_layer and self.photo_layer.isValid():
                        self.symbol_renderer.update_layer_symbol_manually(self.photo_layer, self.iface)
                except RuntimeError:
                    pass  # Layer has been deleted
            
            self.photo_list_manager.updateRendererRequested.connect(safe_update_renderer)
            self.photo_list_manager.updateMetadataRequested.connect(self._on_update_metadata_requested)
            self.photo_list_manager.visibilityChangedFromList.connect(self._on_visibility_changed_from_list)

            # Initialize modular managers
            self.file_selector = FileSelector(self.iface, self.dlg)
            self.photo_processor = PhotoProcessor(self.iface, self.layer_manager, self.exif_handler, self.symbol_renderer)
            self.settings_manager = SettingsManager(self.iface, self.symbol_renderer, self.photo_list_manager, self.label_manager)
            self.feature_manager = FeatureManager(self.iface, self.layer_manager, self.photo_list_manager, self.date_time_filter)
            self.ui_manager = UIManager(self.iface, self.dlg, self.photo_list_manager)
            
            # DEBUG: Verify date_time_filter connection
            QgsMessageLog.logMessage(
                f"[IMPORT INIT DEBUG] feature_manager.date_time_filter is {'CONNECTED' if self.feature_manager.date_time_filter else 'NULL'}",
                'Photo Plugin',
                Qgis.Critical if not self.feature_manager.date_time_filter else Qgis.Info
            )
            self.iface.messageBar().pushMessage(
                "Import Debug",
                f"date_time_filter: {'CONNECTED' if self.feature_manager.date_time_filter else 'NULL'}",
                level=Qgis.Critical if not self.feature_manager.date_time_filter else Qgis.Info,
                duration=5
            )

            # Insert the photo list manager into the dialog
            if hasattr(self.dlg, 'imported_photos_main_layout') and self.dlg.imported_photos_main_layout:
                item = self.dlg.imported_photos_main_layout.takeAt(0)
                if item and item.widget():
                    item.widget().deleteLater()
                self.dlg.imported_photos_main_layout.addWidget(self.photo_list_manager)

            # Connect signals
            self.dlg.pushButton_browse.clicked.connect(self.select_photo)
            if hasattr(self.dlg, 'pushButton_browseFolder'):
                self.dlg.pushButton_browseFolder.clicked.connect(self.select_folder)
            
            # Connect save location button (NEW)
            if hasattr(self.dlg, 'pushButton_browse_save_location'):
                self.dlg.pushButton_browse_save_location.clicked.connect(self.select_layer_save_location)
            
            if hasattr(self.dlg, 'pushButton_browse_output'):
                self.dlg.pushButton_browse_output.clicked.connect(self.select_output_shapefile)
            if hasattr(self.dlg, 'pushButton_apply_all_settings'):
                QgsMessageLog.logMessage("[IMPORT] Connecting pushButton_apply_all_settings", 'Photo Plugin', Qgis.Info)
                self.dlg.pushButton_apply_all_settings.clicked.connect(self.apply_all_settings)
                QgsMessageLog.logMessage("[IMPORT] Successfully connected pushButton_apply_all_settings", 'Photo Plugin', Qgis.Info)
            else:
                QgsMessageLog.logMessage("[IMPORT] ERROR: pushButton_apply_all_settings not found!", 'Photo Plugin', Qgis.Critical)
            if hasattr(self.dlg, 'export_plugin_state_clicked'):
                self.dlg.export_plugin_state_clicked.connect(self.export_plugin_state)
            if hasattr(self.dlg, 'import_plugin_state_clicked'):
                self.dlg.import_plugin_state_clicked.connect(self.import_plugin_state)
            if hasattr(self.dlg, 'pushButton_advanced_label'):
                self.dlg.pushButton_advanced_label.clicked.connect(self.open_advanced_label_settings)
            
            # Connect date/time filter buttons (NEW)
            if hasattr(self.dlg, 'pushButton_apply_filter'):
                self.dlg.pushButton_apply_filter.clicked.connect(self.apply_date_time_filter)
                QgsMessageLog.logMessage("[IMPORT] Connected pushButton_apply_filter", 'Photo Plugin', Qgis.Info)
            
            if hasattr(self.dlg, 'pushButton_remove_filter'):
                self.dlg.pushButton_remove_filter.clicked.connect(self.remove_date_time_filter)
                QgsMessageLog.logMessage("[IMPORT] Connected pushButton_remove_filter", 'Photo Plugin', Qgis.Info)
            
            self.first_start = False
            QgsMessageLog.logMessage("[IMPORT] Dialog initialized successfully", 'Photo Plugin', Qgis.Info)
        
        try:
            result = self.excel_manager.import_plugin_state(
                self.layer_manager, self.photo_layer, self.photo_list_manager, self.symbol_renderer, self.label_manager, self.dlg
            )
        except Exception as e:
            QgsMessageLog.logMessage(f"[IMPORT] ERROR during import: {str(e)}", 'Photo Plugin', Qgis.Critical)
            import traceback
            QgsMessageLog.logMessage(f"[IMPORT] Traceback: {traceback.format_exc()}", 'Photo Plugin', Qgis.Critical)
            QMessageBox.critical(
                self.iface.mainWindow(),
                "Import Error",
                f"Failed to import from Excel file: {str(e)}\n\nCheck the message log for details."
            )
            return
        
        # Update photo_layer and photo_list_manager if import was successful
        if result and result[0] is not None:
            imported_layer = result[0]
            self.photo_layer = imported_layer
            
            # Log layer information for debugging
            QgsMessageLog.logMessage(f"[IMPORT] Updated self.photo_layer to new imported layer: {self.photo_layer.name() if self.photo_layer else 'None'}", 'Photo Plugin', Qgis.Info)
            if self.photo_layer:
                QgsMessageLog.logMessage(f"[IMPORT] Layer source: {self.photo_layer.source()}", 'Photo Plugin', Qgis.Info)
                QgsMessageLog.logMessage(f"[IMPORT] Layer provider: {self.photo_layer.providerType()}", 'Photo Plugin', Qgis.Info)
                if self.photo_layer.providerType() == 'memory':
                    QgsMessageLog.logMessage("[IMPORT] WARNING: Layer is still a memory layer!", 'Photo Plugin', Qgis.Critical)
                    self.iface.messageBar().pushMessage(
                        "Warning",
                        "Imported layer is a temporary memory layer. This should not happen!",
                        level=Qgis.Warning,
                        duration=10
                    )
                else:
                    QgsMessageLog.logMessage("[IMPORT] SUCCESS: Layer is saved to disk", 'Photo Plugin', Qgis.Info)
                    self.iface.messageBar().pushMessage(
                        "Import Success",
                        f"Photos imported and saved to: {os.path.basename(self.photo_layer.source())}",
                        level=Qgis.Success,
                        duration=5
                    )
            
            if result[1] is not None:
                self.photo_list_manager = result[1]
                # If dialog exists, update the photo list in the imported photos tab
                if self.dlg and hasattr(self.dlg, 'imported_photos_main_layout'):
                    # Check if photo_list_manager is already in the layout
                    existing_widget = self.dlg.imported_photos_main_layout.itemAt(0)
                    if existing_widget and existing_widget.widget() != self.photo_list_manager:
                        # Remove old widget and add new one
                        old_widget = self.dlg.imported_photos_main_layout.takeAt(0).widget()
                        if old_widget:
                            old_widget.deleteLater()
                        self.dlg.imported_photos_main_layout.addWidget(self.photo_list_manager)
                    elif not existing_widget:
                        # No widget exists, add the photo list manager
                        self.dlg.imported_photos_main_layout.addWidget(self.photo_list_manager)
            
            # Apply click tolerance if it was imported
            if len(result) > 2 and result[2] is not None:
                click_tolerance = result[2]
                self.click_tolerance_m = click_tolerance
                if self.settings_manager:
                    self.settings_manager.update_click_tolerance(click_tolerance)
                QgsMessageLog.logMessage(f"[IMPORT] Applied click tolerance: {click_tolerance}", 'Photo Plugin', Qgis.Info)
            
            # Connect styleChanged signal to new layer
            try:
                if self.photo_layer and self.photo_layer.isValid():
                    try:
                        # Disconnect first to avoid duplicate connections
                        self.photo_layer.styleChanged.disconnect(self._sync_label_settings_from_layer)
                        QgsMessageLog.logMessage("[IMPORT] Disconnected existing styleChanged", 'Photo Plugin', Qgis.Info)
                    except TypeError:
                        # Not connected, which is expected for new layer
                        pass
                    
                    self.photo_layer.styleChanged.connect(self._sync_label_settings_from_layer)
                    QgsMessageLog.logMessage("[IMPORT] Connected styleChanged to new layer", 'Photo Plugin', Qgis.Info)
                else:
                    QgsMessageLog.logMessage("[IMPORT] Cannot connect styleChanged - layer is invalid", 'Photo Plugin', Qgis.Warning)
            except (RuntimeError, AttributeError) as e:
                QgsMessageLog.logMessage(f"[IMPORT] Could not connect styleChanged: {str(e)}", 'Photo Plugin', Qgis.Warning)
                
    def apply_label_styling(self):
        """Apply label styling to the photo layer based on settings."""
        QgsMessageLog.logMessage("[LABEL STYLE] ===== apply_label_styling called =====", 'Photo Plugin', Qgis.Info)
        
        try:
            if not self.photo_layer or not self.photo_layer.isValid():
                QgsMessageLog.logMessage("[LABEL STYLE] Photo layer is invalid or doesn't exist", 'Photo Plugin', Qgis.Warning)
                self.iface.messageBar().pushMessage(
                    "Warning",
                    "No photo layer available. Please import photos first.",
                    level=Qgis.Warning,
                    duration=3
                )
                return
        except RuntimeError:
            QgsMessageLog.logMessage("[LABEL STYLE] Photo layer has been deleted", 'Photo Plugin', Qgis.Critical)
            self.photo_layer = None
            return
        
        QgsMessageLog.logMessage(f"[LABEL STYLE] Photo layer is valid: {self.photo_layer.name()}", 'Photo Plugin', Qgis.Info)
        
        # Get label settings from the dialog - only update what's available
        if hasattr(self.dlg, 'spinBox_font_size'):
            from qgis.PyQt.QtGui import QColor
            
            QgsMessageLog.logMessage("\n" + "*"*80, 'Photo Plugin', Qgis.Info)
            QgsMessageLog.logMessage("[LABEL STYLE] Reading label settings from dialog BEFORE APPLY", 'Photo Plugin', Qgis.Info)
            QgsMessageLog.logMessage("*"*80, 'Photo Plugin', Qgis.Info)
            
            # Collect only the settings that are available in the dialog
            font_size = self.dlg.spinBox_font_size.value()
            QgsMessageLog.logMessage(f"[LABEL STYLE] >>> Font size FROM DIALOG: {font_size}", 'Photo Plugin', Qgis.Info)
            
            font_bold = self.dlg.checkBox_font_bold.isChecked() if hasattr(self.dlg, 'checkBox_font_bold') else None
            QgsMessageLog.logMessage(f"[LABEL STYLE] >>> Font bold FROM DIALOG: {font_bold}", 'Photo Plugin', Qgis.Info)
            
            # Get font color with opacity
            font_color = None
            if hasattr(self.dlg, 'font_color'):
                font_color = QColor(self.dlg.font_color)
                QgsMessageLog.logMessage(f"[LABEL STYLE] >>> Font color object FROM DIALOG: {self.dlg.font_color}", 'Photo Plugin', Qgis.Info)
                if hasattr(self.dlg, 'slider_font_opacity'):
                    font_opacity = self.dlg.slider_font_opacity.value() / 100.0
                    font_color.setAlphaF(font_opacity)
                    QgsMessageLog.logMessage(f"[LABEL STYLE] >>> Font color FROM DIALOG: {font_color.name()}, opacity: {font_opacity}", 'Photo Plugin', Qgis.Info)
            
            # Get buffer settings
            buffer_size = self.dlg.spinBox_buffer_size.value() if hasattr(self.dlg, 'spinBox_buffer_size') else None
            QgsMessageLog.logMessage(f"[LABEL STYLE] >>> Buffer size FROM DIALOG: {buffer_size}", 'Photo Plugin', Qgis.Info)
            
            buffer_color = None
            if hasattr(self.dlg, 'buffer_color'):
                buffer_color = QColor(self.dlg.buffer_color)
                QgsMessageLog.logMessage(f"[LABEL STYLE] >>> Buffer color object FROM DIALOG: {self.dlg.buffer_color}", 'Photo Plugin', Qgis.Info)
                if hasattr(self.dlg, 'slider_buffer_opacity'):
                    buffer_opacity = self.dlg.slider_buffer_opacity.value() / 100.0
                    buffer_color.setAlphaF(buffer_opacity)
                    QgsMessageLog.logMessage(f"[LABEL STYLE] >>> Buffer color FROM DIALOG: {buffer_color.name()}, opacity: {buffer_opacity}", 'Photo Plugin', Qgis.Info)
            
            # Get label distance (padding)
            label_distance = self.dlg.spinBox_label_padding.value() if hasattr(self.dlg, 'spinBox_label_padding') else None
            QgsMessageLog.logMessage(f"[LABEL STYLE] >>> Label distance FROM DIALOG: {label_distance}", 'Photo Plugin', Qgis.Info)
            
            QgsMessageLog.logMessage("*"*80 + "\n", 'Photo Plugin', Qgis.Info)
            
            # Update label manager settings - only pass non-None values
            QgsMessageLog.logMessage("[LABEL STYLE] Calling label_manager.update_label_style with values:", 'Photo Plugin', Qgis.Info)
            QgsMessageLog.logMessage(f"  - font_size: {font_size}", 'Photo Plugin', Qgis.Info)
            QgsMessageLog.logMessage(f"  - font_bold: {font_bold}", 'Photo Plugin', Qgis.Info)
            QgsMessageLog.logMessage(f"  - font_color: {font_color}", 'Photo Plugin', Qgis.Info)
            QgsMessageLog.logMessage(f"  - buffer_size: {buffer_size}", 'Photo Plugin', Qgis.Info)
            QgsMessageLog.logMessage(f"  - buffer_color: {buffer_color}", 'Photo Plugin', Qgis.Info)
            QgsMessageLog.logMessage(f"  - label_distance: {label_distance}", 'Photo Plugin', Qgis.Info)
            
            self.label_manager.update_label_style(
                font_size=font_size,
                font_bold=font_bold,
                font_color=font_color,
                buffer_size=buffer_size,
                buffer_color=buffer_color,
                label_distance=label_distance
            )
            
            QgsMessageLog.logMessage("[LABEL STYLE] After update_label_style, label_manager values:", 'Photo Plugin', Qgis.Info)
            QgsMessageLog.logMessage(f"  - label_manager.font_size: {self.label_manager.font_size}", 'Photo Plugin', Qgis.Info)
            QgsMessageLog.logMessage(f"  - label_manager.font_bold: {self.label_manager.font_bold}", 'Photo Plugin', Qgis.Info)
            QgsMessageLog.logMessage(f"  - label_manager.font_color: {self.label_manager.font_color}", 'Photo Plugin', Qgis.Info)
            QgsMessageLog.logMessage(f"  - label_manager.buffer_size: {self.label_manager.buffer_size}", 'Photo Plugin', Qgis.Info)
            QgsMessageLog.logMessage(f"  - label_manager.buffer_color: {self.label_manager.buffer_color}", 'Photo Plugin', Qgis.Info)
            QgsMessageLog.logMessage(f"  - label_manager.label_distance: {self.label_manager.label_distance}", 'Photo Plugin', Qgis.Info)
        else:
            QgsMessageLog.logMessage("[LABEL STYLE] spinBox_font_size not found in dialog", 'Photo Plugin', Qgis.Warning)
        
        # Check if labeling should be enabled
        enable_labels = True
        if hasattr(self.dlg, 'checkBox_show_label'):
            enable_labels = self.dlg.checkBox_show_label.isChecked()
            QgsMessageLog.logMessage(f"[LABEL STYLE] Enable labels: {enable_labels}", 'Photo Plugin', Qgis.Info)
        
        # Block all signals from the layer during apply to prevent sync-back
        self.photo_layer.blockSignals(True)
        QgsMessageLog.logMessage("[LABEL STYLE] Blocked layer signals", 'Photo Plugin', Qgis.Info)
        
        # Apply labeling to layer
        QgsMessageLog.logMessage("[LABEL STYLE] Calling label_manager.apply_labeling with enable_labels={}".format(enable_labels), 'Photo Plugin', Qgis.Info)
        success = self.label_manager.apply_labeling(self.photo_layer, enable_labels)
        QgsMessageLog.logMessage(f"[LABEL STYLE] apply_labeling returned: {success}", 'Photo Plugin', Qgis.Info)
        
        # Check dialog values BEFORE unblocking signals
        QgsMessageLog.logMessage("[LABEL STYLE] Dialog values BEFORE unblocking signals:", 'Photo Plugin', Qgis.Info)
        QgsMessageLog.logMessage(f"  - spinBox_font_size: {self.dlg.spinBox_font_size.value()}", 'Photo Plugin', Qgis.Info)
        if hasattr(self.dlg, 'checkBox_font_bold'):
            QgsMessageLog.logMessage(f"  - checkBox_font_bold: {self.dlg.checkBox_font_bold.isChecked()}", 'Photo Plugin', Qgis.Info)
        
        # Unblock signals after apply is complete
        self.photo_layer.blockSignals(False)
        QgsMessageLog.logMessage("[LABEL STYLE] Unblocked layer signals", 'Photo Plugin', Qgis.Info)
        
        # Check dialog values AFTER unblocking signals
        QgsMessageLog.logMessage("[LABEL STYLE] Dialog values AFTER unblocking signals:", 'Photo Plugin', Qgis.Info)
        QgsMessageLog.logMessage(f"  - spinBox_font_size: {self.dlg.spinBox_font_size.value()}", 'Photo Plugin', Qgis.Info)
        if hasattr(self.dlg, 'checkBox_font_bold'):
            QgsMessageLog.logMessage(f"  - checkBox_font_bold: {self.dlg.checkBox_font_bold.isChecked()}", 'Photo Plugin', Qgis.Info)
        
        # Reconnect styleChanged signal after apply is complete
        try:
            self.photo_layer.styleChanged.connect(self._sync_label_settings_from_layer)
            QgsMessageLog.logMessage("[LABEL STYLE] Reconnected styleChanged signal", 'Photo Plugin', Qgis.Info)
        except (TypeError, RuntimeError, AttributeError) as e:
            QgsMessageLog.logMessage(
                f"[LABEL STYLE] Could not reconnect styleChanged: {e}",
                'Photo Plugin',
                Qgis.Warning
            )
        
        # Check dialog values AFTER reconnecting signal
        QgsMessageLog.logMessage("[LABEL STYLE] Dialog values AFTER reconnecting signal:", 'Photo Plugin', Qgis.Info)
        QgsMessageLog.logMessage(f"  - spinBox_font_size: {self.dlg.spinBox_font_size.value()}", 'Photo Plugin', Qgis.Info)
        if hasattr(self.dlg, 'checkBox_font_bold'):
            QgsMessageLog.logMessage(f"  - checkBox_font_bold: {self.dlg.checkBox_font_bold.isChecked()}", 'Photo Plugin', Qgis.Info)
        
        # Manually trigger a repaint since signals were blocked
        QgsMessageLog.logMessage("[LABEL STYLE] Triggering repaint and canvas refresh", 'Photo Plugin', Qgis.Info)
        self.photo_layer.triggerRepaint()
        self.iface.mapCanvas().refresh()
        
        # Check dialog values AFTER repaint
        QgsMessageLog.logMessage("[LABEL STYLE] Dialog values AFTER repaint:", 'Photo Plugin', Qgis.Info)
        QgsMessageLog.logMessage(f"  - spinBox_font_size: {self.dlg.spinBox_font_size.value()}", 'Photo Plugin', Qgis.Info)
        if hasattr(self.dlg, 'checkBox_font_bold'):
            QgsMessageLog.logMessage(f"  - checkBox_font_bold: {self.dlg.checkBox_font_bold.isChecked()}", 'Photo Plugin', Qgis.Info)
        
        if success:
            QgsMessageLog.logMessage("[LABEL STYLE] Label styling applied successfully", 'Photo Plugin', Qgis.Info)
            self.iface.messageBar().pushMessage(
                "Success",
                "Label styling applied successfully!" if enable_labels else "Labeling disabled.",
                level=Qgis.Success,
                duration=3
            )
        else:
            self.iface.messageBar().pushMessage(
                "Error",
                "Failed to apply label styling.",
                level=Qgis.Critical,
                duration=3
            )
    
    def apply_date_time_filter(self):
        """Apply date & time filter to photos based on dialog settings."""
        if not self.photo_layer or not self.photo_layer.isValid():
            self.iface.messageBar().pushMessage(
                "Warning",
                "No photo layer available. Please import photos first.",
                level=Qgis.Warning,
                duration=3
            )
            return
        
        # Get date/time values from dialog
        start_qdatetime = self.dlg.dateTimeEdit_start.dateTime()
        end_qdatetime = self.dlg.dateTimeEdit_end.dateTime()
        
        # Convert QDateTime to Python datetime
        start_datetime = datetime(
            start_qdatetime.date().year(),
            start_qdatetime.date().month(),
            start_qdatetime.date().day(),
            start_qdatetime.time().hour(),
            start_qdatetime.time().minute(),
            start_qdatetime.time().second()
        )
        
        end_datetime = datetime(
            end_qdatetime.date().year(),
            end_qdatetime.date().month(),
            end_qdatetime.date().day(),
            end_qdatetime.time().hour(),
            end_qdatetime.time().minute(),
            end_qdatetime.time().second()
        )
        
        QgsMessageLog.logMessage(
            f"[FILTER] Applying date/time filter: {start_datetime} to {end_datetime}",
            'Photo Plugin',
            Qgis.Info
        )
        
        # Apply filter using the date_time_filter module
        success = self.date_time_filter.apply_filter(
            self.photo_layer,
            start_datetime,
            end_datetime
        )
        
        if success:
            # Rebuild renderer so hidden photos disappear immediately
            self.symbol_renderer.update_layer_symbol_manually(self.photo_layer, self.iface)
            
            # Update status label
            if hasattr(self.dlg, 'label_filter_status'):
                self.dlg.label_filter_status.setText(
                    f"Status: Filter active ({start_datetime.strftime('%Y-%m-%d %H:%M')} to {end_datetime.strftime('%Y-%m-%d %H:%M')})"
                )
                self.dlg.label_filter_status.setStyleSheet("font-weight: bold; color: #00aa00;")
    
    def remove_date_time_filter(self):
        """Remove the date & time filter, restoring all photos (respecting manual visibility)."""
        if not self.photo_layer or not self.photo_layer.isValid():
            self.iface.messageBar().pushMessage(
                "Warning",
                "No photo layer available.",
                level=Qgis.Warning,
                duration=3
            )
            return
        
        QgsMessageLog.logMessage(
            "[FILTER] Removing date/time filter",
            'Photo Plugin',
            Qgis.Info
        )
        
        # Remove filter using the date_time_filter module
        success = self.date_time_filter.remove_filter(self.photo_layer)
        
        if success:
            # Rebuild and re-apply the rule-based renderer so the canvas reflects
            # the restored svg_icon values immediately (same operation that the
            # "Imported Photos" tab triggers via updateRendererRequested).
            self.symbol_renderer.update_layer_symbol_manually(self.photo_layer, self.iface)
            
            # Update status label
            if hasattr(self.dlg, 'label_filter_status'):
                self.dlg.label_filter_status.setText("Status: No filter applied")
                self.dlg.label_filter_status.setStyleSheet("font-weight: bold; color: #0066cc;")
