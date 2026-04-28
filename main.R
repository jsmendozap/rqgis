.plugin_dir <- commandArgs(trailingOnly = TRUE)[1]
.qgis_process <- commandArgs(trailingOnly = TRUE)[2]
.out <- stdout()

cat("READY\n")
flush(.out)

local({
    pkgs <- c("jsonlite", "evaluate", "R6", "httpgd")
    missing <- pkgs[!sapply(pkgs, requireNamespace, quietly = TRUE)]

    if (length(missing) > 0) {
        msg <- sprintf('{"type":"missing","data":"%s"}\n', paste0(missing, collapse = ", "))
        cat(msg, file = .out, sep = "")
        flush(.out)
        quit(status = 1)
    } else {
        invisible(lapply(pkgs[1:3], library, character.only = TRUE))
        suppressMessages(tools::startDynamicHelp())

        source(file.path(.plugin_dir, "core", "r", "protocol.R"), local = TRUE)
    
        if ("png" %in% unigd::ugd_renderers()$id) {
            httpgd::hgd(width = 380, height = 250, silent = TRUE)
            par(mar = c(4, 4, 2, 1))
            details <- httpgd::hgd_details()
            send_message("plot_server", list(
                port = details$port,
                token = details$token
            ))

            if (requireNamespace("qgisprocess", quietly = TRUE)) {
                options(qgisprocess.path = .qgis_process)
                qgisprocess::qgis_configure(use_cached_data = TRUE, quiet = TRUE)
            }

        } else {
            send_message("notify", "Plots disabled: PNG renderer was not found.")
        }
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
