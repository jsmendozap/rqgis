get_signatures <- function(pkg) {
    get_s3_methods <- function(pkg) {
        ns <- tryCatch(asNamespace(pkg), error = function(e) NULL)
        if (is.null(ns)) return(character(0L))
        tbl <- tryCatch(
            get(".__S3MethodsTable__.", envir = ns, inherits = FALSE),
            error = function(e) NULL
        )
        if (is.null(tbl)) return(character(0L))
        ls(tbl)
    }

    should_keep <- function(fname, s3_registered) {
        grepl("^[a-zA-Z._][a-zA-Z0-9._]*$", fname) &
        !endsWith(fname, "<-")                       &
        !startsWith(fname, ".")                      &
        !grepl("^[A-Z]", fname)                      &
        !(fname %in% s3_registered)
    }

    sig_for_fun <- function(fname) {
        f <- tryCatch(
            get(fname, envir = asNamespace(pkg), inherits = FALSE),
            error = function(e) NULL
        )
        if (is.null(f) || !is.function(f)) return(NA_character_)
        fm <- tryCatch(formals(f), error = function(e) NULL)
        if (is.null(fm)) return(NA_character_)
        arg_names <- names(fm)
        arg_strs <- character(0L)
        for (i in seq_along(fm)) {
            nm <- arg_names[[i]]
            if (is.null(nm) || !nzchar(nm) || nm == "...") next
            raw <- tryCatch(deparse(fm[[i]])[1L], error = function(e) "")
            arg_strs <- c(arg_strs,
                if (!nzchar(raw)) nm else sprintf("%s = %s", nm, raw))
        }
        if (length(arg_strs) > 3) {
            paste0(fname, "(\n  ", paste(arg_strs, collapse = ",\n  "), "\n)")
        } else {
            paste0(fname, "(", paste(arg_strs, collapse = ", "), ")")
        }
    }

    exports <- tryCatch(getNamespaceExports(pkg), error = function(e) character(0L))
    exports <- exports[nzchar(exports)]
    s3      <- get_s3_methods(pkg)
    exports <- exports[should_keep(exports, s3)]

    sigs <- vapply(exports, sig_for_fun, character(1L), USE.NAMES = FALSE)
    sigs[!is.na(sigs)]
}