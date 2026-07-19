# Changelog

## 0.5

- Added PTY-backed interactive support for Unix/macOS and Windows.
- Windows can use `pywinpty` (imported as `winpty`) for a true terminal session.
- Added a pipes fallback when `pywinpty` is not available.
- Improved interrupt handling so Ctrl+C stops the running evaluation cleanly.
- Hardened startup handling and PTY log filtering.
- The configured R path now points directly to the R executable, especially `R.exe` on Windows.
- The plugin is now released as a normal plugin instead of experimental.

## 0.4.1

- Added PTY-backed interactive support for Unix/macOS and Windows.
- Windows can use `pywinpty` (imported as `winpty`) for a true terminal session.
- Added a pipes fallback when `pywinpty` is not available.
- Improved interrupt handling so Ctrl+C stops the running evaluation cleanly.
- Hardened startup handling and PTY log filtering.

## 0.4.0

- Support for QGIS 4.
- Introduced the `rqgis` package to wrap the public API for QGIS interaction from R.
- Added `qgis_draw_bbox` and `qgis_draw_points` functions.
- Automatic configuration of `qgis_process` path during `qgisprocess` package load.
- Dedicated API documentation website published via pkgdown.
- Implemented a log viewer in the settings panel.
- Added an option in settings to display the plugin title in the main panel.
- Bug fixes.
