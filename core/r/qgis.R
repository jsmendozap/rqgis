#' @title Interface to the QGIS Project
#'
#' @description
#' The `QgisProject` class provides an R6 interface to interact with the
#' currently active QGIS project. It allows reading project properties, listing
#' layers, and transferring spatial data between R and QGIS.
#'
#' @details
#' An instance of this class, named `qgis`, is automatically created and made
#' available in the R console's global environment when the plugin is loaded.
#' This object serves as the main entry point for all interactions with QGIS.
#'
#' @field title (character) The title of the QGIS project (read-only).
#' @field path (character) The absolute path to the QGIS project file (read-only).
#' @field crs (character) The authority ID of the project's CRS (e.g., "EPSG:4326") (read-only).
#' @field units (character) The map units of the project (e.g., "meters") (read-only).
#'
#' @export
QgisProject <- R6Class("QgisProject",
                        private = list(
                          .title = NULL,
                          .path = NULL,
                          .crs = NULL,
                          .units = NULL,
                          .pkgs_loaded = FALSE, 

                          .ensure_pkgs = function() {

                            pkgs <- c("sf", "terra")
                            missing <- pkgs[!sapply(pkgs, requireNamespace, quietly = TRUE)]

                            if (length(missing) > 0) { 
                              if (length(missing) == 1) {
                                stop(paste0(missing, " package is required but is not installed"), call. = FALSE)
                              } else {
                                stop(paste0(paste0(missing, collapse = ", "), " packages are required but are not installed"), call. = FALSE)
                              }
                            }

                            if (!private$.pkgs_loaded) {
                              suppressPackageStartupMessages(library(sf, quietly = TRUE))
                              suppressPackageStartupMessages(library(terra,  quietly = TRUE))
                              private$.pkgs_loaded <- TRUE
                            }
                          }, 

                          .send_request = function(method, args = NULL) {
                            msg <- toJSON(
                                list(type = "request", method = method, args = args),
                                auto_unbox = TRUE,
                                null = "null"
                            )

                            cat(msg, "\n", file = .out, sep = "")
                            flush(.out)
                            
                            fromJSON(readLines("stdin", n = 1, warn = FALSE))
                          }, 

                          .is_id = function(x) {
                            grepl("_[a-f0-9]{8}_[a-f0-9]{4}_[a-f0-9]{4}_[a-f0-9]{4}_[a-f0-9]{12}$", x)
                          }
                        ),
                        
                        active = list(
                          title = function(value) {
                            if (missing(value)) return(private$.title)
                            stop("Title property is read only", call. = FALSE)
                          }, 
                          path = function(value) {
                            if (missing(value)) return(private$.path)
                            stop("Path property is read only", call. = FALSE)
                          },
                          crs = function(value) {
                            if (missing(value)) return(private$.crs)
                            stop("CRS property is read only", call. = FALSE)
                          },
                          units = function(value) {
                            if (missing(value)) return(private$.units)
                            stop("Units property is read only", call. = FALSE)
                          }
                        ),
                        
                        public = list(
                          #' @description
                          #' Create a new `QgisProject` object.
                          #' This is typically instantiated via qgis_project().
                          #' @param data A list containing the initial project state.
                          #' If `NULL`, it will be requested from QGIS. For internal use.
                          #' @return A new `QgisProject` object.
                          initialize = function(data = NULL){
                            private$.ensure_pkgs()
                            if (is.null(data)) {
                              data <- private$.send_request("project_state")
                            }
                            private$.title <- ifelse(data$title == "", "Untitled", data$title)
                            private$.path <- ifelse(data$path == "", "Unsaved project", data$path)
                            private$.crs <- data$crs
                            private$.units <- data$units
                            invisible(self)
                          },
                          
                          #' @description
                          #' Lists layers available in the current QGIS project.
                          #' @param type (integer) An optional filter for layer type.
                          #' Corresponds to `QgsMapLayerType`: `0` for vector, `1` for raster.
                          #' Use `NULL` to list all layers.
                          #' @return A data frame with the `name` and `id` of the layers.
                          list_layers = function(type = NULL) {
                            # QgsMapLayerType enum in QGIS API goes from 0 to 9
                            # 0: Vector, 1: Raster, 2: Plugin, 3: Mesh, 4: VectorTile,
                            # 5: Annotation, 9: Unknown
                            if (!is.null(type) && !(is.numeric(type) && type %in% 0:9)){
                                stop("type argument must be an integer between 0 and 9 or NULL", call. = FALSE)
                              }

                            response <- private$.send_request("list_layers", list(type = type))
                            return(response$layers)
                          },

                          #' @description
                          #' Reads a QGIS layer and loads it into R as a spatial object.
                          #' @param x (character) The name or ID of the layer to get.
                          #' @param ... Additional arguments passed to `sf::st_read()` for vector
                          #' layers.
                          #' @return An `sf` object for vector layers or a `SpatRaster` object
                          #' from the `terra` package for raster layers.
                          get_layer = function(x, ...) {
                            
                            if (!is.character(x) || length(x) != 1) {
                              stop("x argument must be a character of length 1", call. = FALSE)
                            }
                            
                            column <- if (private$.is_id(x)) "id" else "name"
                            response <- private$.send_request("get_layer", list(col = column, value = x))
                            
                            if (!is.null(response$error)) stop(response$error, call. = FALSE)
                            
                            if (tools::file_ext(response$path) == "fgb"){
                              layer <- st_read(response$path, quiet = TRUE, ...)
                            } else {
                              layer <- rast(response$path)
                            }

                            return(layer)
                          },

                          #' @description
                          #' Inserts an R spatial object into the QGIS project as a new layer.
                          #' @param layer The spatial object to insert. Must be an `sf` object or
                          #' a `SpatRaster` from the `terra` package.
                          #' @param name (character) The desired name for the new layer in QGIS.
                          #' If `NULL`, a name will be generated from the object's variable name.
                          #' @param ... Additional arguments passed to `sf::st_write()` for vector
                          #' layers.
                          #' @return The `QgisProject` object, invisibly.
                          insert_layer = function(layer, name = NULL, ...) {
                            if (!inherits(layer, "sf") && !inherits(layer, "SpatRaster")) {
                              stop("Object not supported", call. = FALSE)
                            }

                            ext <- if (inherits(layer, "sf")) ".fgb" else ".tif"
                            path <- tempfile(fileext = ext)

                            if (inherits(layer, "sf")) {
                              st_write(layer, path, quiet = TRUE, ...)
                            } else {
                              writeRaster(layer, path)
                            }

                            response <- private$.send_request("insert_layer", list(path = path, name = name))
                            
                            cat("Layer inserted with id: ", response$id, "\n")
                            invisible(self)
                          },
                          
                          #' @description
                          #' Prints detailed information about a specific layer.
                          #' @param x (character) The name or ID of the layer.
                          #' @return The `QgisProject` object, invisibly.
                          layer_info = function(x){
                            if (!is.character(x) || length(x) != 1) {
                              stop("x must be a character of length 1", call. = FALSE)
                            }

                            column <- if (private$.is_id(x)) "id" else "name"
                            response <- private$.send_request("layer_info", list(column = column, value = x))

                            if (!is.null(response$error)) stop(response$error, call. = FALSE)
                                                    
                            cat(paste0("<Layer: ", response$name, ">"), "\n")
                            cat("@ Type:", response$layer_type, "\n")
                            cat("@ CRS: ", response$crs, "\n")
                            cat("@ Extent:", "\n",
                                "   xmin =", response$extent$xmin, "\n",
                                "   xmax =", response$extent$xmax, "\n",
                                "   ymin =", response$extent$ymin, "\n",
                                "   ymax =", response$extent$ymax, "\n")
                            
                            if (response$layer_type == "vector") {
                                cat("@ Geometry:", response$geometry, "\n")
                                cat("@ Features:", response$features, "\n")
                                cat("@ Fields:\n")
                                cat("   ", paste(response$fields, collapse = "\n    "))
                            } else {
                                cat("@ Bands:      ", response$bands, "\n")
                                cat("@ Dimensions: ", response$width, "x", response$height, "\n")
                                cat("@ Resolution:", response$res_x, "x", response$res_y, response$units, "\n")
                            }
                            
                            invisible(self)
                          },

                          #' @description
                          #' Gets the extent of the current map canvas.
                          #' @return A `bbox` object from the `sf` package representing the
                          #' current view extent.
                          get_canvas_extent = function() {
                            response <- private$.send_request("canvas_extent")
                            extent <- st_as_sfc(response$wkt, crs = response$crs, class = "WKT")
                            return(st_bbox(extent))
                          },

                          #' @description
                          #' Gets the selected features from the currently active vector layer in QGIS.
                          #' @return An `sf` object containing the selected features.
                          #' Returns an error if the active layer is not a vector layer or has no
                          #' selection.
                          get_selected_features = function() {
                            response <- private$.send_request("selected_features")
                            if (!is.null(response$error)) stop(response$error, call. = FALSE)
                            layer <- st_read(response$path, quiet = TRUE)
                            return(layer)
                          },
                          
                          #' @description
                          #' Prints a summary of the QGIS project information.
                          #' @param ... Ignored.
                          print = function(...) {
                            cat("<QGIS Project Object>\n")
                            cat("@ Title:", private$.title, "\n")
                            cat("@ Path:", private$.path, "\n")
                            cat("@ CRS:", private$.crs, "\n")
                            cat("@ Map units:", private$.units, "\n")
                            invisible(self)
                          }
                        )
  )