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
                              invisible(library(sf))
                              invisible(library(terra))
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
                          initialize = function(data = NULL){
                            if (is.null(data)) {
                              data <- private$.send_request("project_state")
                            }
                            private$.title <- ifelse(data$title == "", "Untitled", data$title)
                            private$.path <- ifelse(data$path == "", "Unsaved project", data$path)
                            private$.crs <- data$crs
                            private$.units <- data$units
                            invisible(self)
                          },
                          
                          list_layers = function(type = NULL) {
                            if (!is.null(type) && !type %in% 0:9){
                                stop("type argument must be an integer between 0 and 9 or NULL", call. = FALSE)
                              }

                            response <- private$.send_request("list_layers", list(type = type))
                            return(response$layers)
                          },

                          get_layer = function(x, ...) {
                            
                            if (!is.character(x) || length(x) != 1) {
                              stop("x argument must be a character of length 1", call. = FALSE)
                            }
                            
                            column <- if (private$.is_id(x)) "id" else "name"
                            response <- private$.send_request("get_layer", list(column = column, value = x))
                            
                            if (!is.null(response$error)) stop(response$error, call. = FALSE)

                            private$.ensure_pkgs()
                            
                            if (tools::file_ext(response$path) == "fgb"){
                              layer <- st_read(response$path, quiet = TRUE, ...)
                            } else {
                              layer <- rast(response$path)
                            }
                          },

                          insert_layer = function(layer, name = NULL, ...) {
                            if (!inherits(layer, "sf") && !inherits(layer, "SpatRaster")) {
                              stop("Object not supported", call. = FALSE)
                            }

                            ext <- if (inherits(layer, "sf")) ".fgb" else ".tif"
                            path <- tempfile(fileext = ext)

                            private$.ensure_pkgs()

                            if (inherits(layer, "sf")) {
                              st_write(layer, path, quiet = TRUE, ...)
                            } else {
                              writeRaster(layer, path)
                            }

                            response <- private$.send_request("insert_layer", list(path = path, name = name))
                            
                            cat("Layer inserted with id: ", response$id, "\n")
                            invisible(self)
                          },
                          
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

                          print = function(...) {
                            cat("<QGIS Project Object>\n")
                            cat("@ Title:", private$.title, "\n")
                            cat("@ Path: ", private$.path, "\n")
                            cat("@ CRS:  ", private$.crs, "\n")
                            cat("@ Map units:", private$.units, "\n")
                            invisible(self)
                          }
                        )
  )