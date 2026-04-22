# Changelog

All notable changes to **Advanced Photo Importer** will be documented in this file.

---

## [1.0.1] - 2026-04-22

### Changed
- Reworked import/export UX with a single integrated progress window (percentage + processed count) (Thanks @billjwilliamson).
- Moved final completion messages into the same progress window (`Done` state), removing duplicate success popups.
- Added live skipped-file tracking during folder import with copyable output in the progress window.
- Improved imported photo list readability with aligned column headers (`Visibility`, `File Name`, `Label`) and corrected row alignment.
- Added a styled destructive `Delete Selected Photo` action in the Imported Photos panel.

### Security
- Hardened XML parsing in bundled EXIF processing code by switching to `defusedxml` for safer XML parsing.
- Removed flagged executable/script artifacts from the plugin package to reduce security scanner noise.
- Reduced low-severity Bandit findings in first-party plugin code by replacing silent exception handling with explicit logging.

### Fixed
- Fixed file hyperlink generation for paths containing spaces in Excel export. (Thanks @billjwilliamson)
- Fixed Qt6 compatibility issues for modal dialogs and frame line enums (`WindowModality`, `QFrame` shape constants).
- Fixed repeated import-cancel flow where disconnecting an unconnected signal raised `TypeError`.

## [1.0.0] - 2026-04-17 — Initial Public Release

### Added
- Import geotagged photos from a single file or an entire folder (with recursive subfolder support)
- Automatic GPS coordinate extraction from EXIF data (latitude, longitude, direction, timestamp)
- Create point layers in-memory or saved as GPKG/Shapefile
- Customizable SVG camera marker symbols with automatic rotation based on photo direction
- Marker size control (10%–500%)
- Date/time range filtering independent of manual visibility control
- Per-photo visibility toggle (manual control separate from filter)
- Label styling: font, size, bold, color, buffer/outline, label offset
- Click-on-map tool (See Photo) to open photos directly from the map canvas
- Photo Edit Dialog for editing coordinates, direction, and label per photo
- Export photo metadata to Excel (.xlsx)
- Import photo metadata from Excel (.xlsx)
- Group management for organizing photo sets
- About tab with plugin info, developer links (LinkedIn, GitHub, website)
- Full GPL v3 licensing
