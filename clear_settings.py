from PySide6 import QtWidgets as qtw
from pathlib import Path
from config.linecraft_config import singleton_settings

qapp = qtw.QApplication.instance()
if not qapp:
    qapp = qtw.QApplication()

mw = qtw.QWidget()
mw.setWindowTitle("Settings Viewer / Clearer")
layout = qtw.QVBoxLayout()

label = qtw.QLabel()
layout.addWidget(label)

app_settings = singleton_settings()

# Build the display text (without clearing anything yet)
label_text = f"Storage title: {app_settings.get_storage_title()}\n"
label_text += "Data:\n\n"
for key, val in app_settings.get_all_as_dict().items():
    label_text += f"{key}: {type(app_settings.get_value(key))}, value: {app_settings.get_value(key)}\n"
label_text += "\nPress OK to clear all stored settings, or Cancel to leave them unchanged."
label.setText(label_text)

# Button row
button_layout = qtw.QHBoxLayout()
ok_button = qtw.QPushButton("OK")
cancel_button = qtw.QPushButton("Cancel")
button_layout.addWidget(ok_button)
button_layout.addWidget(cancel_button)
layout.addLayout(button_layout)

mw.setLayout(layout)
mw.setMinimumSize(600, 600)


def on_ok():
    app_settings.clear()
    label.setText(label_text.split("\nPress OK")[0] + "\nAll stored settings cleared.")
    ok_button.setEnabled(False)
    cancel_button.setEnabled(False)


def on_cancel():
    mw.close()


ok_button.clicked.connect(on_ok)
cancel_button.clicked.connect(on_cancel)

mw.show()
qapp.exec()