"""Defines result classes for parsing messages from the R process."""
from .utils import MissingDependencyError

class RResult:
    stdout = ""
    error = None
    wd = None
    expression = None

    @staticmethod
    def from_msg(msg):
        match msg["type"]:
            case "chunk":       return ChunkResult(msg)
            case "done":        return DoneResult(msg)
            case "expression":  return ExpressionResult(msg)
            case "request":     return RequestResult(msg)
            case "question":    return QuestionResult(msg)
            case "pkg":         return PkgResult(msg)
            case "help":        return HelpResult(msg)
            case "plot_server": return PlotServerResult(msg)
            case "missing":     raise MissingDependencyError(msg["data"])


class ChunkResult(RResult):
    def __init__(self, msg):
        self.stdout = msg["data"]
        self.error = None
        self.wd = msg.get("wd")


class DoneResult(RResult):
    def __init__(self, msg):
        self.error = msg.get("error")
        self.wd = msg.get("wd")


class ExpressionResult(RResult):
    def __init__(self, msg):
        self.expression = msg["data"]


class RequestResult(RResult):
    def __init__(self, msg):
        self.method = msg["method"]
        self.args = msg.get("args")


class QuestionResult(RequestResult):
    def __init__(self, msg):
        self.method = "question"
        self.args = msg


class PkgResult(RResult):
    def __init__(self, msg):
        self.signatures = msg["data"]


class HelpResult(RResult):
    def __init__(self, msg):
        self.path = msg["path"]


class PlotServerResult(RResult):
    def __init__(self, msg):
        self.port = msg["data"]["port"]
        self.token = msg["data"]["token"]
