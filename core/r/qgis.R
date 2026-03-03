local({
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
                        initialize = function(res){
                          private$.title <- ifelse(res$title == "", "Untitled", res$title)
                          private$.path <- ifelse(res$path == "", "Unsaved project", res$path)
                          private$.crs <- res$crs
                          private$.units <- res$units
                          invisible(self)
                        },
                        
                        list_layers = function(type = NULL) {
                          if (!is.null(type) && !type %in% 0:9){
                             stop("type argument must be an integer between 0 and 9 or NULL", call. = FALSE)
                           }

                          msg <- toJSON(list(type = "request", method = "list_layers", args = list(type = type)),
                                        auto_unbox = TRUE, 
                                        null = "null"
                                      )
                          
                          cat(msg, "\n", file = .out, sep = "") 
                          flush(.out)
                          
                          response <- fromJSON(readLines("stdin", n = 1, warn = FALSE))
                          return(response[[2]])
                        },

                        get_layer = function(field, ...) {
                          
                          if (!is.character(field) || length(field) != 1) {
                            stop("field argument must be a character of length 1", call. = FALSE)
                          }
                          
                          is_id <- grepl("_[a-f0-9]{8}_[a-f0-9]{4}_[a-f0-9]{4}_[a-f0-9]{4}_[a-f0-9]{12}$", field)
                          column <- if (is_id) "id" else "name"

                          msg <- toJSON(list(type = "request", method = "get_layer", args = list(col = column, value = field)),
                                        auto_unbox = TRUE, 
                                        null = "null"
                                      )

                          cat(msg, "\n", file = .out, sep = "") 
                          flush(.out)

                          response <- fromJSON(readLines("stdin", n = 1, warn = FALSE))
                          
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

                          msg <- toJSON(list(type = "request", method = "insert_layer", 
                                            args = list(path = path, name = name)),
                                        auto_unbox = TRUE, null = "null")

                          cat(msg, "\n", file = .out, sep = "") 
                          flush(.out)

                          response <- fromJSON(readLines("stdin", n = 1, warn = FALSE))
                          
                          cat("Layer inserted with id: ", response$id, "\n")
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
  QgisProject
})