.plugin_dir <- commandArgs(trailingOnly = TRUE)

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

.qgis <- new.env()
.qgis$qgis_project <- function(data = NULL){
    source(file.path(.plugin_dir, "core", "r", "qgis.R"), local = TRUE)
    return(QgisProject$new(data))
}
attach(.qgis, pos = 2L, name = "qgis:utils", warn.conflicts = FALSE)
source(file.path(.plugin_dir, "core", "r", "worker.R"), local = TRUE)

.worker_env$run()
