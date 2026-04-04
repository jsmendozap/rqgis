.worker_env <- local({

    source(file.path("core", "r", "signatures.R"),  local = TRUE)
    source(file.path("core", "r", "utils.R"), local = TRUE)
    source(file.path("core", "r", "protocol.R"), local = TRUE)
    source(file.path("core", "r", "interactive.R"), local = TRUE)

    .fns <- NULL

    run <- function(){

        while (TRUE) {
            line <- readLines(con = "stdin", n = 1, warn = FALSE)
            if (length(line) == 0) break

            tryCatch({
                request <- fromJSON(line)

                if (!is.null(request$width)) {
                    options(width = request$width)
                }

                if (!is.null(request$type) && request$type == "update") {
                    vars <- ls(globalenv())
                    existing <- vars[sapply(vars, \(x) inherits(get(x, envir = globalenv()), "QgisProject"))]
                    if (length(existing) > 0) {
                        assign(existing[1], qgis_project(request$data), envir = globalenv())
                    }
                    next
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
                .before <- search()

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
                    message = function(x) {
                        send_chunk(conditionMessage(x))
                        invokeRestart("muffleMessage")
                    },
                    error = \(x) error_msg <<- conditionMessage(x)
                )

                for (i in seq_along(exprs)) {
                    original <- paste(deparse(exprs[[i]]), collapse = "\n")
                    modified <- paste(deparse(inject_flush(exprs[[i]])), collapse = "\n")
                    send_expression(original)
                    
                    if (grepl("^`\\?`|^\\?|^help\\(", trimws(original))) {
                        topic <- trimws(original)
                        topic <- sub("^`\\?`\\((.+)\\)$", "\\1", topic)
                        topic <- sub("^\\?+", "", topic)
                        topic <- sub("^help\\((.+)\\)$", "\\1", topic)
                        topic <- gsub('["\']', '', topic) 
                        
                        url <- as.character(help(topic, help_type = "html"))

                        if (length(url) == 0) {
                            send_done(error = paste("function", topic, "not found"))
                        } else {
                            send_help(url)
                        }
                        next
                    }

                    evaluate(modified, output_handler = handler, stop_on_error = 1L,
                            envir = globalenv(), new_device = FALSE)
                    if (!is.null(error_msg)) break
                }

                check_new_pkgs(.before)
                if (!is.null(.fns)) {          
                    send_fns(.fns)
                    .fns <<- NULL
                }

                send_done(error_msg)
            }, error = function(e) {
                send_done(error = conditionMessage(e))
            })
        }
    }
    environment()
})
