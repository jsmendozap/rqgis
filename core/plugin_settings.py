from qgis.PyQt.QtCore import QSettings
import os

_settings = QSettings("r_console", "RConsole")

KEY_R_PATH    = "r_path"
KEY_INITIAL_WD = "initial_wd"
KEY_ENABLE_LOG = "enable_session_log"
KEY_LOG_DIR = "session_log_dir"


def get_r_path():
    return _settings.value(KEY_R_PATH, "", type=str)

def set_r_path(path: str):
    _settings.setValue(KEY_R_PATH, path)

def get_initial_wd():
    wd = _settings.value(KEY_INITIAL_WD, "", type=str)
    if not wd:
        wd = os.path.expanduser("~")
    return wd

def set_initial_wd(path):
    _settings.setValue(KEY_INITIAL_WD, path)

def get_enable_log():
    return _settings.value(KEY_ENABLE_LOG, False, type=bool)

def set_enable_log(enabled):
    _settings.setValue(KEY_ENABLE_LOG, bool(enabled))

def get_log_dir():
    return _settings.value(KEY_LOG_DIR, "", type=str)

def set_log_dir(path):
    _settings.setValue(KEY_LOG_DIR, path)
