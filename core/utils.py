from subprocess import run
import os

def is_valid_rscript(path):
        path = os.path.realpath(path)
        if not os.path.isfile(path) or not os.access(path, os.X_OK):
            return False
        try:
            result = run(
                [path, '-e', 'R.version.string'],
                capture_output=True,
                text=True,
                timeout=5
            )
            output = result.stdout + result.stderr
            return 'R version' in output
        except Exception:
            return False

class RPathRequiredError(RuntimeError):
    pass    

class MissingDependencyError(RuntimeError):
    pass