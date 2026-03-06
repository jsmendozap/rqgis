from .utils import MissingDependencyError

class RResult(dict):

    def __init__(self, msg):
        super().__init__()
        self.stdout = ""
        self.error = None
        self.wd = None
        self.expression = None
        self.is_done = False
        self.is_request = False
        self.is_pkg = False
        self.method = None
        self.args = None
        self.signatures = None
        self._parse(msg)

    def _parse(self, msg):
        match msg["type"]:
            case "expression":
                self.expression = msg["data"]
            case "chunk":
                self.stdout = msg["data"]
                self.wd = msg.get("wd")
                self.update(stdout=self.stdout, error=None, wd=self.wd)
            case "done":
                self.error = msg.get("error")
                self.wd = msg.get("wd")
                self.is_done = True
                self.update(stdout="", error=self.error, wd=self.wd)
            case "error":
                self.error = msg.get("data")
                self.is_done = True
                self.update(stdout="", error=self.error, wd=None)
            case "request":
                self.method = msg["method"]
                self.args = msg.get("args")
                self.is_request = True
                self.is_done = False
            case "pkg":
                self.signatures = msg['data']
                self.is_pkg = True
            case "missing":
                raise MissingDependencyError(f"The following R packages are required but are not installed: {msg['data']}")

    def __bool__(self):
        return not self.is_done