from PySide6 import QtWidgets as qtw
from PySide6 import QtCore as qtc
from pathlib import Path

qapp = qtw.QApplication.instance()
if not qapp:
    qapp = qtw.QApplication()

mw = qtw.QWidget()
layout = qtw.QVBoxLayout()
label = qtw.QLabel()
layout.addWidget(label)
mw.setLayout(layout)


app_definitions = {"app_name": "Test Signal Maker",
                   "version": "0.2.3",
                   # "version": "Test build " + today.strftime("%Y.%m.%d"),
                   "description": "Test Signal Maker - Loudspeaker test signal tool",
                   "copyright": "Copyright (C) 2024 Kerem Basaran",
                   "icon_path": str(Path("./logo/icon.ico")),
                   "author": "Kerem Basaran",
                   "author_short": "kbasaran",
                   "email": "kbasaran@gmail.com",
                   "website": "https://github.com/kbasaran",
                   }

settings_storage_title = app_definitions["app_name"] + " - " + (app_definitions["version"].split(".")[0] if "." in app_definitions["version"] else "")

settings = qtc.QSettings(app_definitions["author_short"], settings_storage_title)

label_text = f"Storage title: {settings_storage_title}\n"
label_text += "Data:\n\n"
for key in settings.allKeys():
    label_text += f"{key}: {type(settings.value(key))}, value: {settings.value(key)}\n"

# Clear settings
settings.clear()
label_text += "\nAll stored settings cleared."

label.setText(label_text)
mw.show()
qapp.exec()
