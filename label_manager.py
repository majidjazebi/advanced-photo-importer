# -*- coding: utf-8 -*-
# Copyright (C) 2026 Majid Jazebi
# Web: Geotechzone.com
# All rights reserved.
# This plugin is licensed under GNU GPL v3.
"""
Label Manager for Advanced Photo Importer
Handles photo labeling configuration and styling.
"""

from qgis.core import (
    QgsPalLayerSettings,
    QgsTextFormat,
    QgsTextBufferSettings,
    QgsVectorLayerSimpleLabeling,
    Qgis,
    QgsMessageLog,
    QgsProperty
)
from qgis.PyQt.QtGui import QColor, QFont


class LabelManager:
    """Manages photo layer labeling configuration and styling."""

    def __init__(self, iface):
        """Initialize the label manager."""
        self.iface = iface
        # Default label settings
        self.font_size = 7.0
        self.font_bold = True  # Default: Bold enabled
        self.font_color = QColor(0, 0, 0, 255)  # Black, 100% opacity
        self.buffer_size = 1.0  # Default: 1.0mm buffer
        self.buffer_color = QColor(255, 255, 255, 255)  # White, 100% opacity
        self.label_field = 'label_text'  # Label with custom text (filename by default)
        self.label_distance = 3.0  # Default: 3mm distance from symbol
        
    def apply_labeling(self, layer, enable_labels=True):
        """
        Apply single labeling to the photo layer.
        
        Args:
            layer: QgsVectorLayer - The photo layer to apply labeling to
            enable_labels: bool - Whether to enable or disable labeling
        """
        if not layer or not layer.isValid():
            QgsMessageLog.logMessage(
                "Invalid layer provided for labeling",
                'Photo Plugin',
                Qgis.Warning
            )
            return False
        
        if not enable_labels:
            # Disable labeling
            layer.setLabelsEnabled(False)
            layer.setLabeling(None)
            layer.triggerRepaint()
            return True
        
        # Create label settings
        label_settings = QgsPalLayerSettings()
        
        # Set the field to label from
        label_settings.fieldName = self.label_field
        label_settings.isExpression = False
        
        # Create text format
        text_format = QgsTextFormat()
        
        # Set font
        font = QFont()
        font.setPointSizeF(self.font_size)
        font.setBold(self.font_bold)
        text_format.setFont(font)
        text_format.setSize(self.font_size)
        text_format.setSizeUnit(Qgis.RenderUnit.Points)
        
        # Set font color and opacity
        text_format.setColor(self.font_color)
        text_format.setOpacity(self.font_color.alphaF())
        
        # Configure buffer
        buffer_settings = QgsTextBufferSettings()
        buffer_settings.setEnabled(True)
        buffer_settings.setSize(self.buffer_size)
        buffer_settings.setSizeUnit(Qgis.RenderUnit.Millimeters)
        buffer_settings.setColor(self.buffer_color)
        buffer_settings.setOpacity(self.buffer_color.alphaF())
        
        # Apply buffer to text format
        text_format.setBuffer(buffer_settings)
        
        # Apply text format to label settings
        label_settings.setFormat(text_format)
        
        # Set label placement
        label_settings.placement = Qgis.LabelPlacement.OrderedPositionsAroundPoint
        
        # Set label distance from symbol (padding)
        label_settings.dist = self.label_distance
        label_settings.distUnits = Qgis.RenderUnit.Millimeters
        
        # Disable obstacle detection and allow overlaps to show all labels
        label_settings.obstacleSettings().setIsObstacle(False)
        
        # Allow labels to overlap with other labels and features
        # This ensures all labels are shown even if they overlap
        if hasattr(label_settings, 'setOverlapHandling'):
            # QGIS 3.26+
            label_settings.setOverlapHandling(Qgis.LabelOverlapHandling.AllowOverlapIfRequired)
        
        # Enable labels
        label_settings.enabled = True
        
        # Add data-defined property to hide labels for invisible (selected) features
        # When svg_icon is 'Invisible.svg', hide the label
        label_settings.dataDefinedProperties().setProperty(
            QgsPalLayerSettings.Show,
            QgsProperty.fromExpression("\"svg_icon\" != 'Invisible.svg'")
        )
        
        # Create simple labeling
        labeling = QgsVectorLayerSimpleLabeling(label_settings)
        
        # Apply labeling to layer
        layer.setLabeling(labeling)
        layer.setLabelsEnabled(True)
        
        # Trigger repaint
        layer.triggerRepaint()
        
        QgsMessageLog.logMessage(
            f"Labeling applied to layer: {layer.name()}",
            'Photo Plugin',
            Qgis.Info
        )
        
        return True
    
    def update_label_style(self, font_size=None, font_bold=None, font_color=None, 
                          buffer_size=None, buffer_color=None, label_distance=None):
        """
        Update label style settings.
        
        Args:
            font_size: float - Font size in points
            font_bold: bool - Whether font should be bold
            font_color: QColor - Font color with alpha
            buffer_size: float - Buffer size in mm
            buffer_color: QColor - Buffer color with alpha
            label_distance: float - Distance from symbol in mm
        """
        if font_size is not None:
            self.font_size = font_size
        if font_bold is not None:
            self.font_bold = font_bold
        if font_color is not None:
            self.font_color = font_color
        if buffer_size is not None:
            self.buffer_size = buffer_size
        if buffer_color is not None:
            self.buffer_color = buffer_color
        if label_distance is not None:
            self.label_distance = label_distance
    
    def set_label_field(self, field_name):
        """
        Set which field to use for labeling.
        
        Args:
            field_name: str - Name of the field to label from
        """
        self.label_field = field_name
    
    def get_label_settings(self):
        """
        Get current label settings as a dictionary.
        
        Returns:
            dict - Current label settings
        """
        return {
            'font_size': self.font_size,
            'font_bold': self.font_bold,
            'font_color': self.font_color,
            'buffer_size': self.buffer_size,
            'buffer_color': self.buffer_color,
            'label_field': self.label_field,
            'label_distance': self.label_distance
        }

