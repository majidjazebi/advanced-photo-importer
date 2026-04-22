# -*- coding: utf-8 -*-
# Copyright (C) 2026 Majid Jazebi
# Web: Geotechzone.com
# All rights reserved.
# This plugin is licensed under GNU GPL v3.
"""
Layer Management Utilities

Handles creation, management, and manipulation of photo layers and features.
"""

import os
import warnings
from qgis.PyQt.QtWidgets import QMessageBox

# Qt 5 (QGIS 3) uses QVariant type enums; Qt 6 (QGIS 4) uses QMetaType.Type
try:
    from qgis.PyQt.QtCore import QVariant
    _QT_STRING = QVariant.String
    _QT_DOUBLE = QVariant.Double
    _QT_BOOL   = QVariant.Bool
except (ImportError, AttributeError):
    from qgis.PyQt.QtCore import QMetaType
    _QT_STRING = QMetaType.Type.QString
    _QT_DOUBLE = QMetaType.Type.Double
    _QT_BOOL   = QMetaType.Type.Bool
from qgis.core import (
    QgsVectorLayer,
    QgsField,
    QgsFields,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsCoordinateTransform,
    QgsCoordinateReferenceSystem,
    QgsProject,
    QgsRectangle,
    QgsMessageLog,
    Qgis,
    QgsVectorFileWriter,
    QgsWkbTypes,
)


class LayerManager:
    """Manages photo layer creation, feature addition, and layer operations."""
    
    def __init__(self, symbol_renderer):
        """Initialize with a reference to the symbol renderer."""
        self.symbol_renderer = symbol_renderer
    
    def create_point_layer(self, iface, photo_layer, photo_list_manager, output_uri=None):
        """
        Creates the in-memory point layer or opens an existing layer if output_uri is provided.
        Returns the QgsVectorLayer instance.
        """
        # Check if photo_layer is still valid (avoid RuntimeError with deleted C++ objects)
        layer_is_valid = False
        if photo_layer is not None:
            try:
                layer_is_valid = photo_layer.isValid()
            except RuntimeError:
                # Layer has been deleted, reset reference
                photo_layer = None
        
        if layer_is_valid:
            layer_in_project = QgsProject.instance().mapLayers().get(photo_layer.id())
            
            if output_uri and photo_layer.source() != output_uri:
                QgsProject.instance().removeMapLayer(photo_layer.id())
                photo_layer = None
            
            elif layer_in_project is not None:
                # If layer is already in project, just update its renderer
                self.symbol_renderer.update_layer_symbol_manually(photo_layer, iface) 
                
                # Re-apply transparent selection symbol (safety)
                self.symbol_renderer.apply_transparent_selection_symbol(photo_layer, iface) 
                return photo_layer
            else:
                photo_layer = None
        
        layer_name = 'Photo Locations (In-Memory)'
        
        if output_uri:
            # Check if file already exists - if yes, load it; if no, create new layer and save it
            if os.path.exists(output_uri):
                layer_name = os.path.basename(output_uri)
                layer = QgsVectorLayer(output_uri, layer_name, 'ogr')
                
                if not layer.isValid(): 
                    QMessageBox.critical(None, "Layer Error", f"Failed to load output layer: {layer_name}")
                    return None
                
                # IMPORTANT: Clear all existing features from the layer
                # This ensures we're replacing the layer content, not appending to it
                if layer.dataProvider().featureCount() > 0:
                    feature_ids = [f.id() for f in layer.getFeatures()]
                    layer.dataProvider().deleteFeatures(feature_ids)
                    QgsMessageLog.logMessage(
                        f"[LAYER] Cleared {len(feature_ids)} existing features from {layer_name}",
                        'Photo Plugin',
                        Qgis.Info
                    )
                
                QgsProject.instance().addMapLayer(layer)
                photo_layer = layer # Set layer before applying style
            else:
                # Create new file-based layer
                layer_name = os.path.basename(output_uri)
                
                # Determine driver based on extension
                if output_uri.lower().endswith('.gpkg'):
                    driver_name = 'GPKG'
                    layer_name_in_gpkg = os.path.splitext(layer_name)[0]
                elif output_uri.lower().endswith('.shp'):
                    driver_name = 'ESRI Shapefile'
                    layer_name_in_gpkg = None
                else:
                    QMessageBox.critical(None, "Layer Error", "Unsupported file format. Use .gpkg or .shp")
                    return None
                
                # Define fields
                fields = QgsFields()
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", DeprecationWarning)
                    fields.append(QgsField('path', _QT_STRING, 'string', 255))
                    fields.append(QgsField('latitude', _QT_DOUBLE, 'double', 20, 6))
                    fields.append(QgsField('longitude', _QT_DOUBLE, 'double', 20, 6))
                    fields.append(QgsField('direction', _QT_DOUBLE, 'double', 20, 2))
                    fields.append(QgsField('svg_icon', _QT_STRING, '', 20))
                    fields.append(QgsField('svg_icon_backup', _QT_STRING, '', 50))
                    fields.append(QgsField('visible', _QT_BOOL, 'boolean'))
                    fields.append(QgsField('group', _QT_STRING, 'string', 100))
                    fields.append(QgsField('label_text', _QT_STRING, 'string', 255))
                    fields.append(QgsField('label_visible', _QT_BOOL, 'boolean'))
                    fields.append(QgsField('label_offset_x', _QT_DOUBLE, 'double', 20, 2))
                    fields.append(QgsField('label_offset_y', _QT_DOUBLE, 'double', 20, 2))
                    fields.append(QgsField('photo_time', _QT_STRING, 'string', 100))
                    fields.append(QgsField('filterVisibility', _QT_BOOL, 'boolean'))
                
                # Write the layer to file
                from qgis.core import QgsVectorFileWriter
                crs = QgsCoordinateReferenceSystem('EPSG:4326')
                
                save_options = QgsVectorFileWriter.SaveVectorOptions()
                save_options.driverName = driver_name
                save_options.fileEncoding = 'UTF-8'
                if driver_name == 'GPKG' and layer_name_in_gpkg:
                    save_options.layerName = layer_name_in_gpkg
                
                writer = QgsVectorFileWriter.create(
                    output_uri,
                    fields,
                    QgsWkbTypes.Point,
                    crs,
                    QgsProject.instance().transformContext(),
                    save_options
                )
                
                if writer.hasError() != QgsVectorFileWriter.NoError:
                    QMessageBox.critical(None, "Layer Error", f"Failed to create layer file: {writer.errorMessage()}")
                    return None
                
                del writer  # Close the file
                
                # Now load the layer
                layer = QgsVectorLayer(output_uri, layer_name, 'ogr')
                if not layer.isValid():
                    QMessageBox.critical(None, "Layer Error", f"Failed to load created layer: {layer_name}")
                    return None
                
                QgsProject.instance().addMapLayer(layer)
                photo_layer = layer
            
        else:
            # Creation of new in-memory layer
            fields = QgsFields()
            
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                fields.append(QgsField('path', _QT_STRING, 'string', 255))
                fields.append(QgsField('latitude', _QT_DOUBLE, 'double', 20, 6))
                fields.append(QgsField('longitude', _QT_DOUBLE, 'double', 20, 6))
                fields.append(QgsField('direction', _QT_DOUBLE, 'double', 20, 2))
                fields.append(QgsField('svg_icon', _QT_STRING, '', 20))
                fields.append(QgsField('svg_icon_backup', _QT_STRING, '', 50))
                fields.append(QgsField('visible', _QT_BOOL, 'boolean'))
                fields.append(QgsField('group', _QT_STRING, 'string', 100))
                fields.append(QgsField('label_text', _QT_STRING, 'string', 255))
                fields.append(QgsField('label_visible', _QT_BOOL, 'boolean'))
                fields.append(QgsField('label_offset_x', _QT_DOUBLE, 'double', 20, 2))
                fields.append(QgsField('label_offset_y', _QT_DOUBLE, 'double', 20, 2))
                fields.append(QgsField('photo_time', _QT_STRING, 'string', 100))  # Photo capture time
                fields.append(QgsField('filterVisibility', _QT_BOOL, 'boolean'))  # Date/time filter visibility (separate from manual visibility)

            uri = "Point?crs=epsg:4326&field=path:string(255)&field=latitude:double&field=longitude:double&field=direction:double&field=svg_icon:string(20)&field=svg_icon_backup:string(50)&field=visible:boolean&field=group:string(100)&field=label_text:string(255)&field=label_visible:boolean&field=label_offset_x:double&field=label_offset_y:double&field=photo_time:string(100)&field=filterVisibility:boolean" 
            layer = QgsVectorLayer(uri, layer_name, 'memory')
            
            if not layer.isValid(): 
                return None

            QgsProject.instance().addMapLayer(layer)
            photo_layer = layer # Set layer before applying style
        
        # Apply mandatory styles regardless of whether it's new or loaded
        if photo_layer:
            self.symbol_renderer.update_layer_symbol_manually(photo_layer, iface)
            self.symbol_renderer.apply_transparent_selection_symbol(photo_layer, iface) 
            
            # --- NEW: Ensure the PhotoListManager has the current layer ---
            if photo_list_manager:
                photo_list_manager.setLayer(photo_layer)
                
        return photo_layer

    def add_point_to_map(self, layer, lat, lon, photo_path, direction_angle=None, is_visible=True, group_name='', label_text='', photo_time='', svg_icon_filename=None):
        """Adds a feature to the photo layer."""
        
        if not layer or not layer.isValid(): 
            return None

        if not layer.isEditable(): 
            layer.startEditing()
        
        point = QgsPointXY(lon, lat)
        
        if layer.crs().authid() != 'EPSG:4326':
            input_crs = QgsCoordinateReferenceSystem('EPSG:4326')
            transform = QgsCoordinateTransform(input_crs, layer.crs(), QgsProject.instance())
            point = transform.transform(point)

        feature = QgsFeature(layer.fields())
        feature.setGeometry(QgsGeometry.fromPointXY(point))
        
        # Default base icon: 0.svg (rotation handled by direction field)
        base_icon_name = svg_icon_filename if svg_icon_filename else '0.svg'
        
        if layer.fields().indexOf('path') >= 0:
            feature.setAttribute('path', photo_path)
        if layer.fields().indexOf('latitude') >= 0:
            feature.setAttribute('latitude', lat)
        if layer.fields().indexOf('longitude') >= 0:
            feature.setAttribute('longitude', lon)
        if layer.fields().indexOf('direction') >= 0: 
            feature.setAttribute('direction', direction_angle)
        if layer.fields().indexOf('svg_icon') >= 0: 
            # Use provided svg_icon_filename for visible photos, else 0.svg
            feature.setAttribute('svg_icon', base_icon_name) 
        if layer.fields().indexOf('svg_icon_backup') >= 0:
            # Initialize backup to the same base icon
            feature.setAttribute('svg_icon_backup', base_icon_name)
        if layer.fields().indexOf('visible') >= 0:
            feature.setAttribute('visible', is_visible)
        if layer.fields().indexOf('group') >= 0:
            feature.setAttribute('group', group_name)
        if layer.fields().indexOf('label_text') >= 0:
            # Use provided label_text, or default to filename if empty
            feature.setAttribute('label_text', label_text if label_text else os.path.basename(photo_path))
        if layer.fields().indexOf('label_visible') >= 0:
            feature.setAttribute('label_visible', True)  # Default to visible
        if layer.fields().indexOf('label_offset_x') >= 0:
            feature.setAttribute('label_offset_x', 0.0)
        if layer.fields().indexOf('label_offset_y') >= 0:
            feature.setAttribute('label_offset_y', 0.0)
        if layer.fields().indexOf('photo_time') >= 0:
            feature.setAttribute('photo_time', photo_time)
        if layer.fields().indexOf('filterVisibility') >= 0:
            feature.setAttribute('filterVisibility', True)  # Default: filter not active, show all photos
        
        layer.addFeature(feature)
        
        feat_id = feature.id()
        svg_icon_idx = layer.fields().indexOf('svg_icon')
        
        if svg_icon_idx >= 0 and feat_id > 0:
            # Update the svg_icon field with the unique ID prefix + base SVG name
            new_unique_icon = f"{feat_id}-{base_icon_name}"
            # This is necessary because the feature ID is only available after addFeature()
            layer.changeAttributeValue(feat_id, svg_icon_idx, new_unique_icon)
            # Also set the backup field if available
            svg_icon_backup_idx = layer.fields().indexOf('svg_icon_backup')
            if svg_icon_backup_idx >= 0:
                layer.changeAttributeValue(feat_id, svg_icon_backup_idx, new_unique_icon)
        
        # Note: Caller is responsible for committing changes (batch commit after all features added)

        return feature 

    def update_feature_metadata(self, iface, photo_layer, feat_id, new_lon, new_lat, new_direction):
        """
        Updates feature metadata (coordinates and direction) in the layer.
        """
        if not photo_layer or not photo_layer.isValid():
            iface.messageBar().pushMessage(
                "Error", 
                "Photo layer not found or invalid. Cannot update metadata.", 
                level=Qgis.Critical
            )
            return False
            
        if not photo_layer.isEditable():
            try:
                photo_layer.startEditing()
            except Exception as e:
                 iface.messageBar().pushMessage(
                    "Error", 
                    f"Failed to start editing layer: {e}", 
                    level=Qgis.Critical
                )
                 return False

        try:
            
            # 1. Update Geometry (Coordinates)
            new_point = QgsPointXY(new_lon, new_lat)
            if photo_layer.crs().authid() != 'EPSG:4326':
                 input_crs = QgsCoordinateReferenceSystem('EPSG:4326')
                 transform = QgsCoordinateTransform(input_crs, photo_layer.crs(), QgsProject.instance())
                 new_point = transform.transform(new_point)
            
            if photo_layer.changeGeometry(feat_id, QgsGeometry.fromPointXY(new_point)):
                
                # 2. Update Attributes
                direction_idx = photo_layer.fields().indexOf('direction')
                svg_icon_idx = photo_layer.fields().indexOf('svg_icon')
                lat_idx = photo_layer.fields().indexOf('latitude')
                lon_idx = photo_layer.fields().indexOf('longitude')
                
                if direction_idx >= 0:
                    photo_layer.changeAttributeValue(feat_id, direction_idx, new_direction)
                
                # Update svg_icon based on the new direction value:
                # if direction is now set, switch to the normal camera icon;
                # if direction is cleared (None/NULL), switch to the no-arrow variant.
                if svg_icon_idx >= 0:
                    current_feature = photo_layer.getFeature(feat_id)
                    current_icon_value = current_feature.attribute('svg_icon') if current_feature.isValid() else None
                    if current_icon_value and current_icon_value != 'Invisible.svg':
                        # Ask the renderer to decide the correct icon for this new direction
                        new_icon = self.symbol_renderer._resolve_icon_for_direction(
                            current_icon_value, new_direction
                        )
                        if new_icon and new_icon != current_icon_value:
                            photo_layer.changeAttributeValue(feat_id, svg_icon_idx, new_icon)
                            backup_idx = photo_layer.fields().indexOf('svg_icon_backup')
                            if backup_idx >= 0:
                                photo_layer.changeAttributeValue(feat_id, backup_idx, new_icon)
                            QgsMessageLog.logMessage(
                                f"[META UPDATE] svg_icon updated: {current_icon_value} -> {new_icon} (direction={new_direction})",
                                'Photo Plugin', Qgis.Info
                            )
                        else:
                            QgsMessageLog.logMessage(
                                f"[META UPDATE] Preserving icon {current_icon_value} (direction={new_direction})",
                                'Photo Plugin', Qgis.Info
                            )

                if lat_idx >= 0:
                    photo_layer.changeAttributeValue(feat_id, lat_idx, new_lat)
                if lon_idx >= 0:
                    photo_layer.changeAttributeValue(feat_id, lon_idx, new_lon)
                
                photo_layer.commitChanges()
                photo_layer.startEditing() 
                
                iface.messageBar().pushMessage(
                    "Update Success", 
                    f"Feature ID {feat_id} metadata updated.", 
                    level=Qgis.Success, 
                    duration=3
                )
                self.symbol_renderer.update_layer_symbol_manually(photo_layer, iface) 
                photo_layer.triggerRepaint()
                iface.mapCanvas().refresh()
                return True
                
            else:
                 iface.messageBar().pushMessage(
                    "Error", 
                    f"Failed to change geometry for Feature ID {feat_id}.", 
                    level=Qgis.Critical
                )
                 return False
                
        except Exception as e:
            if photo_layer.isEditable():
                photo_layer.rollBack()
                photo_layer.startEditing()
            
            iface.messageBar().pushMessage(
                "Error", 
                f"Failed to update metadata for Feature ID {feat_id}: {e}", 
                level=Qgis.Critical
            )
            return False

    def zoom_to_100m_area(self, iface, lat, lon):
        """Zooms the map to a 100m x 100m area centered at the given coordinates."""
        map_canvas = iface.mapCanvas()
        canvas_crs = map_canvas.mapSettings().destinationCrs()
        source_crs = QgsCoordinateReferenceSystem('EPSG:4326')
        
        transform = QgsCoordinateTransform(source_crs, canvas_crs, QgsProject.instance())
        center_point_canvas = transform.transform(QgsPointXY(lon, lat))
        
        HALF_SIDE = 50 
        
        new_extent = QgsRectangle(
            center_point_canvas.x() - HALF_SIDE,
            center_point_canvas.y() - HALF_SIDE,
            center_point_canvas.x() + HALF_SIDE,
            center_point_canvas.y() + HALF_SIDE
        )

        map_canvas.setExtent(new_extent)
        map_canvas.refresh()

    def get_expanded_extent_for_zoom(self, iface, photo_layer, current_extent):
        """Expands an extent to ensure a minimum zoom size."""
        map_canvas = iface.mapCanvas()
        canvas_crs = map_canvas.mapSettings().destinationCrs()
        
        if current_extent.isEmpty():
            return None 

        layer_crs = photo_layer.crs()
        transform = QgsCoordinateTransform(layer_crs, canvas_crs, QgsProject.instance())

        geom = QgsGeometry.fromRect(current_extent)
        geom.transform(transform)
        
        canvas_extent = geom.boundingBox()

        min_dim = 100 
        
        if canvas_crs.isGeographic():
            # A rough minimum dimension in degrees for a small area
            min_dim = 0.0009 
        
        width = canvas_extent.width()
        height = canvas_extent.height()

        x_pad = 0
        if width < min_dim:
            x_pad = (min_dim - width) / 2.0
            
        y_pad = 0
        if height < min_dim:
            y_pad = (min_dim - height) / 2.0

        expanded_extent = QgsRectangle(
            canvas_extent.xMinimum() - x_pad,
            canvas_extent.yMinimum() - y_pad,
            canvas_extent.xMaximum() + x_pad,
            canvas_extent.yMaximum() + y_pad
        )
        
        return expanded_extent
