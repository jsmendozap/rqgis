local({
  QgisProject <- R6Class("QgisProject",
                      private = list(
                        .title = NULL,
                        .path = NULL,
                        .crs = NULL,
                        .units = NULL,
                        .layers = NULL
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
                        },
                        layers = function(value) {
                          if (missing(value)) return(private$.layers)
                          stop("Layers property is read only", call. = FALSE)
                        }
                      ),
                      
                      public = list(
                        initialize = function(res){
                          private$.title <- ifelse(res$title == "", "Untitled", res$title)
                          private$.path <- ifelse(res$path == "", "Unsaved project", res$path)
                          private$.crs <- res$crs
                          private$.units <- res$units
                          private$.layers <- paste0(res$layers, collapse = ", ")
                          #invisible(self)
                        },
                        
                        list_layers = function(type = NULL) {
                          msg <- toJSON(list(type = "request", method = "list_layers", args = list(type = type)),
                                        auto_unbox = TRUE, 
                                        null = "null"
                                      )
                          
                          cat(msg, "\n", file = .out, sep = "") 
                          flush(.out)
                          
                          response <- fromJSON(readLines("stdin", n = 1, warn = FALSE))
                          return(response[[2]])
                        },

                        project_state = function() {
                          msg <- toJSON(list(type = "request", method = "project_state"),
                                        auto_unbox = TRUE, 
                                        null = "null"
                                      )
                          
                          cat(msg, "\n", file = .out, sep = "") 
                          flush(.out)

                          response <- fromJSON(readLines("stdin", n = 1, warn = FALSE))
                          return(response[-1])
                        },
                        
                        print = function(...) {
                          cat("<QGIS Project Object>\n")
                          cat("@ Title:", private$.title, "\n")
                          cat("@ Path: ", private$.path, "\n")
                          cat("@ Map units:", private$.units, "\n")
                          cat("@ CRS:  ", private$.crs, "\n")
                          cat("@ Layers: ", private$.layers, "\n")
                          invisible(self)
                        }
                      )
  )
  QgisProject
})