.ask_yes_no <- function(msg = NULL, default = TRUE, ...) {
    response <- send_question("ask_yes_no", list(question = msg, default = default))
    isTRUE(response$data)
}

.menu <- function(choices, graphics = FALSE, title = NULL) {
    response <- send_question("menu", list(choices = choices, title = title))
    return(response$data)
}

.file.choose <- function(new = FALSE) {
    response <- send_question("file_choose", list(new = new))
    if (is.null(response$data) || response$data == "") stop("file choice cancelled")
    return(response$data)
}

.editor <- function(name = NULL, file = "", title = NULL, remove_on_close = FALSE, ...) {
    if (is.null(name) && is.character(file) == "") return(invisible(0L))
    
    if (!is.null(name)){
        file <- tempfile(pattern = deparse(substitute(name)), fileext = ".R")
        remove_on_close <- TRUE
        write_file(name, file)
    }
    
    file <- normalizePath(file, mustWork = FALSE)
    if (is.null(title)) title <- basename(file)
    
    send_question("file_edit", list(file = file, title = title, remove_on_close = isTRUE(remove_on_close)))
    return(invisible(0L))
}

.readline <- function(prompt = "") {
    response <- send_question("readline", list(prompt = prompt))
    if (is.null(response$data)) return("")
    return(as.character(response$data))
}

.View <- function(x, title = NULL, max_rows = 1000) {
    if (missing(title)) title <- deparse(substitute(x))[1]
    
    if (is.data.frame(x) || is.matrix(x)) {

        if (class(x)[1] == "sf") {
            x$geom <- sf::st_geometry_type(x)
            x <- sf::st_drop_geometry(x)
        }

        if (nrow(x) > max_rows) {
            x <- x[1:max_rows, , drop = FALSE]
            title <- paste0(title, " (Showing first ", max_rows, " rows)")
        }
        file <- tempfile(pattern = "View_", fileext = ".csv")
        write.csv(as.data.frame(x), file, row.names = FALSE)
        send_question("show_table", list(file = file, title = title, remove_on_close = TRUE))
        return(invisible(NULL))
    }

    if (is.list(x)) {
        to_jsonable <- function(obj, depth) {
            if (depth <= 0L) return("<max depth>")
            if (is.null(obj) || is.atomic(obj)) return(obj)
            if (is.data.frame(obj)) {
                out <- lapply(obj, function(v) to_jsonable(v, depth - 1L))
                if (!is.null(names(obj))) names(out) <- names(obj)
                return(list(
                    `__r_meta__` = list(
                        type = "data.frame",
                        value = paste(dim(obj), collapse = " x ")
                    ),
                    `__r_children__` = out
                ))
            }
            if (is.list(obj)) {
                out <- lapply(obj, function(v) to_jsonable(v, depth - 1L))
                if (!is.null(names(obj))) names(out) <- names(obj)
                return(out)
            }
            if (is.function(obj)) return("<function>")
            if (is.environment(obj)) return("<environment>")
            if (inherits(obj, "call") || inherits(obj, "formula") || inherits(obj, "language")) {
                return(paste(deparse(obj), collapse = " "))
            }
            return(as.character(obj))
        }

        file <- tempfile(pattern = "View_", fileext = ".json")
        ok <- tryCatch({
            obj <- list(title = x)
            names(obj) <- title
            jsonlite::write_json(
                to_jsonable(obj, depth = 5L),
                file,
                auto_unbox = TRUE,
                null = "null",
                na = "string"
            )
            TRUE
        }, error = function(e) FALSE)

        if (isTRUE(ok)) {
            send_question("show_tree", list(file = file, title = title, remove_on_close = TRUE))
            return(invisible(NULL))
        }
    }
    
    file <- tempfile(pattern = "View_", fileext = ".R")
    sink(file)
    on.exit(sink(), add = TRUE)
    write_file(x, file)
    .editor(file = file, title = title, remove_on_close = TRUE)
}

.patch_fn <- function(name, new_fn, pkg) {
    pkg_env <- paste0("package:", pkg)
    if (pkg_env %in% search()) {
        env <- as.environment(pkg_env)
        unlockBinding(name, env)
        assign(name, new_fn, envir = env)
        lockBinding(name, env)
    }
}

.patch_fn("menu", .menu, "utils")
.patch_fn("file.choose", .file.choose, "base")
.patch_fn("readline", .readline, "base")
.patch_fn("View", .View, "utils")

options(
    repos = c(CRAN = "https://cloud.r-project.org"),
    editor = .editor,
    rlang_interactive = TRUE,
    askYesNo = .ask_yes_no,
    shiny.launch.browser = FALSE,
    device = "httpgd", 
    browser = function(url, ...) {
        html <- paste(readLines(url, warn = FALSE), collapse = "\n")
        send_help(html)
    },
    help_type = "html",
    echo = FALSE, 
    max.print = 100
)
