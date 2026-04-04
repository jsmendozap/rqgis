send_message <- function(type, data) {
    msg <- toJSON(list(type = type, data = data), auto_unbox = TRUE, null = "null")
    cat(msg, "\n", file = .out, sep = "")
    flush(.out)
}

send_chunk <- function(data) send_message("chunk", data)
send_expression <- function(expr) send_message("expression", expr)
send_fns <- function(pkgs) send_message("pkg", pkgs)

send_done <- function(error = NULL) {
    msg <- toJSON(
        list(type = "done", error = error, wd = getwd()),
        auto_unbox = TRUE,
        null = "null"
    )
    cat(msg, "\n", file = .out, sep = "")
    flush(.out)
}

send_help <- function(url) {
    path <- tempfile(fileext = ".html")
    tools::Rd2HTML(utils:::.getHelpFile(url), out = path)
    msg <- toJSON(list(type = "help", path = path), auto_unbox = TRUE)
    cat(msg, "\n", file = .out, sep = "")
    flush(.out)
}

send_question <- function(method, args = NULL) {
    msg <- toJSON(
        list(type = "question", method = method, args = args),
        auto_unbox = TRUE,
        null = "null"
    )
    cat(msg, "\n", file = .out, sep = "")
    flush(.out)

    response <- fromJSON(readLines("stdin", n = 1, warn = FALSE))
    return(response)
}