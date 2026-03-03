.plugin_dir <- commandArgs(trailingOnly = TRUE)
source(file.path(.plugin_dir, "core", "r", "worker.R"), local = TRUE)

.worker_env$run()
