send_chunk <- function(data) {
    msg <- toJSON(list(type = "chunk", data = data), auto_unbox = TRUE)
    cat(msg, "\n", file = .out, sep = "")
    flush(.out)
}

send_expression <- function(expr) {
    msg <- toJSON(list(type = "expression", data = expr), auto_unbox = TRUE)
    cat(msg, "\n", file = .out, sep = "")
    flush(.out) 
}

send_done <- function(error = NULL) {
    msg <- toJSON(
        list(type = "done", error = error, wd = getwd()),
        auto_unbox = TRUE,
        null = "null"
    )
    cat(msg, "\n", file = .out, sep = "")
    flush(.out)
}

send_fns <- function(pkgs) {
    msg <- toJSON(list(type = "pkg", data = pkgs), auto_unbox = TRUE)
    cat(msg, "\n", file = .out, sep = "")
    flush(.out)
}

check_new_pkgs <- function(before) {
    new_pkgs <- setdiff(search(), before)
    pkgs <- gsub("^package:", "", new_pkgs[startsWith(new_pkgs, "package:")])

    if (length(pkgs) > 0) {
        sigs <- unlist(lapply(pkgs, \(pkg) tryCatch(get_signatures(pkg), error = \(e) character(0L))))
        if (length(sigs) > 0) .fns <<- sigs
    }
}

inject_flush <- function(expr) {
    if (!is.call(expr)) return(expr)

    flush_call <- quote(flush_console())
    name <- expr[[1]]

    args <- lapply(as.list(expr[-1]), inject_flush)
    expr <- as.call(c(list(name), args))

    is_loop <- identical(name, as.name("for")) ||
            identical(name, as.name("while")) ||
            identical(name, as.name("repeat"))

    if (is_loop) {
        body_idx <- length(expr)
        body <- expr[[body_idx]]

        if (is.call(body) && identical(body[[1]], as.name("{"))) {
            stmts <- as.list(body[-1])
            new_stmts <- unlist(
                lapply(stmts, function(s) list(s, flush_call)),
                recursive = FALSE
            )
            expr[[body_idx]] <- as.call(c(list(as.name("{")), new_stmts))
        } else {
            expr[[body_idx]] <- call("{", body, flush_call)
        }
    }

    return(expr)
}