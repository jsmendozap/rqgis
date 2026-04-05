from datetime import datetime, timezone
import os 
import json

class SessionLogger:
    """A simple logger that writes R console sessions to a file."""
    def __init__(self, log_dir):
        self.path = os.path.join(log_dir, "session.log")
        try:
            self._fp = open(self.path, "w", encoding="utf-8")
        except OSError:
            self._fp = None

    def log(self, direction, data):

        match direction:
            case 1:
                direction = "stdout"
            case 2:
                direction = "stderr"

        if self._fp:
            try:
                msg = json.loads(data)
            except (json.JSONDecodeError, TypeError):
                msg = data
            
            entry = {
                "time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "level": "info",
                "route": direction
            }
            entry.update(msg if isinstance(msg, dict) else {"msg": msg})
            self._fp.write(json.dumps(entry) + "\n")
            self._fp.flush()

    def close(self):
        if self._fp:
            self._fp.close()
            self._fp = None
