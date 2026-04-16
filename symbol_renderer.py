# -*- coding: utf-8 -*-
# Copyright (C) 2026 Majid Jazebi
# Web: Geotechzone.com
# All rights reserved.
# This plugin is licensed under GNU GPL v3.
"""
Symbol and Renderer Management

Handles symbol creation, rendering, and layer styling for photo markers.
"""

import os
from qgis.PyQt.QtGui import QColor
from qgis.core import (
    QgsMarkerSymbol,
    QgsSimpleMarkerSymbolLayer,
    QgsSvgMarkerSymbolLayer,
    QgsSingleSymbolRenderer,
    QgsCategorizedSymbolRenderer,
    QgsRendererCategory,
    QgsRuleBasedRenderer,
    QgsLineSymbol,
    QgsSimpleLineSymbolLayer,
    QgsMarkerLineSymbolLayer,
    QgsGeometryGeneratorSymbolLayer,
    QgsWkbTypes,
    QgsMessageLog,
    Qgis,
    QgsVectorLayer,
)


class SymbolRenderer:
    """Handles all symbol creation and renderer management."""
    
    def __init__(self, mandatory_icons_dir, default_symbol_path, camera_icons_dir=None):
        """Initialize with paths to icon directories."""
        self.mandatory_icons_dir = mandatory_icons_dir
        self.default_symbol_path = default_symbol_path
        self.camera_icons_dir = camera_icons_dir  # icons/2-Cameras directory
        self.no_arrow_icons_dir = os.path.join(camera_icons_dir, 'No arrow') if camera_icons_dir else None
        self.icon_size_percentage = 100  # Default size percentage
        # Whether icons should be rotated according to the 'direction' field
        self.include_direction = True
        # Currently selected camera icon filename (e.g. 'Cam1.svg'); None = use default '0.svg'
        self.selected_icon = None
    
    def get_base_svg_filename(self, angle):
        """
        LEGACY METHOD: Returns '0.svg' for all angles.
        Rotation is now handled by symbol rotation, not different icon files.
        Kept for backward compatibility only.
        """
        return "0.svg"
    
    def set_icon_size_percentage(self, percentage):
        """Set the icon size percentage (10-500%)."""
        self.icon_size_percentage = max(10, min(500, percentage))
    
    def get_actual_icon_size(self):
        """Calculate the actual icon size based on base size and percentage."""
        base_size = 10.0
        return base_size * (self.icon_size_percentage / 100.0)

    def create_base_symbol(self, svg_filename=None, rotation_angle=None):
        """
        Creates a QgsMarkerSymbol using the base 0.svg icon with rotation.
        
        Args:
            svg_filename: Icon name (0.svg, Invisible.svg, etc.)
            rotation_angle: Rotation angle in degrees (0-360)
        """
        # Always use 0.svg as base (unless it's Invisible.svg)
        if svg_filename == 'Invisible.svg':
            icon_path = os.path.join(self.mandatory_icons_dir, 'Invisible.svg')
        else:
            icon_path = self.default_symbol_path

        symbol = QgsMarkerSymbol()
        symbol.deleteSymbolLayer(0) 
        symbol_layer = None
        
        if icon_path and icon_path.lower().endswith('.svg'):
            if os.path.exists(icon_path):
                try:
                    symbol_layer = QgsSvgMarkerSymbolLayer(icon_path)
                    actual_size = self.get_actual_icon_size()
                    symbol_layer.setSize(actual_size)
                    
                    if rotation_angle is not None and svg_filename != 'Invisible.svg' and self.include_direction:
                        symbol_layer.setAngle(rotation_angle)
                except Exception as e:
                    QgsMessageLog.logMessage(f"[ERROR] Failed to load SVG {icon_path}: {e}", 'Photo Plugin', Qgis.Critical)
                    symbol_layer = None
            else:
                QgsMessageLog.logMessage(f"[ERROR] SVG file not found: {icon_path}", 'Photo Plugin', Qgis.Warning)
                symbol_layer = None
        
        if not symbol_layer:
            actual_size = self.get_actual_icon_size()
            symbol_layer = QgsSimpleMarkerSymbolLayer.create({'color': '255,0,0,255', 'size': str(actual_size), 'name': 'circle'})

        symbol.appendSymbolLayer(symbol_layer)
        return symbol

    def apply_categorized_renderer(self, photo_layer):
        """
        Creates and returns a Categorized Renderer based on the 'svg_icon' field.
        Also includes Invisible.svg as a category in the layer panel.
        """
        if not photo_layer or photo_layer.fields().indexOf('svg_icon') < 0:
            return QgsSingleSymbolRenderer(self.create_base_symbol()) 

        field_name = 'svg_icon'
        categories = []
        
        unique_icons = set()
        for feature in photo_layer.getFeatures():
            icon_name = feature.attribute(field_name)
            if icon_name:
                unique_icons.add(icon_name)
        
        # Add Invisible.svg to the categories even if no features have it
        unique_icons.add('Invisible.svg')

        for unique_category_name in sorted(list(unique_icons)):
            
            # The symbol creation is dynamic now, reading the base file name from the category name
            category_symbol = self.create_base_symbol(svg_filename=unique_category_name)
            
            category = QgsRendererCategory(unique_category_name, category_symbol, unique_category_name)
            categories.append(category)

        renderer = QgsCategorizedSymbolRenderer(field_name, categories)
        
        return renderer
    
    @staticmethod
    def _direction_is_null(val):
        """Return True if val is a missing/NULL direction.

        Handles both Python None AND the PyQGIS NULL singleton, which is
        returned by feature.attribute() in some QGIS versions instead of None.
        Uses a float-conversion test so any non-numeric value is treated as null.
        """
        if val is None:
            return True
        try:
            float(val)
            return False  # successfully converted → a real numeric direction
        except (TypeError, ValueError):
            return True   # conversion failed → NULL / invalid

    def _get_no_arrow_name(self, icon_name):
        """Return the 'No arrow/CamX.svg' virtual name if a no-arrow variant exists, else None.
        This value can be stored directly in the svg_icon layer attribute."""
        if icon_name.startswith('Cam') and icon_name.endswith('.svg') and self.no_arrow_icons_dir:
            path = os.path.join(self.no_arrow_icons_dir, icon_name)
            if os.path.exists(path):
                return 'No arrow/' + icon_name
        return None

    def _get_icon_path(self, icon_name):
        """Resolve an svg_icon field value to the actual filesystem path.
        Handles 'No arrow/CamX.svg' virtual names, regular camera icons, and mandatory icons."""
        if icon_name.startswith('No arrow/'):
            cam_name = icon_name[len('No arrow/'):]
            if self.no_arrow_icons_dir:
                return os.path.join(self.no_arrow_icons_dir, cam_name)
            return os.path.join(os.path.dirname(self.mandatory_icons_dir), '2-Cameras', 'No arrow', cam_name)
        elif icon_name.startswith('Cam') and icon_name.endswith('.svg'):
            if self.camera_icons_dir:
                return os.path.join(self.camera_icons_dir, icon_name)
            return os.path.join(os.path.dirname(self.mandatory_icons_dir), '2-Cameras', icon_name)
        else:
            return os.path.join(self.mandatory_icons_dir, icon_name)

    def _get_no_arrow_path(self, icon_name):
        """Deprecated: use _get_no_arrow_name() + _get_icon_path() instead."""
        name = self._get_no_arrow_name(icon_name)
        return self._get_icon_path(name) if name else None

    def _resolve_icon_for_direction(self, current_icon, new_direction):
        """Return the correct svg_icon name to store after a direction value changes.

        Called when the user manually edits the direction field of an existing feature.

        Rules:
          - If the new direction is a valid number AND direction display is on
            → return the normal camera icon (e.g. 'Cam1.svg' or '0.svg')
          - Otherwise (direction cleared to NULL, or direction display off)
            → return the no-arrow variant if one exists, else the normal icon.

        'current_icon' may already be 'No arrow/CamX.svg' or 'CamX.svg'.
        Returns the target icon name, or None if no change is required.
        """
        # Normalise: strip the 'No arrow/' prefix to get the base camera name
        if current_icon.startswith('No arrow/'):
            base_icon = current_icon[len('No arrow/'):]
        else:
            base_icon = current_icon  # e.g. 'Cam1.svg' or '0.svg'

        direction_absent = self._direction_is_null(new_direction)
        use_no_arrow = direction_absent or not self.include_direction

        if use_no_arrow:
            no_arrow_name = self._get_no_arrow_name(base_icon)
            target = no_arrow_name if no_arrow_name else base_icon
        else:
            target = base_icon  # direction is valid → show normal icon with rotation

        return target if target != current_icon else None  # None = no change needed

    def _create_symbol_for_rule(self, icon_path, apply_rotation=False):
        """Create a QgsMarkerSymbol for use in a rule-based renderer rule."""
        from qgis.core import QgsProperty
        symbol = QgsMarkerSymbol()
        symbol.deleteSymbolLayer(0)
        svg_layer = QgsSvgMarkerSymbolLayer(icon_path)
        svg_layer.setSize(self.get_actual_icon_size())
        if apply_rotation:
            svg_layer.setDataDefinedProperty(
                QgsSvgMarkerSymbolLayer.PropertyAngle,
                QgsProperty.fromField('direction')
            )
        symbol.appendSymbolLayer(svg_layer)
        return symbol

    def apply_rule_based_rotation_renderer(self, photo_layer):
        """
        Creates a Rule-Based Renderer with ONE rule per unique svg_icon value.

        The no-arrow vs rotation decision is encoded directly in the svg_icon
        attribute value:
          'CamX.svg'          -> drawn from 2-Cameras/CamX.svg WITH rotation
          'No arrow/CamX.svg' -> drawn from 2-Cameras/No arrow/CamX.svg, no rotation
          'Invisible.svg'     -> transparent, no rotation
          '0.svg'             -> drawn from 1-Mandatory/0.svg WITH rotation
        No IS NULL QGIS expressions are used.
        """
        from qgis.core import QgsRuleBasedRenderer

        root_rule = QgsRuleBasedRenderer.Rule(None)

        unique_icons = set()
        for feature in photo_layer.getFeatures():
            icon_name = feature.attribute('svg_icon')
            if icon_name:
                unique_icons.add(icon_name)
        unique_icons.add('Invisible.svg')

        for icon_name in sorted(unique_icons):
            icon_path = self._get_icon_path(icon_name)

            is_no_arrow = icon_name.startswith('No arrow/')
            is_invisible = icon_name == 'Invisible.svg'
            is_directional = (
                (icon_name.startswith('Cam') and icon_name.endswith('.svg'))
                or icon_name == '0.svg'
            )
            apply_rotation = (
                self.include_direction and is_directional
                and not is_no_arrow and not is_invisible
            )

            symbol = self._create_symbol_for_rule(icon_path, apply_rotation)
            rule = QgsRuleBasedRenderer.Rule(symbol)
            rule.setFilterExpression(f'"svg_icon" = \'{icon_name}\'')
            rule.setLabel(icon_name)
            root_rule.appendChild(rule)

        renderer = QgsRuleBasedRenderer(root_rule)
        return renderer

    def set_include_direction(self, include):
        """Enable or disable rotation of icons based on the `direction` field."""
        self.include_direction = bool(include)

    def apply_rule_based_renderer(self, photo_layer):
        """Returns the rule-based renderer with data-driven rotation."""
        return self.apply_rule_based_rotation_renderer(photo_layer)

    def update_layer_symbol_manually(self, photo_layer, iface):
        """Manually forces an update of the layer's symbol using a Rule-Based Renderer."""
        if not photo_layer or not photo_layer.isValid():
            return

        renderer = self.apply_rule_based_renderer(photo_layer)
        photo_layer.setRenderer(renderer)
        self.setup_visibility_handler(photo_layer, iface)
        photo_layer.triggerRepaint()
        iface.mapCanvas().refresh()

    def apply_transparent_selection_symbol(self, photo_layer, iface):
        """
        Creates and applies a fully transparent symbol for selected features 
        to hide the default yellow selection markers.
        
        CRITICAL FIX: Checks if setSelectionSymbol exists before calling it, 
        to handle potential API inconsistencies in different QGIS versions.
        """
        if not photo_layer or not isinstance(photo_layer, QgsVectorLayer):
             return

        # 1. Create a fully transparent symbol
        transparent_symbol = QgsMarkerSymbol.defaultSymbol(photo_layer.geometryType()).clone()

        # Ensure ALL layers are transparent and size 0
        for i in range(transparent_symbol.symbolLayerCount()):
             sl = transparent_symbol.symbolLayer(i)
             sl.setStrokeColor(QColor(0, 0, 0, 0)) # Fully Transparent Stroke
             sl.setFillColor(QColor(0, 0, 0, 0))   # Fully Transparent Fill
             sl.setSize(0) # Set size to zero

        # 2. Check for the method's existence before calling it
        if hasattr(photo_layer, 'setSelectionSymbol'):
            # The correct QGIS 3+ API method
            photo_layer.setSelectionSymbol(transparent_symbol) 
        else:
             # Log a warning if the API is missing, but continue execution
             QgsMessageLog.logMessage(
                 "WARNING: QgsVectorLayer.setSelectionSymbol API missing. Cannot guarantee yellow selection marker is hidden on selection. Try updating QGIS.", 
                 'Photo Plugin', 
                 Qgis.Warning
             )
        
        photo_layer.triggerRepaint()
        iface.mapCanvas().refresh()

    def setup_visibility_handler(self, photo_layer, iface):
        """
        Sets up a handler to change svg_icon to Invisible.svg when features are selected (hidden)
        and restore original svg_icon when deselected (visible).
        """
        # Store original svg_icon values as instance variable to persist
        if not hasattr(self, 'original_svg_icons'):
            self.original_svg_icons = {}
        
        # Store reference to this renderer on the layer for access from other modules
        photo_layer._symbol_renderer = self
        
        # --- FIX C1: Disconnect previous handler to prevent signal stacking ---
        if hasattr(self, '_visibility_handler') and self._visibility_handler is not None:
            try:
                photo_layer.selectionChanged.disconnect(self._visibility_handler)
            except TypeError:
                pass  # Was not connected
        
        def on_selection_changed(selected, deselected, clearAndSelect):
            """Handle selection changes to update svg_icon field."""
            photo_layer.startEditing()
            
            # For newly selected features (hidden): change to Invisible.svg
            for fid in selected:
                feature = photo_layer.getFeature(fid)
                if feature.isValid():
                    current_icon = feature.attribute('svg_icon')
                    if current_icon != 'Invisible.svg':
                        backup_idx = photo_layer.fields().indexOf('svg_icon_backup')
                        if backup_idx >= 0 and current_icon:
                            photo_layer.changeAttributeValue(fid, backup_idx, current_icon)
                        photo_layer.changeAttributeValue(fid, photo_layer.fields().indexOf('svg_icon'), 'Invisible.svg')
            
            # For deselected features: check if they should be visible
            for fid in deselected:
                feature = photo_layer.getFeature(fid)
                if feature.isValid():
                    visible_idx = photo_layer.fields().indexOf('visible')
                    filter_visibility_idx = photo_layer.fields().indexOf('filterVisibility')
                    manual_visible = feature.attribute('visible') if visible_idx >= 0 else True
                    filter_visible = feature.attribute('filterVisibility') if filter_visibility_idx >= 0 else True
                    
                    if manual_visible and filter_visible:
                        backup_idx = photo_layer.fields().indexOf('svg_icon_backup')
                        restored = None
                        if backup_idx >= 0:
                            restored = feature.attribute('svg_icon_backup')
                        if restored:
                            photo_layer.changeAttributeValue(fid, photo_layer.fields().indexOf('svg_icon'), restored)
                        else:
                            photo_layer.changeAttributeValue(fid, photo_layer.fields().indexOf('svg_icon'), '0.svg')
                    else:
                        photo_layer.changeAttributeValue(fid, photo_layer.fields().indexOf('svg_icon'), 'Invisible.svg')
            
            photo_layer.commitChanges()
            photo_layer.triggerRepaint()
            iface.mapCanvas().refresh()
        
        # Connect to selection changed signal and store reference for cleanup
        self._visibility_handler = on_selection_changed
        photo_layer.selectionChanged.connect(on_selection_changed)
