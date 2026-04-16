# -*- coding: utf-8 -*-
# Copyright (C) 2026 Majid Jazebi
# Web: Geotechzone.com
# All rights reserved.
# This plugin is licensed under GNU GPL v3.
"""
EXIF Data Processing
 
Handles reading EXIF data from photos and extracting GPS coordinates and direction.
"""

from .dependency_manager import safe_import

exifread = safe_import("exifread")
EXIFREAD_AVAILABLE = exifread is not None

from qgis.core import QgsMessageLog, Qgis


class ExifHandler:
    """Handles EXIF data extraction from photo files."""

    @staticmethod
    def is_available():
        """Check if the exifread library is available."""
        return EXIFREAD_AVAILABLE

    def get_exif_gps_value(self, tags, key):
        """Extract GPS value from EXIF tags and convert DMS to decimal degrees."""
        if key not in tags: 
            return None
        
        def to_float(ratio):
            if EXIFREAD_AVAILABLE and isinstance(ratio, exifread.utils.Ratio):
                return float(ratio.num) / float(ratio.den)
            return float(ratio)

        dms_tag_value = tags[key].values
        
        try:
            degrees = to_float(dms_tag_value[0])
            minutes = to_float(dms_tag_value[1])
            seconds = to_float(dms_tag_value[2])
            
            decimal_degrees = degrees + (minutes / 60.0) + (seconds / 3600.0)
            return decimal_degrees
        except Exception as e:
            QgsMessageLog.logMessage(f"Conversion ERROR for {key}: {e}", 'Photo Plugin', Qgis.Critical)
            return None
    
    def extract_gps_and_direction(self, filepath):
        """
        Reads EXIF data from a photo file and extracts GPS coordinates, direction, and capture time.
        
        Returns a dictionary with keys: 'latitude', 'longitude', 'direction', 'photo_time' (or None for any missing).
        """
        if not EXIFREAD_AVAILABLE:
            QgsMessageLog.logMessage("exifread library is not installed. Cannot extract EXIF data.", 'Photo Plugin', Qgis.Critical)
            return {'latitude': None, 'longitude': None, 'direction': None, 'photo_time': None}
        try:
            with open(filepath, 'rb') as f:
                tags = exifread.process_file(f)
            
            LAT_KEY = 'GPS GPSLatitude'
            LON_KEY = 'GPS GPSLongitude'
            LAT_REF_KEY = 'GPS GPSLatitudeRef'
            LON_REF_KEY = 'GPS GPSLongitudeRef'
            DIRECTION_KEY = 'GPS GPSImgDirection' 
            DATETIME_KEY = 'EXIF DateTimeOriginal'  # Primary datetime field
            DATETIME_ALT_KEY = 'Image DateTime'  # Alternative datetime field

            lat = self.get_exif_gps_value(tags, LAT_KEY)
            lon = self.get_exif_gps_value(tags, LON_KEY)

            lat_ref_tag = tags.get(LAT_REF_KEY)
            lon_ref_tag = tags.get(LON_REF_KEY)
            
            direction_angle = None
            direction_tag = tags.get(DIRECTION_KEY)

            if direction_tag:
                 if EXIFREAD_AVAILABLE and isinstance(direction_tag.values[0], exifread.utils.Ratio):
                      value = direction_tag.values[0] if isinstance(direction_tag.values, list) else direction_tag.values
                      direction_angle = float(value.num) / float(value.den)
                 else:
                      direction_angle = float(direction_tag.values[0])
            
            # Extract photo capture time
            photo_time = None
            datetime_tag = tags.get(DATETIME_KEY) or tags.get(DATETIME_ALT_KEY)
            if datetime_tag:
                try:
                    # EXIF datetime format is typically "YYYY:MM:DD HH:MM:SS"
                    photo_time = str(datetime_tag.values)
                except Exception as e:
                    QgsMessageLog.logMessage(f"Error parsing datetime for {filepath}: {e}", 'Photo Plugin', Qgis.Warning)
            
            if lat is not None and lat_ref_tag and lat_ref_tag.printable == 'S':
                 lat *= -1
            if lon is not None and lon_ref_tag and lon_ref_tag.printable == 'W':
                 lon *= -1
            
            return {
                'latitude': lat,
                'longitude': lon,
                'direction': direction_angle,
                'photo_time': photo_time
            }

        except Exception as e:
            QgsMessageLog.logMessage(f"Error reading EXIF from {filepath}: {e}", 'Photo Plugin', Qgis.Critical)
            return {
                'latitude': None,
                'longitude': None,
                'direction': None,
                'photo_time': None
            }
