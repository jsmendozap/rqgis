#.plugin_dir <- commandArgs(trailingOnly = TRUE)[1]
#source(file.path(.plugin_dir, "core", "r", "worker.R"))
.out <- stdout()

source("core/r/worker.R", local = TRUE)
source("core/r/qgis.R", local = TRUE)

.worker_env$run()
