local({
    QgisProject <- R6Class("QgisProject",
                       private = list(
                         .title = NULL,
                         .path = NULL,
                         .crs = NULL,
                         .units = NULL
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
                         initialize = function(title = "Untitled", path = "Unsaved project", crs, units){
                           private$.title <- title
                           private$.path <- path
                           private$.crs <- crs
                           private$.units <- units
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
                         
                         print = function(...) {
                           cat("<QGIS Project Object>\n")
                           cat("@ Title:", private$.title, "\n")
                           cat("@ Path: ", private$.path, "\n")
                           cat("@ CRS:  ", private$.crs, "\n")
                           cat("@ Units:", private$.units, "\n")
                           invisible(self)
                         }
                       )
    )
    qgis <- QgisProject$new(crs = "EPSG:4326", units = "degrees")
    assign("qgis", qgis, envir = globalenv())
})