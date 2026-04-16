# -*- coding: utf-8 -*-
# Copyright (C) 2026 Majid Jazebi
# Web: Geotechzone.com
# All rights reserved.
# This plugin is licensed under GNU GPL v3.

import os
from functools import partial
from qgis.PyQt.QtCore import Qt, QSize, pyqtSignal, QCoreApplication, QDateTime
from qgis.PyQt.QtGui import QFont, QIcon, QColor, QPixmap, QTransform
from qgis.PyQt.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QGroupBox,
    QGridLayout,
    QWidget,
    QToolButton,
    QScrollArea,
    QCheckBox,
    QTabWidget,
    QSpinBox,
    QDoubleSpinBox,
    QSlider,
    QColorDialog,
    QDateTimeEdit,
    QComboBox,
    QFrame,
)

from .dependency_manager import DependencyManager


class AdvancedPhotoImporterDialog(QDialog):
    """
    Dialog for the Advanced Photo Importer plugin, organized into Import, Settings, and Imported Photos tabs.
    """
    
    # Define custom signals
    apply_tolerance_clicked = pyqtSignal(float)
    export_plugin_state_clicked = pyqtSignal()
    import_plugin_state_clicked = pyqtSignal()

    IN_MEMORY_LAYER_NAME = "Photo Locations (In-Memory)"

    def __init__(self, plugin_dir, parent=None, initial_tolerance=5.0):
        """Constructor."""
        super().__init__(parent)
        self.setWindowTitle(self.tr("Advanced Photo Importer"))
        self.setMinimumWidth(750) # Increased width to accommodate the photo list/preview
        self.setMinimumHeight(450)
        
        self.plugin_dir = plugin_dir
        self.mandatory_icons_dir = os.path.join(self.plugin_dir, 'icons', '1-Mandatory')
        
        self.initial_tolerance = initial_tolerance
        
        # Reference to the main content area of the 'Imported Photos' tab 
        # The main plugin class will insert the PhotoListManager here.
        self.imported_photos_main_layout = None 

        self.initUi()
        
        # --- Post-UI Setup and Connections ---
        
        # Connect widgets inside the Settings tab
        self.spinBox_tolerance.setValue(int(initial_tolerance))
        
        # Connect export/import buttons
        self.pushButton_export.clicked.connect(self.export_plugin_state_clicked.emit)
        self.pushButton_import.clicked.connect(self.import_plugin_state_clicked.emit)
        
        # Connect close button in Settings tab
        self.pushButton_cancel.clicked.connect(self.reject)


    def tr(self, message):
        """Helper for QCoreApplication translation."""
        return QCoreApplication.translate('AdvancedPhotoImporterDialog', message)

    def set_import_status(self, save_location_set, message=None):
        """Update the status banner and enable/disable Step 2 based on whether Step 1 is complete."""
        if not hasattr(self, 'label_coordinate'):
            return

        if save_location_set:
            text = message or self.tr(
                "\u2714\u2002\u2193\u2002 Save location set \u2014 now select photos or use import / export below."
            )
            self.label_coordinate.setStyleSheet(
                "color: #1a6e2e;"
                "background-color: #eaf6ed;"
                "border: 1px solid #7acf8f;"
                "border-radius: 5px;"
                "padding: 6px 12px;"
                "margin: 3px 0px;"
            )
            # Unlock Step 2
            if hasattr(self, 'step2_group'):
                self.step2_group.setEnabled(True)
                self.step2_group.setStyleSheet(self._STEP2_STYLE_ENABLED)
        else:
            text = message or self.tr(
                "\u26a0\u2002\u2191\u2002 Step 1 required \u2014 choose a save location before selecting photos."
            )
            self.label_coordinate.setStyleSheet(
                "color: #c0392b;"
                "background-color: #fdf0ef;"
                "border: 1px solid #e8b4af;"
                "border-radius: 5px;"
                "padding: 6px 12px;"
                "margin: 3px 0px;"
            )
            # Lock Step 2
            if hasattr(self, 'step2_group'):
                self.step2_group.setEnabled(False)
                self.step2_group.setStyleSheet(self._STEP2_STYLE_DISABLED)

        self.label_coordinate.setText(text)


    def initUi(self):
        """Sets up the main layout and QTabWidget."""
        main_layout = QVBoxLayout(self)
        
        # --- 1. Main Tab Widget ---
        self.tab_widget = QTabWidget()
        
        self.import_tab = self._create_import_tab()
        self.settings_tab = self._create_settings_tab()
        self.filter_tab = self._create_filter_tab()  # NEW: Date & Time Filter tab
        self.imported_photos_tab = self._create_imported_photos_tab()
        self.about_tab = self._create_about_tab()  # NEW: About tab

        # Add tabs with icons
        upload_icon_path = os.path.join(self.mandatory_icons_dir, 'upload_photos.svg')
        settings_icon_path = os.path.join(self.mandatory_icons_dir, 'Settings Icon.svg')
        filter_icon_path = os.path.join(self.mandatory_icons_dir, 'Filter Icon.svg')
        photos_icon_path = os.path.join(self.mandatory_icons_dir, 'see_photo.svg')
        about_icon_path = os.path.join(self.mandatory_icons_dir, 'About.svg')
        
        self.tab_widget.addTab(self.import_tab, QIcon(upload_icon_path), self.tr("Upload"))
        self.tab_widget.addTab(self.imported_photos_tab, QIcon(photos_icon_path), self.tr("Imported Photos"))
        self.tab_widget.addTab(self.filter_tab, QIcon(filter_icon_path), self.tr("Filter"))  # NEW TAB
        self.tab_widget.addTab(self.settings_tab, QIcon(settings_icon_path), self.tr("Settings"))
        self.tab_widget.addTab(self.about_tab, QIcon(about_icon_path), self.tr("About"))  # About tab at the end

        main_layout.addWidget(self.tab_widget)
        
        self.setLayout(main_layout)

    # --- TAB CREATION METHODS ---

    # ─── Step-2 group stylesheet helpers ────────────────────────────────────
    _STEP2_STYLE_ENABLED = """
        QGroupBox {
            border: 1px solid #b0c4b8;
            border-radius: 6px;
            margin-top: 8px;
            background-color: #ffffff;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
            color: #1a6e2e;
            font-weight: bold;
        }
    """
    _STEP2_STYLE_DISABLED = """
        QGroupBox {
            border: 1px solid #d8d8d8;
            border-radius: 6px;
            margin-top: 8px;
            background-color: #f4f4f4;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
            color: #aaaaaa;
            font-weight: bold;
        }
        QGroupBox QLineEdit, QGroupBox QCheckBox, QGroupBox QLabel {
            color: #bbbbbb;
        }
        QGroupBox QPushButton {
            color: #bbbbbb;
            background-color: #e8e8e8;
            border: 1px solid #d0d0d0;
        }
    """

    def _create_import_tab(self):
        """Creates the 'Import' tab content."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(4)
        layout.setContentsMargins(8, 8, 8, 8)

        # ── Step 1: Layer Save Location ──────────────────────────────────────
        save_location_group = QGroupBox(self.tr("Step 1 — Layer Save Location"))
        save_location_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #b0b0c8;
                border-radius: 6px;
                margin-top: 8px;
                background-color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #2a4a8a;
                font-weight: bold;
            }
        """)
        save_location_layout = QGridLayout(save_location_group)
        save_location_layout.setContentsMargins(10, 14, 10, 10)

        save_info_label = QLabel(self.tr(
            "Choose where to save the photo layer. This is required before importing photos.\n"
            "Recommended: Save in your project\u2019s reference folder."
        ))
        save_info_label.setWordWrap(True)
        save_info_label.setStyleSheet("color: #666; font-style: italic; margin-bottom: 4px;")
        save_location_layout.addWidget(save_info_label, 0, 0, 1, 3)

        self.lineEdit_save_location = QLineEdit()
        self.lineEdit_save_location.setPlaceholderText(self.tr("No save location chosen yet..."))
        self.lineEdit_save_location.setReadOnly(True)
        self.pushButton_browse_save_location = QPushButton(self.tr("Choose Save Location..."))
        self.pushButton_browse_save_location.setToolTip(
            self.tr("Select where to save the photo layer file (.gpkg)")
        )

        save_location_layout.addWidget(QLabel(self.tr("Save Location:")), 1, 0)
        save_location_layout.addWidget(self.lineEdit_save_location, 1, 1)
        save_location_layout.addWidget(self.pushButton_browse_save_location, 1, 2)

        layout.addWidget(save_location_group)

        # ── Status / Arrow Banner (between Step 1 and Step 2) ────────────────
        self.label_coordinate = QLabel(
            self.tr("\u26a0\u2002\u2191\u2002 Step 1 required \u2014 choose a save location before selecting photos.")
        )
        self.label_coordinate.setFont(QFont("Sans Serif", 9, QFont.Bold))
        self.label_coordinate.setWordWrap(True)
        self.label_coordinate.setAlignment(Qt.AlignCenter)
        self.label_coordinate.setStyleSheet(
            "color: #c0392b;"
            "background-color: #fdf0ef;"
            "border: 1px solid #e8b4af;"
            "border-radius: 5px;"
            "padding: 6px 12px;"
            "margin: 3px 0px;"
        )
        layout.addWidget(self.label_coordinate)

        # ── Step 2: Source Photos + Import/Export Alternative (combined) ──────
        self.step2_group = QGroupBox(
            self.tr("Step 2 \u2014 Select Photos or Import / Export from File")
        )
        self.step2_group.setEnabled(False)
        self.step2_group.setStyleSheet(self._STEP2_STYLE_DISABLED)
        step2_layout = QVBoxLayout(self.step2_group)
        step2_layout.setContentsMargins(10, 14, 10, 10)
        step2_layout.setSpacing(6)

        # ---- A: Photo file / folder selection --------------------------------
        photo_grid = QGridLayout()
        photo_grid.setSpacing(6)

        self.checkBox_include_subfolders = QCheckBox(self.tr("Include subfolders"))
        self.checkBox_include_subfolders.setToolTip(
            self.tr("When checked, photos in all subfolders will also be imported")
        )
        self.checkBox_include_subfolders.setChecked(False)
        photo_grid.addWidget(self.checkBox_include_subfolders, 0, 0, 1, 3)

        self.lineEdit_path = QLineEdit()
        photo_grid.addWidget(QLabel(self.tr("File / Folder Path:")), 1, 0)
        photo_grid.addWidget(self.lineEdit_path, 1, 1, 1, 2)

        self.pushButton_browse = QPushButton(self.tr("\U0001f5bc\ufe0f  Browse Photo File..."))
        self.pushButton_browseFolder = QPushButton(self.tr("\U0001f4c2  Browse Photo Folder..."))
        browse_h = QHBoxLayout()
        browse_h.setSpacing(8)
        browse_h.addWidget(self.pushButton_browse)
        browse_h.addWidget(self.pushButton_browseFolder)
        photo_grid.addLayout(browse_h, 2, 1, 1, 2)

        step2_layout.addLayout(photo_grid)

        # ---- B: "Or alternatively" container (visually separated) ------------
        step2_layout.addSpacing(8)

        alt_container = QWidget()
        alt_container.setObjectName("altContainer")
        alt_container.setStyleSheet(
            "QWidget#altContainer {"
            "  background-color: #f0f4f8;"
            "  border: 1px solid #c8d8e8;"
            "  border-radius: 5px;"
            "}"
        )
        alt_inner = QVBoxLayout(alt_container)
        alt_inner.setContentsMargins(12, 8, 12, 10)
        alt_inner.setSpacing(6)

        # divider line + label
        alt_header_layout = QHBoxLayout()
        alt_header_layout.setSpacing(8)
        line_l = QFrame(); line_l.setFrameShape(QFrame.HLine); line_l.setFrameShadow(QFrame.Sunken)
        line_l.setStyleSheet("background-color: #a0b8cc; max-height: 1px;")
        alt_title = QLabel(self.tr("\u2014\u2002Or alternatively: Import / Export to Excel or CSV files\u2002\u2014"))
        alt_title.setAlignment(Qt.AlignCenter)
        alt_title.setStyleSheet(
            "color: #3a6080;"
            "font-style: italic;"
            "font-size: 8pt;"
            "font-weight: bold;"
            "background: transparent;"
            "border: none;"
        )
        line_r = QFrame(); line_r.setFrameShape(QFrame.HLine); line_r.setFrameShadow(QFrame.Sunken)
        line_r.setStyleSheet("background-color: #a0b8cc; max-height: 1px;")
        alt_header_layout.addWidget(line_l, 1)
        alt_header_layout.addWidget(alt_title, 0)
        alt_header_layout.addWidget(line_r, 1)
        alt_inner.addLayout(alt_header_layout)

        # Import / Export buttons inside the alternative container
        pkg_layout = QHBoxLayout()
        pkg_layout.setSpacing(8)
        self.pushButton_import = QPushButton(self.tr("⬇  Import Package"))
        self.pushButton_import.setToolTip(self.tr("Import photos and settings from Excel file"))
        self.pushButton_import.setMinimumHeight(35)
        self.pushButton_export = QPushButton(self.tr("⬆  Export Package"))
        self.pushButton_export.setToolTip(self.tr("Export all photos and settings to Excel file"))
        self.pushButton_export.setMinimumHeight(35)
        pkg_layout.addWidget(self.pushButton_import)
        pkg_layout.addWidget(self.pushButton_export)
        alt_inner.addLayout(pkg_layout)

        step2_layout.addWidget(alt_container)

        layout.addWidget(self.step2_group)
        layout.addStretch(1)

        return tab

    def _refresh_dependency_panel(self):
        """Update the dependency status panel based on current install state."""
        statuses = DependencyManager.check_all()
        all_ok = all(s["installed"] for s in statuses)

        lines = []
        for s in statuses:
            icon = "\u2705" if s["installed"] else "\u274C"
            tag = "Required" if s["required"] else "Optional"
            if s["installed"]:
                src = "(system)" if s.get("source") == "system" else "(bundled)"
                status_text = f"Installed {src}"
            else:
                status_text = "Not available"
            lines.append(f"{icon}  <b>{s['pip']}</b> ({tag}) — {s['description']} — <i>{status_text}</i>")

        if all_ok:
            self.dep_frame.setStyleSheet(
                "QFrame { background-color: #d4edda; border: 1px solid #28a745;"
                " border-radius: 6px; }"
            )
            header = "<b>All dependencies are installed.</b>"
        else:
            self.dep_frame.setStyleSheet(
                "QFrame { background-color: #f8d7da; border: 1px solid #dc3545;"
                " border-radius: 6px; }"
            )
            missing = [s["pip"] for s in statuses if not s["installed"]]
            header = f"<b>Missing libraries: {', '.join(missing)}</b><br>Please install manually. See Help or README for instructions."

        self.dep_label.setText(header + "<br>" + "<br>".join(lines))

    def _create_settings_tab(self):
        """Creates the 'Settings' tab content."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # --- Direction Line and Tolerance Group ---
        tolerance_group = QGroupBox(self.tr("Map Tool & Symbol Options"))
        tolerance_layout = QGridLayout(tolerance_group)
        
        # Click Tolerance Setting (QSpinBox)
        self.spinBox_tolerance = QSpinBox()
        self.spinBox_tolerance.setRange(1, 100)
        self.spinBox_tolerance.setSuffix(self.tr(" map units"))
        self.spinBox_tolerance.setToolTip(self.tr("Search radius for finding a photo feature when using the 'See Photo' tool."))
        
        tolerance_layout.addWidget(QLabel(self.tr("Click Tolerance:")), 0, 0)
        tolerance_layout.addWidget(self.spinBox_tolerance, 0, 1)
        
        # Icon Size Setting (QSpinBox)
        self.spinBox_icon_size = QSpinBox()
        self.spinBox_icon_size.setRange(10, 500)
        self.spinBox_icon_size.setSuffix(self.tr("%"))
        self.spinBox_icon_size.setValue(100)  # Default: 100%
        self.spinBox_icon_size.setToolTip(self.tr("Icon size as percentage of default size (100% = default)"))
        
        tolerance_layout.addWidget(QLabel(self.tr("Icon Size:")), 1, 0)
        tolerance_layout.addWidget(self.spinBox_icon_size, 1, 1)
        
        # Icon Appearance Setting (QComboBox)
        self.comboBox_icon_appearance = QComboBox()
        self.comboBox_icon_appearance.setToolTip(self.tr("Select the icon appearance style"))
        self.comboBox_icon_appearance.setIconSize(QSize(48, 48))  # Set larger icon size for better visibility
        # Populate with camera icons from icons/2-Cameras folder
        camera_icons_path = os.path.join(self.plugin_dir, 'icons', '2-Cameras')
        if os.path.exists(camera_icons_path):
            camera_files = [f for f in os.listdir(camera_icons_path) if f.endswith('.svg')]
            # Sort naturally (Cam1, Cam2, ..., Cam10, Cam11, ...)
            camera_files.sort(key=lambda x: int(''.join(filter(str.isdigit, x))) if any(c.isdigit() for c in x) else 0)
            for camera_file in camera_files:
                display_name = os.path.splitext(camera_file)[0]  # Remove .svg extension
                # Load the SVG icon, rotate 180° for display in the combobox only
                icon_path = os.path.join(camera_icons_path, camera_file)
                raw_pixmap = QIcon(icon_path).pixmap(QSize(48, 48))
                rotated_pixmap = raw_pixmap.transformed(QTransform().rotate(180))
                icon = QIcon(rotated_pixmap)
                # Add item with both icon and text
                self.comboBox_icon_appearance.addItem(icon, display_name, camera_file)
        # Set default to Cam1.svg
        default_index = self.comboBox_icon_appearance.findData('Cam1.svg')
        if default_index >= 0:
            self.comboBox_icon_appearance.setCurrentIndex(default_index)
        
        tolerance_layout.addWidget(QLabel(self.tr("Icon Appearance:")), 2, 0)
        tolerance_layout.addWidget(self.comboBox_icon_appearance, 2, 1)

        # Show Direction Checkbox (default: checked)
        self.checkBox_show_direction = QCheckBox(self.tr("Show Direction"))
        self.checkBox_show_direction.setChecked(True)
        self.checkBox_show_direction.setToolTip(self.tr("When checked, icons are rotated according to the photo 'direction' field"))
        tolerance_layout.addWidget(self.checkBox_show_direction, 3, 1)

        layout.addWidget(tolerance_group)
        
        # --- Label Styling Group ---
        label_styling_group = QGroupBox(self.tr("Label Styling"))
        label_styling_layout = QGridLayout(label_styling_group)
        
        # Font Size
        label_styling_layout.addWidget(QLabel(self.tr("Font Size:")), 0, 0)
        self.spinBox_font_size = QDoubleSpinBox()
        self.spinBox_font_size.setRange(1.0, 100.0)
        self.spinBox_font_size.setSingleStep(0.5)
        self.spinBox_font_size.setValue(7.0)  # Default: 7
        self.spinBox_font_size.setToolTip(self.tr("Label font size"))
        label_styling_layout.addWidget(self.spinBox_font_size, 0, 1)
        
        # Font Bold
        self.checkBox_font_bold = QCheckBox(self.tr("Bold"))
        self.checkBox_font_bold.setChecked(True)  # Default: Bold enabled
        self.checkBox_font_bold.setToolTip(self.tr("Make label text bold"))
        label_styling_layout.addWidget(self.checkBox_font_bold, 0, 2)
        
        # Font Color
        label_styling_layout.addWidget(QLabel(self.tr("Font Color:")), 1, 0)
        self.font_color = QColor("#000000")  # Default black
        self.pushButton_font_color = QPushButton()
        self.pushButton_font_color.setFixedSize(50, 25)
        self.pushButton_font_color.setStyleSheet(f"background-color: {self.font_color.name()};")
        self.pushButton_font_color.clicked.connect(self._select_font_color)
        self.pushButton_font_color.setToolTip(self.tr("Click to select font color"))
        label_styling_layout.addWidget(self.pushButton_font_color, 1, 1)
        
        # Font Opacity
        label_styling_layout.addWidget(QLabel(self.tr("Font Opacity:")), 2, 0)
        self.slider_font_opacity = QSlider(Qt.Horizontal)
        self.slider_font_opacity.setRange(0, 100)
        self.slider_font_opacity.setValue(100)  # Default: fully opaque
        self.slider_font_opacity.setToolTip(self.tr("Font opacity (0-100%)"))
        label_styling_layout.addWidget(self.slider_font_opacity, 2, 1, 1, 2)
        
        # Buffer Size
        label_styling_layout.addWidget(QLabel(self.tr("Buffer Size:")), 3, 0)
        self.spinBox_buffer_size = QDoubleSpinBox()
        self.spinBox_buffer_size.setRange(0.0, 10.0)
        self.spinBox_buffer_size.setSingleStep(0.1)
        self.spinBox_buffer_size.setValue(1.0)  # Default: 1.0
        self.spinBox_buffer_size.setToolTip(self.tr("Label buffer (outline) size"))
        label_styling_layout.addWidget(self.spinBox_buffer_size, 3, 1)
        
        # Buffer Color
        label_styling_layout.addWidget(QLabel(self.tr("Buffer Color:")), 4, 0)
        self.buffer_color = QColor("#ffffff")  # Default white
        self.pushButton_buffer_color = QPushButton()
        self.pushButton_buffer_color.setFixedSize(50, 25)
        self.pushButton_buffer_color.setStyleSheet(f"background-color: {self.buffer_color.name()};")
        self.pushButton_buffer_color.clicked.connect(self._select_buffer_color)
        self.pushButton_buffer_color.setToolTip(self.tr("Click to select buffer color"))
        label_styling_layout.addWidget(self.pushButton_buffer_color, 4, 1)
        
        # Buffer Opacity
        label_styling_layout.addWidget(QLabel(self.tr("Buffer Opacity:")), 5, 0)
        self.slider_buffer_opacity = QSlider(Qt.Horizontal)
        self.slider_buffer_opacity.setRange(0, 100)
        self.slider_buffer_opacity.setValue(100)  # Default: fully opaque
        self.slider_buffer_opacity.setToolTip(self.tr("Buffer opacity (0-100%)"))
        label_styling_layout.addWidget(self.slider_buffer_opacity, 5, 1, 1, 2)
        
        # Show Labels Checkbox
        self.checkBox_show_label = QCheckBox(self.tr("Show Labels"))
        self.checkBox_show_label.setChecked(True)  # Default: show labels
        self.checkBox_show_label.setToolTip(self.tr("Enable/disable photo labels"))
        label_styling_layout.addWidget(self.checkBox_show_label, 6, 0, 1, 2)
        
        # Label Padding/Distance (NEW)
        label_styling_layout.addWidget(QLabel(self.tr("Label Distance:")), 7, 0)
        self.spinBox_label_padding = QDoubleSpinBox()
        self.spinBox_label_padding.setRange(0.0, 50.0)
        self.spinBox_label_padding.setSingleStep(0.5)
        self.spinBox_label_padding.setValue(3.0)  # Default: 3mm
        self.spinBox_label_padding.setSuffix(self.tr(" mm"))
        self.spinBox_label_padding.setToolTip(self.tr("Distance between label and icon symbol on map"))
        label_styling_layout.addWidget(self.spinBox_label_padding, 7, 1, 1, 2)
        
        # Advanced Label Settings Button
        self.pushButton_advanced_label = QPushButton(self.tr("Advanced Label Settings..."))
        self.pushButton_advanced_label.setToolTip(self.tr("Open QGIS layer properties for advanced label configuration"))
        label_styling_layout.addWidget(self.pushButton_advanced_label, 8, 0, 1, 3)
        
        layout.addWidget(label_styling_group)
        
        layout.addStretch(1)
        
        # --- Action Buttons Row (Apply, Close) ---
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        # Apply All Settings Button (Prominent)
        self.pushButton_apply_all_settings = QPushButton(self.tr("✓ Apply All Settings"))
        self.pushButton_apply_all_settings.setMinimumHeight(40)
        self.pushButton_apply_all_settings.setToolTip(self.tr("Apply click tolerance, icon size, and label styling"))
        self.pushButton_apply_all_settings.setStyleSheet("""
            QPushButton {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                  stop:0 #2ECC71,
                                                  stop:0.45 #27AE60,
                                                  stop:1 #1A7A43);
                color: white;
                border: 1px solid #166F3A;
                border-radius: 5px;
                font-weight: bold;
                font-size: 10pt;
                padding: 8px 20px;
                letter-spacing: 0.4px;
            }
            QPushButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                  stop:0 #3DDC82,
                                                  stop:0.45 #2ECC71,
                                                  stop:1 #22904F);
                border: 1px solid #1E8449;
            }
            QPushButton:pressed {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                  stop:0 #1A7A43, stop:1 #145E32);
                border: 1px solid #0F4A27;
                padding-top: 9px;
                padding-bottom: 7px;
            }
            QPushButton:disabled {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                  stop:0 #A8D5B5, stop:1 #8ABF9E);
                color: rgba(255,255,255,160);
                border: 1px solid #7AAD8B;
            }
        """)
        buttons_layout.addWidget(self.pushButton_apply_all_settings)
        
        # Close Button
        self.pushButton_cancel = QPushButton(self.tr("Close"))
        self.pushButton_cancel.setToolTip(self.tr("Close the settings dialog"))
        self.pushButton_cancel.setMinimumHeight(35)
        buttons_layout.addWidget(self.pushButton_cancel)
        
        layout.addLayout(buttons_layout)
        
        return tab

    def _create_filter_tab(self):
        """Creates the 'Filter' tab for date & time filtering."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # --- Filter Group ---
        filter_group = QGroupBox(self.tr("Date & Time Filter"))
        filter_layout = QGridLayout(filter_group)
        
        # Info label
        info_label = QLabel(self.tr(
            "Filter photos by date & time range. Photos outside the range will be hidden.\n"
            "Note: This is separate from manual visibility control."
        ))
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; font-style: italic;")
        filter_layout.addWidget(info_label, 0, 0, 1, 2)
        
        # Start date & time
        filter_layout.addWidget(QLabel(self.tr("Start Date & Time:")), 1, 0)
        self.dateTimeEdit_start = QDateTimeEdit()
        self.dateTimeEdit_start.setCalendarPopup(True)
        self.dateTimeEdit_start.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        # Set default to 30 days ago
        self.dateTimeEdit_start.setDateTime(QDateTime.currentDateTime().addDays(-30))
        self.dateTimeEdit_start.setToolTip(self.tr("Photos taken before this time will be hidden"))
        filter_layout.addWidget(self.dateTimeEdit_start, 1, 1)
        
        # End date & time
        filter_layout.addWidget(QLabel(self.tr("End Date & Time:")), 2, 0)
        self.dateTimeEdit_end = QDateTimeEdit()
        self.dateTimeEdit_end.setCalendarPopup(True)
        self.dateTimeEdit_end.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        # Set default to now
        self.dateTimeEdit_end.setDateTime(QDateTime.currentDateTime())
        self.dateTimeEdit_end.setToolTip(self.tr("Photos taken after this time will be hidden"))
        filter_layout.addWidget(self.dateTimeEdit_end, 2, 1)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.pushButton_apply_filter = QPushButton(self.tr("Apply Filter"))
        self.pushButton_apply_filter.setToolTip(self.tr("Apply date/time filter to photos"))
        self.pushButton_apply_filter.setMinimumHeight(35)
        button_layout.addWidget(self.pushButton_apply_filter)
        
        self.pushButton_remove_filter = QPushButton(self.tr("Remove Filter"))
        self.pushButton_remove_filter.setToolTip(self.tr("Remove filter and restore all photos (respecting manual visibility)"))
        self.pushButton_remove_filter.setMinimumHeight(35)
        button_layout.addWidget(self.pushButton_remove_filter)
        
        filter_layout.addLayout(button_layout, 3, 0, 1, 2)
        
        # Filter status label
        self.label_filter_status = QLabel(self.tr("Status: No filter applied"))
        self.label_filter_status.setStyleSheet("font-weight: bold; color: #0066cc;")
        self.label_filter_status.setWordWrap(True)
        filter_layout.addWidget(self.label_filter_status, 4, 0, 1, 2)
        
        layout.addWidget(filter_group)
        layout.addStretch(1)
        
        return tab
    
    def _create_imported_photos_tab(self):
        """Creates the 'Imported Photos' tab content (list and preview container)."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # This layout is a placeholder where the main plugin class (AdvancedPhotoImporter) 
        # will insert the PhotoListManager instance.
        # We store a reference to this layout so the plugin can dynamically add the widget.
        self.imported_photos_main_layout = layout
        
        # Add a placeholder label until the layer is loaded
        placeholder_label = QLabel(self.tr("Imported photos list will appear here after import."))
        placeholder_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(placeholder_label)
        
        return tab
    
    def _create_about_tab(self):
        """Creates the 'About' tab with professional styling and information."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(25, 15, 25, 15)
        layout.setSpacing(10)
        
        # Main Title
        title_label = QLabel(self.tr("Advanced Photo Importer"))
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #1a1a1a; padding: 3px;")
        layout.addWidget(title_label)
        
        # Subtitle
        subtitle_label = QLabel(self.tr("Enhance Your Geospatial Imagery Workflow"))
        subtitle_font = QFont()
        subtitle_font.setPointSize(13)
        subtitle_font.setItalic(True)
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("color: #4a4a4a; padding-bottom: 5px;")
        layout.addWidget(subtitle_label)
        
        # Separator line
        line1 = self._create_separator()
        layout.addWidget(line1)
        
        # Overview Section
        overview_title = QLabel(self.tr("Overview"))
        overview_title.setFont(self._section_title_font())
        overview_title.setStyleSheet("color: #2a2a2a; font-weight: bold; padding-top: 2px;")
        layout.addWidget(overview_title)
        
        overview_text = QLabel(self.tr(
            "Advanced Photo Importer is a powerful tool designed to simplify the integration of "
            "geotagged photos into QGIS. It focuses on easier photo import and management, and "
            "provides intuitive tools for quick modifications, ensuring a seamless transition from "
            "field data to spatial analysis."
        ))
        overview_text.setWordWrap(True)
        overview_text.setFont(self._body_text_font())
        overview_text.setStyleSheet("color: #3a3a3a; padding: 2px 0px;")
        layout.addWidget(overview_text)
        
        layout.addSpacing(3)
        
        # Separator
        line2 = self._create_separator()
        layout.addWidget(line2)
        
        # Developed By Section
        dev_title = QLabel(self.tr("Developed by"))
        dev_title.setFont(self._section_title_font())
        dev_title.setStyleSheet("color: #2a2a2a; font-weight: bold; padding-top: 2px;")
        layout.addWidget(dev_title)
        
        dev_name = QLabel(self.tr("Dr. Majid Jazebi"))
        dev_name.setFont(self._body_text_font())
        dev_name.setStyleSheet("color: #1a1a1a; font-weight: bold; font-size: 11pt; padding: 2px 0px;")
        layout.addWidget(dev_name)

        # Website link
        website_label = QLabel(
            '<a href="https://geotechzone.com/qgis/advanced-photo-importer" style="color: #2980b9; text-decoration: none;">'
            + self.tr("geotechzone.com") + '</a>'
        )
        website_label.setOpenExternalLinks(True)
        website_label.setFont(self._body_text_font())
        layout.addWidget(website_label)

        # GitHub link
        github_label = QLabel(
            '<a href="https://github.com/majidjazebi/advanced-photo-importer" style="color: #24292e; text-decoration: none;">'
            + self.tr("GitHub Repository") + '</a>'
        )
        github_label.setOpenExternalLinks(True)
        github_label.setFont(self._body_text_font())
        layout.addWidget(github_label)

        # LinkedIn link (clickable)
        linkedin_label = QLabel(
            '<a href="https://www.linkedin.com/in/majidjazebi/" style="color: #0077b5; text-decoration: none;">'
            + self.tr("Connect on LinkedIn") + '</a>'
        )
        linkedin_label.setOpenExternalLinks(True)
        linkedin_label.setFont(self._body_text_font())
        layout.addWidget(linkedin_label)
        
        layout.addSpacing(3)
        
        # Separator
        line3 = self._create_separator()
        layout.addWidget(line3)
        
        # Support & Feedback Section
        support_title = QLabel(self.tr("Support & Feedback"))
        support_title.setFont(self._section_title_font())
        support_title.setStyleSheet("color: #2a2a2a; font-weight: bold; padding-top: 2px;")
        layout.addWidget(support_title)
        
        support_text = QLabel(
            self.tr("If you encounter any issues or have suggestions for new features, please reach out via ") +
            '<a href="https://github.com/majidjazebi/advanced-photo-importer/issues" style="color: #e74c3c; text-decoration: none;">GitHub Issues</a>' +
            self.tr(" or visit the ") +
            '<a href="https://geotechzone.com/qgis/advanced-photo-importer" style="color: #2980b9; text-decoration: none;">plugin homepage</a>' +
            self.tr(" for documentation.")
        )
        support_text.setOpenExternalLinks(True)
        support_text.setWordWrap(True)
        support_text.setFont(self._body_text_font())
        support_text.setStyleSheet("color: #3a3a3a; padding: 2px 0px;")
        layout.addWidget(support_text)
        
        # Separator
        line4 = self._create_separator()
        layout.addWidget(line4)
        
        # --- Dependency Status Panel ---
        dep_title = QLabel(self.tr("Dependencies"))
        dep_title.setFont(self._section_title_font())
        dep_title.setStyleSheet("color: #2a2a2a; font-weight: bold; padding-top: 2px;")
        layout.addWidget(dep_title)
        
        self.dep_frame = QFrame()
        self.dep_frame.setFrameShape(QFrame.StyledPanel)
        dep_layout = QVBoxLayout(self.dep_frame)
        dep_layout.setContentsMargins(10, 8, 10, 8)

        self.dep_label = QLabel()
        self.dep_label.setWordWrap(True)
        dep_layout.addWidget(self.dep_label)

        layout.addWidget(self.dep_frame)
        self._refresh_dependency_panel()
        
        layout.addStretch(1)
        
        return tab
    
    def _section_title_font(self):
        """Returns a QFont configured for section titles."""
        font = QFont()
        font.setPointSize(13)
        font.setBold(True)
        return font
    
    def _body_text_font(self):
        """Returns a QFont configured for body text."""
        font = QFont()
        font.setPointSize(10)
        return font
    
    def _create_separator(self):
        """Creates a horizontal separator line."""
        from qgis.PyQt.QtWidgets import QFrame
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("color: #cccccc; margin: 2px 0px;")
        return line
        """Creates the 'Settings' tab content."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # --- Direction Line and Tolerance Group ---
        tolerance_group = QGroupBox(self.tr("Map Tool & Symbol Options"))
        tolerance_layout = QGridLayout(tolerance_group)
        
        # Click Tolerance Setting (QSpinBox)
        self.spinBox_tolerance = QSpinBox()
        self.spinBox_tolerance.setRange(1, 100)
        self.spinBox_tolerance.setSuffix(self.tr(" map units"))
        self.spinBox_tolerance.setToolTip(self.tr("Search radius for finding a photo feature when using the 'See Photo' tool."))
        
        tolerance_layout.addWidget(QLabel(self.tr("Click Tolerance:")), 0, 0)
        tolerance_layout.addWidget(self.spinBox_tolerance, 0, 1)
        
        # Icon Size Setting (QSpinBox)
        self.spinBox_icon_size = QSpinBox()
        self.spinBox_icon_size.setRange(10, 500)
        self.spinBox_icon_size.setSuffix(self.tr("%"))
        self.spinBox_icon_size.setValue(100)  # Default: 100%
        self.spinBox_icon_size.setToolTip(self.tr("Icon size as percentage of default size (100% = default)"))
        
        tolerance_layout.addWidget(QLabel(self.tr("Icon Size:")), 1, 0)
        tolerance_layout.addWidget(self.spinBox_icon_size, 1, 1)

        layout.addWidget(tolerance_group)
        
        # --- Label Styling Group ---
        label_styling_group = QGroupBox(self.tr("Label Styling"))
        label_styling_layout = QGridLayout(label_styling_group)
        
        # Font Size
        label_styling_layout.addWidget(QLabel(self.tr("Font Size:")), 0, 0)
        self.spinBox_font_size = QDoubleSpinBox()
        self.spinBox_font_size.setRange(1.0, 100.0)
        self.spinBox_font_size.setSingleStep(0.5)
        self.spinBox_font_size.setValue(7.0)  # Default: 7
        self.spinBox_font_size.setSuffix(self.tr(" pt"))
        label_styling_layout.addWidget(self.spinBox_font_size, 0, 1)
        
        # Font Style (Bold)
        label_styling_layout.addWidget(QLabel(self.tr("Font Style:")), 1, 0)
        self.checkBox_font_bold = QCheckBox(self.tr("Bold"))
        self.checkBox_font_bold.setChecked(True)  # Default: Bold
        label_styling_layout.addWidget(self.checkBox_font_bold, 1, 1)
        
        # Font Color
        label_styling_layout.addWidget(QLabel(self.tr("Font Color:")), 2, 0)
        self.pushButton_font_color = QPushButton()
        self.pushButton_font_color.setFixedSize(80, 25)
        self.font_color = QColor(0, 0, 0, 255)  # Black, 100% opacity
        self.pushButton_font_color.setStyleSheet(f"background-color: {self.font_color.name()};")
        self.pushButton_font_color.clicked.connect(self._select_font_color)
        label_styling_layout.addWidget(self.pushButton_font_color, 2, 1)
        
        # Font Opacity
        label_styling_layout.addWidget(QLabel(self.tr("Font Opacity:")), 3, 0)
        self.slider_font_opacity = QSlider(Qt.Horizontal)
        self.slider_font_opacity.setRange(0, 100)
        self.slider_font_opacity.setValue(100)  # Default: 100%
        self.label_font_opacity = QLabel("100%")
        self.slider_font_opacity.valueChanged.connect(
            lambda val: self.label_font_opacity.setText(f"{val}%")
        )
        opacity_h_layout = QHBoxLayout()
        opacity_h_layout.addWidget(self.slider_font_opacity)
        opacity_h_layout.addWidget(self.label_font_opacity)
        label_styling_layout.addLayout(opacity_h_layout, 3, 1)
        
        # Buffer Size
        label_styling_layout.addWidget(QLabel(self.tr("Buffer Size:")), 4, 0)
        self.spinBox_buffer_size = QDoubleSpinBox()
        self.spinBox_buffer_size.setRange(0.0, 10.0)
        self.spinBox_buffer_size.setSingleStep(0.1)
        self.spinBox_buffer_size.setValue(1.0)  # Default: 1
        self.spinBox_buffer_size.setSuffix(self.tr(" mm"))
        label_styling_layout.addWidget(self.spinBox_buffer_size, 4, 1)
        
        # Buffer Color
        label_styling_layout.addWidget(QLabel(self.tr("Buffer Color:")), 5, 0)
        self.pushButton_buffer_color = QPushButton()
        self.pushButton_buffer_color.setFixedSize(80, 25)
        self.buffer_color = QColor(255, 255, 255, 255)  # White, 100% opacity
        self.pushButton_buffer_color.setStyleSheet(f"background-color: {self.buffer_color.name()};")
        self.pushButton_buffer_color.clicked.connect(self._select_buffer_color)
        label_styling_layout.addWidget(self.pushButton_buffer_color, 5, 1)
        
        # Buffer Opacity
        label_styling_layout.addWidget(QLabel(self.tr("Buffer Opacity:")), 6, 0)
        self.slider_buffer_opacity = QSlider(Qt.Horizontal)
        self.slider_buffer_opacity.setRange(0, 100)
        self.slider_buffer_opacity.setValue(100)  # Default: 100%
        self.label_buffer_opacity = QLabel("100%")
        self.slider_buffer_opacity.valueChanged.connect(
            lambda val: self.label_buffer_opacity.setText(f"{val}%")
        )
        buffer_opacity_h_layout = QHBoxLayout()
        buffer_opacity_h_layout.addWidget(self.slider_buffer_opacity)
        buffer_opacity_h_layout.addWidget(self.label_buffer_opacity)
        label_styling_layout.addLayout(buffer_opacity_h_layout, 6, 1)
        
        # Show Label Checkbox
        self.checkBox_show_label = QCheckBox(self.tr("Show Label"))
        self.checkBox_show_label.setChecked(True)  # Default to enabled
        self.checkBox_show_label.setToolTip(self.tr("Enable or disable labels on the photo layer"))
        label_styling_layout.addWidget(self.checkBox_show_label, 7, 0, 1, 2)
        
        layout.addWidget(label_styling_group)
        
        # --- Unified Apply Button (for all settings) ---
        apply_button_layout = QHBoxLayout()
        self.pushButton_apply_all_settings = QPushButton(self.tr("Apply All Settings"))
        self.pushButton_apply_all_settings.setToolTip(self.tr("Apply click tolerance, icon size, and label styling settings"))
        self.pushButton_apply_all_settings.setStyleSheet("QPushButton { font-weight: bold; padding: 8px; }")
        apply_button_layout.addStretch()
        apply_button_layout.addWidget(self.pushButton_apply_all_settings)
        apply_button_layout.addStretch()
        layout.addLayout(apply_button_layout)
        
        # Advanced Label Setting Button (separate from apply)
        advanced_button_layout = QHBoxLayout()
        self.pushButton_advanced_label = QPushButton(self.tr("Advanced Label Settings"))
        self.pushButton_advanced_label.setToolTip(self.tr("Open layer labeling properties dialog"))
        advanced_button_layout.addStretch()
        advanced_button_layout.addWidget(self.pushButton_advanced_label)
        advanced_button_layout.addStretch()
        layout.addLayout(advanced_button_layout)
        
        # --- Export/Import Group (moved to bottom) ---
        export_import_group = QGroupBox(self.tr("Excel File Management"))
        export_import_layout = QHBoxLayout(export_import_group)
        
        self.pushButton_export = QPushButton(self.tr("Export Excel File"))
        self.pushButton_export.setToolTip(self.tr("Save a copy of the Excel management file to a specified location"))
        
        self.pushButton_import = QPushButton(self.tr("Import from Excel"))
        self.pushButton_import.setToolTip(self.tr("Import photos from an Excel file and create a new layer"))
        
        export_import_layout.addWidget(self.pushButton_export)
        export_import_layout.addWidget(self.pushButton_import)
        
        layout.addWidget(export_import_group)
        layout.addStretch(1)

        return tab

    # --- Utility Methods ---
    
    def _emit_tolerance_signal_from_spinbox(self):
        """Emits the tolerance when the spin box editing finishes."""
        self.apply_tolerance_clicked.emit(float(self.spinBox_tolerance.value()))
    
    def toggle_output_widgets(self, checked):
        """Enables/disables the output path widgets and updates the status display."""
        
        # Enable/Disable browse widgets
        self.lineEdit_output_path.setVisible(checked)
        self.pushButton_browse_output.setVisible(checked)
        if self.label_layer_path:
            self.label_layer_path.setVisible(checked)
        
        # Update the Current Output Label based on state
        if checked:
            path_text = self.lineEdit_output_path.text()
            if path_text:
                self.label_current_output.setText(f"{self.tr('File:')} {os.path.basename(path_text)}")
                self.label_current_output.setStyleSheet("QLabel { font-weight: bold; color: purple; }")
            else:
                self.label_current_output.setText(self.tr("Pending file selection..."))
                self.label_current_output.setStyleSheet("QLabel { font-weight: normal; color: orange; }")
        else:
            self.label_current_output.setText(f"{self.tr('Temporary Layer:')} {self.IN_MEMORY_LAYER_NAME}")
            self.label_current_output.setStyleSheet("QLabel { font-weight: bold; color: green; }")
        
        # Disable symbol tools and Settings tab when using an existing layer
        symbol_group = self.findChild(QGroupBox, self.tr("Point Symbol Selection (icons/2-Pins)"))
        
        # Disable symbol group and interaction group
        if symbol_group:
            symbol_group.setEnabled(not checked)
        
        # Disable the entire Settings tab (index 0 now since Groups tab removed)
        self.tab_widget.setTabEnabled(0, not checked)
        # Disable the Imported Photos tab (index 1) as its data depends on the layer being managed
        # Note: You might want to enable this if you decide to allow editing existing layer points.
        # self.tab_widget.setTabEnabled(1, not checked) 
        

    
    def _select_font_color(self):
        """Opens a color dialog to select font color."""
        color = QColorDialog.getColor(self.font_color, self, self.tr("Select Font Color"))
        if color.isValid():
            self.font_color = color
            self.pushButton_font_color.setStyleSheet(f"background-color: {color.name()};")
    
    def _select_buffer_color(self):
        """Opens a color dialog to select buffer color."""
        color = QColorDialog.getColor(self.buffer_color, self, self.tr("Select Buffer Color"))
        if color.isValid():
            self.buffer_color = color
            self.pushButton_buffer_color.setStyleSheet(f"background-color: {color.name()};")

