.lib <- file.path(.plugin_dir, "lib")
dir.create(.lib, showWarnings = FALSE)
.libPaths(c(.lib, .libPaths()))

options(rqgis.qgis_process = .qgis_process)

pkg <- file.path(.plugin_dir, "core", "r", "rqgis")
source_version <- package_version(read.dcf(file.path(pkg, "DESCRIPTION"), fields = "Version"))

installed_version <- tryCatch(
    utils::packageVersion("rqgis", lib.loc = .lib),
    error = function(e) NULL
)

if (is.null(installed_version) || installed_version != source_version) {
    install.packages(pkg, lib = .lib, repos = NULL, type = "source", quiet = TRUE)
}

setHook(packageEvent("qgisprocess", "onLoad"), function(libname, pkgname) {
    path <- getOption("rqgis.qgis_process")
    if (!is.null(path)) options(qgisprocess.path = path)
    qgisprocess::qgis_configure(use_cached_data = TRUE, quiet = TRUE)
})