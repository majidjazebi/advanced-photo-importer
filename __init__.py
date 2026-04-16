# -*- coding: utf-8 -*-
"""
/***************************************************************************
 AdvancedPhotoImporter
                                 A QGIS plugin
 Import, manage and visualize geotagged photos with EXIF data in QGIS
                             -------------------
        begin                : 2025-11-10
        copyright            : (C) 2026 by Majid Jazebi
        email                : majidjazebi@gmail.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load AdvancedPhotoImporter class from file AdvancedPhotoImporter.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .Advanced_Photo_Importer import AdvancedPhotoImporter
    return AdvancedPhotoImporter(iface)
