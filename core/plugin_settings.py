from qgis.PyQt.QtCore import QSettings
import os

_settings = QSettings("r_console", "RConsole")

KEY_R_PATH    = "r_path"
KEY_INITIAL_WD = "initial_wd"
KEY_STATUS_DEBUG = "enable_session_log"
KEY_LOG_DIR = "session_log_dir"


def get_r_path():
    return _settings.value(KEY_R_PATH, "", type=str)

def set_r_path(path):
    _settings.setValue(KEY_R_PATH, path)

def get_initial_wd():
    wd = _settings.value(KEY_INITIAL_WD, "", type=str)
    if not wd:
        wd = os.path.expanduser("~")
    return wd

def set_initial_wd(path):
    _settings.setValue(KEY_INITIAL_WD, path)

def get_status_debug():
    return _settings.value(KEY_STATUS_DEBUG, False, type=bool)

def set_status_debug(enabled):
    _settings.setValue(KEY_STATUS_DEBUG, bool(enabled))

def get_log_dir():
    return _settings.value(KEY_LOG_DIR, "", type=str)

def set_log_dir(path):
    _settings.setValue(KEY_LOG_DIR, path)
