# R Console

![Status](https://img.shields.io/badge/Status-Experimental-orange.svg)
![Version](https://img.shields.io/badge/Version-0.3.1-blue.svg)
![QGIS](https://img.shields.io/badge/QGIS-3.30%2B-brightgreen.svg)
![License](https://img.shields.io/badge/License-GPL%20v2-green.svg)

An R console integrated into QGIS. Write and execute R code directly inside QGIS with full access to the active project's layers, CRS, extent, and properties from R. Supports bidirectional interoperability: load vector and raster layers from QGIS into R, and insert R spatial objects back into the project.

> [!WARNING] 
> This project is currently in an early stage of development. While the core functionalities are already implemented and fully functional, there are still several features and improvements pending (please refer to the [Roadmap](#roadmap) below).

![Demo](resources/demo.gif)

## Features

- Interactive R console with command history, plot history, and a graphics panel
- Multi-tab script editor with R syntax highlighting and autocompletion
- UI controls to restart the R session, clear the console, and change the working directory
- Keyboard shortcuts
  - Ctrl / Cmd + Enter: execute current line or selection
  - Ctrl / Cmd + S: save active script
  - Ctrl / Cmd + L (console): clear console
- Bidirectional interoperability between R and QGIS:
  - Read project metadata (title, path, CRS, map units)
  - Load vector and raster layers from QGIS into R as `sf` or `SpatRaster` objects
  - Insert R spatial objects back into the QGIS project
  - Load selected features from the active layer
- Automatic project state synchronization when layers or project properties change
- Get selected features from the active layer
- Configurable R path and initial working directory

## Roadmap

- [x] Support for `plot` command
- [x] Support for `View` command
- [x] Enable functions that require user interaction (e.g. `file.choose`, `menu`, ...)
- [ ] Pseudo-terminal (PTY) emulation for full interactive support
- [ ] Compatibility with QGIS 4
- [ ] Language Server Protocol (LSP) implementation for advanced editor features

## Requirements

- QGIS 3.30 or later (QGIS 4 is not yet supported)
- R 4.1.0 or later 
- R packages: `R6`, `jsonlite`, `evaluate`, `httpgd`, `sf`, `terra`

Install the required R packages before using the plugin:

```r
install.packages(c("R6", "jsonlite", "evaluate", "httpgd", "sf", "terra"))
```

## Installation

The R Console plugin is available in the official QGIS Plugin Repository.

1.  Open QGIS and go to **Plugins → Manage and Install Plugins...**.
2.  Search for **"R Console"** in the `All` tab.
3.  Select **R Console** from the list and click **Install Plugin**.

> [!NOTE]
> This plugin is marked as experimental. If you cannot find it, go to the **Settings** tab in the plugin manager and make sure the **"Show also experimental plugins"** option is checked.

## Usage

The dock widget contains two panels: an interactive console and a script editor.

### Console

Type R expressions and press **Enter** to execute. Use the **Up/Down** arrow keys to navigate command history. 

### Editor

Write R scripts in the editor. Execute the current expression with **Ctrl+Enter**, or run the entire script with the **Run** button. 

### QGIS project access

Connect to the active QGIS project using `qgis_project()`. This creates a `R6` object in your R environment. You can assign it any name:

```r
qgis <- qgis_project()
```

The object is automatically updated when project properties or layers change.

### QgisProject methods

#### Project metadata

```r
qgis$title    # project title
qgis$path     # project file path
qgis$crs      # CRS identifier (e.g. "EPSG:4326")
qgis$units    # map units (e.g. "degrees")
```

#### Interacting with Layers

**List all layers in the project:**

```r
# List all layers
layers_df <- qgis$list_layers()
print(layers_df)

# List only vector layers
vector_layers <- qgis$list_layers(type = 0)
print(vector_layers)
```

**Process data in R and insert it back into QGIS:**

Perform any analysis in R and push the results back to QGIS as a new layer.

```r
library(sf)
library(rnaturalearth)
library(dplyr)

world <- ne_countries() %>% select(name, continent)

# Insert the new layer into QGIS
qgis$insert_layer(world, name = "world")
```

**Get a layer from QGIS into R:**

You can load a layer by its name or its ID. Vector layers are loaded as `sf` objects and rasters as `SpatRaster` objects.

```r
# Load the vector layer back into R
world_new <- qgis$get_layer("world")

# Load a raster layer
dem <- qgis$get_layer("dem_raster")
```

#### Layer information

```r
qgis$layer_info("world")
# Layer: world> 
# @ Type: vector 
# @ CRS:  EPSG:4326 
# @ Extent: 
#     xmin = -180 
#     xmax = 180 
#     ymin = -90 
#     ymax = 83.64513 
# @ Geometry: MultiPolygon 
# @ Features: 177 
# @ Fields:
#     name
#     continent
```

#### Canvas extent

```r
# returns the current map canvas extent as an bbox object
qgis$get_canvas_extent()
```

#### Selected features

```r
# returns selected features from the active layer as an sf object
qgis$get_selected_features()
```

## License

Copyright (C) 2024 Juan Mendoza.

R Console is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 2 of the License, or (at your option) any later version.

R Console is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with R Console. If not, see <https://www.gnu.org/licenses/>.
