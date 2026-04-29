#' Connect to the Active QGIS Project
#'
#' @description
#' Establishes a connection to the currently active QGIS project. This function 
#' is the main entry point for the \code{rqgis} package, returning an R6 object 
#' that allows you to interact with QGIS layers, extent, and project metadata directly 
#' from the R console.
#' 
#' @param data Optional list containing updates about the project state. Intended for internal plugin use only.
#' 
#' @return An R6 object of class \code{\link{QgisProject}} containing the project's metadata 
#' and methods for bidirectional data transfer.
#' 
#' @examples
#' \dontrun{
#' # Connect to the active QGIS project
#' qgis <- qgis_project()
#' 
#' # Inspect project properties
#' qgis$title
#' qgis$crs
#' 
#' # List available layers and retrieve one as an sf object
#' qgis$list_layers()
#' my_layer <- qgis$get_layer("world_borders")
#' }
#' 
#' @export

qgis_project <- function(data = NULL) {
  QgisProject$new(data)
}