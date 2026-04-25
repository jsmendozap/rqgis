from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout
from ..qt.gui import QFont
from ..qt.widgets import QTextEdit

import json
import html

class LogViewerDialog(QDialog):
    COL_COLORS = ["#24292e", "#22863a", "#005cc5", "#6f42c1", "#e36209"]
    COL1_W = 12
    COL2_W = 13
    INDENT_3 = COL1_W + 1 + COL2_W + 3
    TERM_W = 120

    def __init__(self, log_file, parent=None):
        super().__init__(parent)
        self.setWindowTitle("R Session Logs")
        self.setMinimumSize(900, 400)
        
        layout = QVBoxLayout(self)
        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)
        self.text_edit.setLineWrapMode(QTextEdit.NoWrap)
        
        font = QFont("Courier")
        font.setStyleHint(QFont.Monospace)
        self.text_edit.setFont(font)
        
        layout.addWidget(self.text_edit)
        self._load_logs(log_file)
        
    def _load_logs(self, log_file):
        html_content = ["<pre>"]
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    html_content.append(self._format_entry(entry))
                except json.JSONDecodeError:
                    html_content.append(f"{html.escape(line)}\n")
        html_content.append("</pre>")
        self.text_edit.setHtml("".join(html_content))

    def _wrap(self, text, indent):
        if not text:
            return ""
        avail = max(20, self.TERM_W - indent - 2)
        result = []
        for i, line in enumerate(text.splitlines()):
            prefix = "" if i == 0 else " " * indent
            if len(line) <= avail:
                result.append(prefix + line)
            else:
                first = True
                while line:
                    chunk = line[:avail]
                    line = line[avail:]
                    p = "" if (i == 0 and first) else " " * indent
                    result.append(p + chunk)
                    first = False
        return "\n".join(result)

    def _columns(self, msg):
        t = msg.get("type", "")

        if t == "code":
            code = msg.get("code", "")
            parts = [self._wrap(code, self.INDENT_3)]
            if "width" in msg:
                parts.append(f"width={msg['width']}")
            return parts

        if t in ("send", "expression"):
            return [self._wrap(msg.get("data", ""), self.INDENT_3)]

        if t == "chunk":
            return [self._wrap(msg.get("data", "").rstrip("\n"), self.INDENT_3)]

        if t == "done":
            err = msg.get("error")
            err_str = f"error={err}" if err else "error=null"
            return [self._wrap(err_str, self.INDENT_3), f"wd={msg.get('wd', '')}"]

        if t == "plot_server":
            d = msg.get("data", {})
            if isinstance(d, str):
                try:
                    d = json.loads(d)
                except json.JSONDecodeError:
                    pass
            if not isinstance(d, dict):
                d = {}
            return [f"port={d.get('port', '?')}", f"token={d.get('token', '?')}"]

        if t in ("request", "question"):
            method = msg.get("method", "")
            args = json.dumps(msg.get("args", {}), ensure_ascii=False)
            indent_args = self.INDENT_3 + len(method) + 2
            return [method, self._wrap(args, indent_args)]

        if t == "help":
            html_text = msg.get("html", msg.get("data", ""))
            return [html_text[:50] + "..." if len(html_text) > 50 else html_text]

        if t == "pkg":
            data = str(msg.get("data", ""))
            return [data[:50] + "..." if len(data) > 50 else data]

        if t in ("error", "missing"):
            return [str(msg.get('data', msg.get('error', '')))]

        data = msg.get("data", msg.get("code", ""))
        return [self._wrap(str(data), self.INDENT_3)]

    def _colorize(self, text, idx, is_error=False):
        c = "#d73a49" if is_error else self.COL_COLORS[idx % len(self.COL_COLORS)]
        lines = text.splitlines()
        if not lines:
            return ""
        return "\n".join(f'<span style="color: {c};">{html.escape(l)}</span>' for l in lines)
        
    def _format_entry(self, entry):
        route = entry.get("route", "")
        t = entry.get("type", "code")
        
        route_color = "#005cc5" if route.startswith("QGIS") else "#22863a"
        
        tag1 = f"[{route}]"
        pad1 = " " * max(0, self.COL1_W - len(tag1) + 1)
        col1 = f'<span style="color: {route_color};"><b>{html.escape(tag1)}</b></span>'
        
        tag2 = f"[{t}]"
        pad2 = " " * max(0, self.COL2_W - len(tag2) + 1)
        col2 = f'<span style="color: #6f42c1;">{html.escape(tag2)}</span>'
        
        prefix = "\n" if route.startswith("QGIS") else ""
        header = f'{prefix}{col1}{pad1}{col2}{pad2}<span style="color: #808080;">&gt;</span> '
        cols = self._columns(entry)

        colored = []
        for i, c in enumerate(cols):
            is_err = False
            if t in ("error", "missing") and i == 0:
                is_err = True
            elif t == "done" and i == 0 and c != "error=null":
                is_err = True
            colored.append(self._colorize(c, i, is_err))

        if len(cols) == 1:
            return header + colored[0] + "\n"

        lines_per_col = [c.splitlines() for c in colored]
        max_lines = max((len(l) for l in lines_per_col), default=0)

        result = []
        for j in range(max_lines):
            parts = []
            for col_lines in lines_per_col:
                if j < len(col_lines):
                    parts.append(col_lines[j])
            if j == 0:
                result.append("  ".join(parts))
            else:
                result.append("".join(parts))

        return header + "\n".join(result) + "\n"