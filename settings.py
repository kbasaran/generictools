import logging
import json
from PySide6 import QtCore as qtc


class SettingsManager(qtc.QObject):
    _instance = None
    _initialized = False
    settings_changed = qtc.Signal()

    def __new__(cls, app_definitions=None, defaults=None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, app_definitions=None, defaults=None):
        if self.__class__._initialized:
            return
        super().__init__()
        if app_definitions is None or defaults is None:
            raise ValueError("app_definitions and defaults must be provided on first instantiation")
        self.app_definitions = app_definitions
        self.DEFAULTS = defaults
        self.q_settings = qtc.QSettings(
            app_definitions["author_short"],
            self.get_storage_title()
        )
        self.__class__._initialized = True

    def get_storage_title(self):
        version = self.app_definitions["version"]
        return (
            self.app_definitions["app_name"]
            + " v"
            + (".".join(version.split(".")[:2]) if "." in version else "???")
        )

    def get_value(self, key: str):
        """
        Retrieve value from QSettings.
        If key doesn't exist, return the default value from DEFAULTS.
        Returns the value with its original JSON type.
        """
        if not self.q_settings.contains(key):
            return self.DEFAULTS.get(key)

        raw = self.q_settings.value(key)
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return raw

    def get_all_as_dict(self):
        """Retrieve all settings as a dictionary."""
        return {key: self.get_value(key) for key in self.DEFAULTS.keys()}

    def set_all_from_dict(self, settings_dict: dict, signal=True):
        """Set all settings from a dictionary."""
        for key, value in settings_dict.items():
            self.set_value(key, value, signal=False)
        if signal:
            self.settings_changed.emit()

    def set_value(self, key: str, value, signal=True):
        """
        Store value as JSON string in QSettings.
        Emits setting_changed signal with key and value.
        """
        if isinstance(value, dict):
            new_value = value["current_text"]  # handles data coming from comboboxes. stores main text only.
        else:
            new_value = value

        json_string = json.dumps(new_value)
        self.q_settings.setValue(key, json_string)
        if signal:
            self.settings_changed.emit()

    def remove_value(self, key: str):
        """Delete a setting. Next get_value will return the default."""
        self.q_settings.remove(key)

    def reset_to_default(self, key: str):
        """Remove a setting so it falls back to the default value."""
        self.remove_value(key)

    def reset_all_to_defaults(self):
        """Clear all settings and reload from DEFAULTS."""
        self.q_settings.clear()
        self.settings_changed.emit()

    def sync(self):
        """Force write to disk."""
        self.q_settings.sync()

    def get_all_defaults(self):
        """Return a copy of the defaults dictionary."""
        return self.DEFAULTS.copy()

    def clear(self):
        """Clear all settings and reload from DEFAULTS."""
        self.q_settings.clear()
        self.settings_changed.emit()


def singleton_settings():
    from config.app_config import APP_DEFINITIONS, DEFAULTS
    return SettingsManager(APP_DEFINITIONS, DEFAULTS)


if __name__ == "__main__":
    pass
else:
    logger = logging.getLogger(__name__)
