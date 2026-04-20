from qgis.PyQt.QtWidgets import (
    QInputDialog, QFileDialog, QDialog,
    QVBoxLayout, QTableView, QHeaderView,
    QTreeView
)
from qgis.PyQt.QtWidgets import QAbstractItemView
from qgis.PyQt.QtGui import QStandardItemModel, QStandardItem
from ..qt.widgets import QDialogButtonBox, QMessageBox

import os
import csv
import json
from .editor import EditorTab

class QuestionDialog:

    def __init__(self, parent, method, args):
        self.parent = parent
        self.method = method
        self.args = args

    def dispatch(self):
        match self.method:
            case "ask_yes_no":
                return self._ask_yes_no()
            case "menu":
                return self._show_menu()
            case "file_choose":
                return self._file_choose()
            case "file_edit":
                return self._file_edit()
            case "readline":
                return self._readline()
            case "show_table":
                return self._show_table()
            case "show_tree":
                return self._show_tree()

    def _ask_yes_no(self):
        question = self.args.get("question", "")
        default = self.args.get("default", True)

        default_btn = QMessageBox.Yes if default else QMessageBox.No
        ret = QMessageBox.question(self.parent, "R Question", question, QMessageBox.Yes | QMessageBox.No, default_btn)
        return {"type": "response", "data": ret == QMessageBox.Yes}
    
    def _show_menu(self):
        choices = self.args.get("choices", [])
        title = self.args.get("title") or "R Menu"
        item, ok = QInputDialog.getItem(self.parent, "R Input", title, choices, 0, False)
        if not ok:
            return {"type": "response", "data": 0}
        return {"type": "response", "data": choices.index(item) + 1}

    def _file_choose(self):
        new = self.args.get("new", False)
        if new:
            path, _ = QFileDialog.getSaveFileName(self.parent, "R File Choose")
        else:
            path, _ = QFileDialog.getOpenFileName(self.parent, "R File Choose")
        
        if not path:
            return {"type": "response", "data": ""}
        return {"type": "response", "data": path}

    def _file_edit(self):
        file_path = self.args.get("file", "")
        title = self.args.get("title") or "R Editor"
        dialog, layout = self._make_dialog(title)
        
        editor = EditorTab(dialog)
        if file_path and os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                editor.setText(f.read())
            editor.mark_saved(file_path)
            
        layout.addWidget(editor)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("Save and Close")
        
        def save_and_accept():
            if file_path:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(editor.text())
            dialog.accept()
            
        buttons.accepted.connect(save_and_accept)
        buttons.rejected.connect(dialog.reject)
        if not self.args.get("remove_on_close", False):
            layout.addWidget(buttons)
        
        dialog.exec_()
        self._remove_file(file_path, self.args.get("remove_on_close", False))
        return {"type": "response", "data": True}

    def _show_table(self):
        file_path = self.args.get("file", "")
        title = self.args.get("title") or "R View"

        dialog, layout = self._make_dialog(title)
        
        table = QTableView()
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setSortingEnabled(True)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        if file_path and os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                data = list(reader)
                if data:
                    model = QStandardItemModel()
                    model.setColumnCount(len(data[0]))
                    model.setHorizontalHeaderLabels(data[0])
                    for row_data in data[1:]:
                        items = [QStandardItem(cell_data) for cell_data in row_data]
                        model.appendRow(items)
                    table.setModel(model)
                            
        layout.addWidget(table)
        
        dialog.exec_()
        self._remove_file(file_path, self.args.get("remove_on_close", False))
        return {"type": "response", "data": True}

    def _show_tree(self):
        file_path = self.args.get("file", "")
        title = self.args.get("title") or "R View"

        dialog, layout = self._make_dialog(title)
        tree = QTreeView()
        tree.setUniformRowHeights(True)
        tree.setEditTriggers(QAbstractItemView.NoEditTriggers)

        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["Name", "Value"])

        if file_path and os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                def value_for_node(value):
                    if isinstance(value, dict) and "__r_meta__" in value and "__r_children__" in value:
                        meta = value.get("__r_meta__", {})
                        r_type = meta.get("type", "list")
                        r_value = meta.get("value", "")
                        if r_type == "data.frame":
                            return f"Data Frame of dims {r_value}"
                        return str(r_value)
                    if isinstance(value, dict):
                        return f"List of length {len(value)}"
                    if isinstance(value, list):
                        return f"Vector of length {len(value)}"
                    return "" if value is None else str(value)

                def iter_children(value):
                    if isinstance(value, dict) and "__r_meta__" in value and "__r_children__" in value:
                        children = value.get("__r_children__", {})
                        if isinstance(children, dict):
                            return children.items()
                        return []
                    if isinstance(value, dict):
                        return value.items()
                    if isinstance(value, list):
                        return [(i + 1, v) for i, v in enumerate(value)]
                    return []

                def add_node(parent, key, value):
                    key_item = QStandardItem(str(key))
                    value_item = QStandardItem(value_for_node(value))
                    parent.appendRow([key_item, value_item])
                    for k, v in iter_children(value):
                        add_node(key_item, k, v)

                root = model.invisibleRootItem()
                if isinstance(data, dict):
                    for k, v in data.items():
                        add_node(root, k, v)
                elif isinstance(data, list):
                    for i, v in enumerate(data):
                        add_node(root, i, v)
                else:
                    add_node(root, "value", data)
            except (OSError, json.JSONDecodeError):
                pass

        tree.setModel(model)
        tree.header().setSectionResizeMode(QHeaderView.Stretch)
        tree.collapseAll()
        if model.rowCount() > 0:
            tree.setExpanded(model.index(0, 0), True)
        layout.addWidget(tree)

        dialog.exec_()
        self._remove_file(file_path, self.args.get("remove_on_close", False))
        return {"type": "response", "data": True}

    def _readline(self):
        prompt = self.args.get("prompt", "")
        text, ok = QInputDialog.getText(self.parent, "R Input", prompt)
        if not ok:
            return {"type": "response", "data": ""}
        return {"type": "response", "data": text}

    def _make_dialog(self, title):
        dialog = QDialog(self.parent)
        dialog.setWindowTitle(title)
        dialog.resize(800, 600)
        layout = QVBoxLayout(dialog)
        return dialog, layout

    def _remove_file(self, file_path, remove):
        if not remove:
            return
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
