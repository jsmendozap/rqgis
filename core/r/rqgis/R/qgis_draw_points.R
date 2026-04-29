#' Draw Points on the QGIS Map Canvas
#'
#' @description
#' Interactively prompts the user to draw a specified number of points 
#' on the QGIS map canvas and returns them as an \code{sfc} object.
#'
#' @param n (integer) The number of points to draw. Defaults to 1.
#'
#' @return An \code{sfc} object (geometry column) from the \code{sf} package 
#' containing the drawn points.
#'
#' @examples
#' \dontrun{
#' # Draw a single point
#' pt <- qgis_draw_points()
#' 
#' # Draw 3 points
#' pts <- qgis_draw_points(n = 3)
#' print(pts)
#' }
#'
#' @export
qgis_draw_points <- function(n = 1) {
  request <- getOption("rqgis.send_request")

  n <- as.integer(n)
  if (is.na(n) || n < 1) {
    stop("n must be a positive integer.", call. = FALSE)
  }

  response <- request("draw_points", list(n = n))
  if (!is.null(response$error)) stop(response$error, call. = FALSE)

  coords <- cbind(response$data$points$x, response$data$points$y)
  sfc <- sf::st_sfc(lapply(1:nrow(coords), \(i) sf::st_point(coords[i, ])), crs = response$data$crs)
  
  return(sfc)
}
