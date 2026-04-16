# Advanced Photo Importer

> A powerful QGIS plugin for importing, managing, and visualizing geotagged photos with EXIF data.

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![QGIS](https://img.shields.io/badge/QGIS-%3E%3D3.28-green.svg)](https://qgis.org)
[![Python](https://img.shields.io/badge/Python-3.x-blue.svg)](https://python.org)
[![GitHub Issues](https://img.shields.io/github/issues/majidjazebi/advanced-photo-importer)](https://github.com/majidjazebi/advanced-photo-importer/issues)

| | |
|---|---|
| **Author** | Dr. Majid Jazebi |
| **Website** | [geotechzone.com/qgis/advanced-photo-importer](https://geotechzone.com/qgis/advanced-photo-importer) |
| **Repository** | [github.com/majidjazebi/advanced-photo-importer](https://github.com/majidjazebi/advanced-photo-importer) |
| **License** | GNU GPL v3 |
| **QGIS Minimum** | 3.28 |

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Dependencies](#dependencies)
- [Usage](#usage)
- [Supported Formats](#supported-formats)
- [Known Limitations](#known-limitations)
- [License](#license)
- [Contact & Support](#contact--support)
- [Changelog](#changelog)

---

## Overview

Advanced Photo Importer simplifies the integration of geotagged photos into your QGIS projects. It automatically extracts GPS coordinates, direction, and timestamp from EXIF metadata, creates point layers, and provides intuitive tools for managing, filtering, labeling, and visualizing field photos directly on the map.

---

## Features

| Category | Capability |
|---|---|
| 📂 **Import** | Single file or entire folder — with recursive subfolder support |
| 🔍 **EXIF Extraction** | GPS latitude/longitude, bearing/direction, and capture timestamp |
| 🗺️ **Layer Creation** | In-memory, GeoPackage (`.gpkg`), or Shapefile (`.shp`) |
| 📸 **Camera Markers** | Customizable SVG icons with rotation based on photo direction |
| 📏 **Marker Size** | Scale from 10% to 500% |
| 📅 **Date/Time Filter** | Independent range filtering separate from manual visibility |
| 👁️ **Visibility Toggle** | Show or hide individual photos |
| 🏷️ **Label Styling** | Font, size, bold, color, buffer/outline, and offset controls |
| 🖱️ **Map Click Tool** | Click a point on the canvas to open the corresponding photo |
| ✏️ **Photo Edit Dialog** | Edit coordinates, direction, and label for any photo |
| 📊 **Excel Export/Import** | Save and reload all photo metadata via `.xlsx` files |
| 📁 **Group Management** | Organize photos into named groups |

---

## Installation

### From QGIS Plugin Repository *(Recommended)*

1. Open QGIS
2. Go to **Plugins → Manage and Install Plugins...**
3. Search for **Advanced Photo Importer**
4. Click **Install Plugin**

### Manual Installation

1. Download the latest release `.zip` from [GitHub Releases](https://github.com/majidjazebi/advanced-photo-importer/releases)
2. In QGIS, go to **Plugins → Manage and Install Plugins → Install from ZIP**
3. Select the downloaded `.zip` file and click **Install Plugin**

> **Note:** If you downloaded the zip directly from GitHub, the extracted folder may be named `advanced-photo-importer-main`. QGIS requires the plugin folder to be named exactly `advanced_photo_importer`. Rename it before placing it in your QGIS plugins directory.

---

## Dependencies

📦 **No External Installation Required**

This plugin ships with all necessary Python libraries bundled inside:

| Library | Purpose |
|---|---|
| [`exifread`](https://pypi.org/project/exifread/) | Read EXIF metadata from JPEG photos |
| [`openpyxl`](https://pypi.org/project/openpyxl/) | Excel import/export functionality |

Everything works out of the box — no need to open a terminal, OSGeo4W Shell, or run `pip install`.

> **Note:** If a system-installed version of a library is already available, the plugin will prefer it automatically. The bundled copy is only used as a fallback.

---

## Usage

### Basic Workflow

```
Open Plugin → Upload Tab → Browse Photos → Upload Photos → View on Map
```

1. **Open the plugin** via the toolbar button or **Plugins → Advanced Photo Importer**
2. **Upload tab** — choose a save location for the layer, then browse to a photo file or folder
3. Click **Upload Photos** — the plugin extracts EXIF data and places point markers on the map
4. **Imported Photos tab** — view the list, toggle visibility, and preview photos
5. **Filter tab** — set a date/time range to show only photos within that period
6. **Settings tab** — adjust marker size, icon style, direction display, and label appearance
7. Use the **See Photo** toolbar button to click directly on map points to open photos

### Excel Workflow

1. Click **Export Package** in the Upload tab — saves all photo metadata to an `.xlsx` file
2. Edit the Excel file externally (visibility, labels, coordinates, etc.)
3. Re-import using **Import from Excel** to apply changes back to the layer

---

## Supported Formats

| Type | Format |
|---|---|
| Photo input | JPEG / JPG *(must contain GPS EXIF data)* |
| Layer output | GeoPackage (`.gpkg`), Shapefile (`.shp`), in-memory |
| Excel export/import | `.xlsx` |

---

## Known Limitations

- Only JPEG photos with embedded GPS EXIF data are supported
- Large batches (1000+ photos) are processed on the main thread — performance may vary
- Photos without GPS EXIF data are skipped automatically

---

## License

This plugin is free software; you can redistribute it and/or modify it under the terms of the **GNU General Public License version 3** as published by the Free Software Foundation.

See the [LICENSE](LICENSE) file for the full license text.

---

## Contact & Support

| Channel | Link |
|---|---|
| 🐛 Bug Reports & Issues | [GitHub Issues](https://github.com/majidjazebi/advanced-photo-importer/issues) |
| 🌐 Website & Documentation | [geotechzone.com](https://geotechzone.com/qgis/advanced-photo-importer) |
| 💼 LinkedIn | [linkedin.com/in/majidjazebi](https://www.linkedin.com/in/majidjazebi/) |

---

## 📜 Credits / Icons

Full details regarding third-party assets and icon attributions can be found in the [CREDITS.md](CREDITS.md) file.

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.
