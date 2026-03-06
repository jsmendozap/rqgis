.plugin_dir <- commandArgs(trailingOnly = TRUE)
source(file.path(.plugin_dir, "core", "r", "worker.R"), local = TRUE)

options(echo = FALSE, max.print = 100)
.out <- stdout()

cat("READY\n")
flush(.out)

local({
    pkgs <- c("jsonlite", "evaluate", "R6")
    missing <- pkgs[!sapply(pkgs, requireNamespace, quietly = TRUE)]

    if (length(missing) > 0) {
        msg <- sprintf('{"type":"missing","data":"%s"}\n', paste0(missing, collapse = ", "))
        cat(msg, file = .out, sep = "")
        flush(.out)
        quit(status = 1)
    } else {
        invisible(lapply(pkgs[1:3], library, character.only = TRUE))
    }
})

.worker_env$run()
