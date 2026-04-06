import os 
import json

class SessionLogger:
    """A simple logger that writes R console sessions to a file."""
    def __init__(self, path):
        self.path = os.path.join(path, "session.log")
        try:
            self._fp = open(self.path, "w", encoding="utf-8")
        except OSError:
            self._fp = None

    def log(self, direction, data):
        match direction:
            case 1:
                direction = "QGIS → R"
            case 2:
                direction = "R → QGIS"

        if not self._fp:
            return

        try:
            msg = json.loads(data)
        except json.JSONDecodeError:
            msg = {"type": "error", "data": data}

        msg |= {"route": direction}
        self._fp.write(json.dumps(msg) + "\n")
        self._fp.flush()

    def close(self):
        if self._fp:
            self._fp.close()
            self._fp = None
