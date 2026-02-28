options(echo = FALSE)
.out <- stdout()

cat("READY\n")
flush(.out)

pkgs <- c("jsonlite", "evaluate", "agricolae", "abc", "dfasd", "fasdfasd", "afsfdf")
missing <- pkgs[!sapply(pkgs, requireNamespace, quietly = TRUE)]

if (length(missing) > 0) {
    msg <- sprintf('{"type":"missing","data":"%s"}\n', paste0(missing, collapse = ", "))
    cat(msg, file = .out, sep = "")
    flush(.out)
    quit(status = 1)
} else {
    invisible(lapply(pkgs, library, character.only = TRUE))
}

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


while (TRUE) {
    line <- readLines(con = "stdin", n = 1, warn = FALSE)
    if (length(line) == 0) break

    request <- fromJSON(line)

    if (!is.null(request$width)) {
        options(width = request$width)
    }

    exprs <- tryCatch(
        parse(text = request$code),
        error = function(e) {
            send_done(error = conditionMessage(e))
            NULL
        }
    )
    
    if (is.null(exprs)) next

    error_msg <- NULL

    handler <- new_output_handler(
        text = \(x) send_chunk(x),
        value = function(x, visible) {
            if (visible) {
                text <- paste(capture.output(print(x)), collapse = "\n")
                send_chunk(paste0(text, "\n"))
            }
        },
        warning = function(x) {
            send_chunk(paste0("Warning: ", conditionMessage(x), "\n"))
            invokeRestart("muffleWarning")
        },
        error = \(x) error_msg <<- conditionMessage(x)
    )

    for (i in seq_along(exprs)) {
        original <- paste(deparse(exprs[[i]]), collapse = "\n")
        modified <- paste(deparse(inject_flush(exprs[[i]])), collapse = "\n")
        send_expression(original)
        evaluate(modified, output_handler = handler, stop_on_error = 1L)
        if (!is.null(error_msg)) break
    }

    send_done(error_msg)
}