"""Internal helpers for Qt compatibility shims."""


def scoped(owner, scope_name, value_name):
    scope = getattr(owner, scope_name, None)
    if scope is None:
        return None
    return getattr(scope, value_name, None)
