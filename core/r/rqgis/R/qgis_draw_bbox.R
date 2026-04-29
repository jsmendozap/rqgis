#' Draw a Rectangle on the QGIS Map Canvas
#'
#' @description
#' Interactively prompts the user to draw a rectangle on the QGIS map canvas
#' and returns its bounding box.
#'
#' @return A \code{bbox} object from the \code{sf} package representing the drawn extent.
#'
#' @examples
#' \dontrun{
#' # Draw a bounding box and save the extent to a variable
#' my_bbox <- qgis_draw_bbox()
#' print(my_bbox)
#' }
#'
#' @export

qgis_draw_bbox <- function() {
  request <- getOption("rqgis.send_request")

  response <- request("draw_bbox")
  if (!is.null(response$error)) stop(response$error, call. = FALSE)

  bbox <- sf::st_bbox(c(xmin = response$data$xmin, ymin = response$data$ymin, 
                        xmax = response$data$xmax, ymax = response$data$ymax), 
                      crs = response$data$crs)
  return(bbox)
}
