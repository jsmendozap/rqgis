library(jsonlite)
options(echo = FALSE) # Vital cuando se usa R.exe/R en lugar de Rscript

cat("READY\n")
flush(stdout())

while (TRUE) {
    line <- readLines(con = "stdin", n = 1, warn = FALSE)

    if (length(line) == 0) break

    request <- fromJSON(line)
    code <- request$code

    output_con <- textConnection("output", "w", local = TRUE)
    sink(output_con, type = "output")
    sink(output_con, type = "message")

    error_msg <- NULL

    tryCatch({
        withCallingHandlers({
                expr <- parse(text = code)
                vis <- withVisible(eval(expr, envir = globalenv()))
                if (vis$visible) print(vis$value)
            },
            warning = function(w) {
                cat("Warning: ", conditionMessage(w), "\n")
                invokeRestart("muffleWarning")
            })
        }, 
        error = function(e) {
            error_msg <<- conditionMessage(e)
        },
        finally = {
            sink(type = "output")
            try(sink(type = "message"), silent = TRUE)
            close(output_con)
    })

    response <- toJSON(
        list(
            stdout = paste(output, collapse = "\n"),
            error = error_msg
        ),
        auto_unbox = TRUE,
        null = "null"
    )
    cat(response, "\n")
    flush(stdout())
}