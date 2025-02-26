# This file is part of Linecraft - Frequency response display and statistics tool
# Copyright (C) 2023 - Kerem Basaran
# https://github.com/kbasaran
__email__ = "kbasaran@gmail.com"

# Linecraft is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation, either version 3
# of the License, or (at your option) any later version.

# Linecraft is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public
# License along with Linecraft. If not, see <https://www.gnu.org/licenses/>

import traceback

from PySide6 import QtWidgets as qtw
from PySide6 import QtCore as qtc
from PySide6 import QtGui as qtg

import sounddevice as sd
import numpy as np
from generictools import signal_tools
import pickle

import logging
if __name__ == "__main__":
    logger = logging.getLogger(__name__)
else:
    logging.basicConfig(level=logging.WARNING)
    logger = logging.getLogger()


class FloatSpinBox(qtw.QDoubleSpinBox):
    def __init__(self, name, tooltip,
                 decimals=2,
                 min_max=(None, None),
                 coeff_for_SI=1,
                 ):
        self._name = name
        self.coeff_for_SI = coeff_for_SI
        super().__init__()
        if tooltip:
            self.setToolTip(tooltip)
        self.setStepType(qtw.QAbstractSpinBox.StepType.AdaptiveDecimalStepType)
        self.setDecimals(decimals)

        if min_max[0] is not None:
            self.setMinimum(min_max[0])
        else:
            self.setMinimum(1 / 10**self.decimals())

        if min_max[1] is not None:
            self.setMaximum(min_max[1])
        else:
            self.setMaximum((1000_000 - 1) / 10**self.decimals())

    def add_elements_to_dict(self, user_data_widgets: dict):
        user_data_widgets[self._name] = self


class IntSpinBox(qtw.QSpinBox):
    def __init__(self, name, tooltip,
                 min_max=(None, None),
                 coeff_for_SI=1,
                 ):
        self._name = name
        self.coeff_for_SI = coeff_for_SI
        super().__init__()
        if tooltip:
            self.setToolTip(tooltip)

        if min_max[0] is not None:
            self.setMinimum(min_max[0])
        else:
            self.setMinimum(0)

        if min_max[1] is not None:
            self.setMaximum(min_max[1])
        else:
            self.setMaximum(99_999)

    def add_elements_to_dict(self, user_data_widgets: dict):
        user_data_widgets[self._name] = self

class CheckBox(qtw.QCheckBox):
    def __init__(self, name, tooltip,
                 ):
        self._name = name
        super().__init__()
        if tooltip:
            self.setToolTip(tooltip)

    def add_elements_to_dict(self, user_data_widgets: dict):
        user_data_widgets[self._name] = self

class LineTextBox(qtw.QLineEdit):
    def __init__(self, name, tooltip):
        self._name = name
        super().__init__()
        if tooltip:
            self.setToolTip(tooltip)

    def add_elements_to_dict(self, user_data_widgets: dict):
        user_data_widgets[self._name] = self


class SunkenLine(qtw.QFrame):
    def __init__(self):
        super().__init__()
        self.setFrameShape(qtw.QFrame.HLine)
        self.setFrameShadow(qtw.QFrame.Sunken)
        self.setContentsMargins(0, 10, 0, 10)


class Title(qtw.QLabel):
    def __init__(self, text:str):
        super().__init__()
        self.setText(text)
        self.setStyleSheet("font-weight: bold")
        self.setAlignment(qtg.Qt.AlignmentFlag.AlignCenter)


class PushButtonGroup(qtw.QWidget):
    def __init__(self, names: dict, tooltips: dict, vertical=False):
        """Both names and tooltips have the same keys: short_name's
        Values for names: text
        """
        self._buttons = dict()
        super().__init__()
        layout = qtw.QVBoxLayout(self) if vertical else qtw.QHBoxLayout(self)
        for key, val in names.items():
            name = key + "_pushbutton"
            button = qtw.QPushButton(val)
            if key in tooltips:
                button.setToolTip(tooltips[key])
            layout.addWidget(button)
            self._buttons[name] = button

    def add_elements_to_dict(self, user_data_widgets: dict):
        for name, button in self._buttons.items():
            user_data_widgets[name] = button

    def buttons(self) -> dict:
        return self._buttons

class PushButton(qtw.QPushButton):
    def __init__(self, name, label, tooltip):
        self._name = name
        super().__init__()
        self.setText(label)
        if tooltip:
            self.setToolTip(tooltip)

    def add_elements_to_dict(self, user_data_widgets: dict):
        user_data_widgets[self._name] = self

class ChoiceButtonGroup(qtw.QWidget):
    def __init__(self, group_name, names: dict, tooltips: dict, vertical=False):
        """keys for names: integers
        values for names: text
        """
        self._name = group_name
        super().__init__()
        self.button_group = qtw.QButtonGroup()
        layout = qtw.QVBoxLayout(self) if vertical else qtw.QHBoxLayout(self)
        for key, button_name in names.items():
            button = qtw.QRadioButton(button_name)
            if key in tooltips:
                button.setToolTip(tooltips[key])
            self.button_group.addButton(button, key)
            layout.addWidget(button)
        self.button_group.buttons()[0].setChecked(True)

    def add_elements_to_dict(self, user_data_widgets: dict):
        user_data_widgets[self._name] = self.button_group

    def buttons(self) -> list:
        return self.button_group.buttons()


class ComboBox(qtw.QComboBox):
    def __init__(self, name,
                 tooltip,
                 items: list,
                 ):
        self._name = name
        super().__init__()
        if tooltip:
            self.setToolTip(tooltip)
        for item in items:
            self.addItem(*item)  # tuple (text, userData), therefore *

    def add_elements_to_dict(self, user_data_widgets: dict):
        user_data_widgets[self._name] = self


class SubForm(qtw.QWidget):
    def __init__(self):
        super().__init__()
        self._layout = qtw.QFormLayout(self)


class UserForm(qtw.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._layout = qtw.QFormLayout(self)  # the argument makes already here the "setLayout" for the widget
        self.interactable_widgets = dict()  # this is a dict of objects that user give input in, such as a 
        # textbox or a checkmark. key is the name of the parameter. value is the widget itself.
        # buttons are also in here although they do not store a value.

    def add_row(self, obj, description=None, into_form=None):
        if into_form:
            layout = into_form.layout()
        else:
            layout = self.layout()

        if description:
            layout.addRow(description, obj)
        else:
            layout.addRow(obj)

        if hasattr(obj, "add_elements_to_dict"):
            obj.add_elements_to_dict(self.interactable_widgets)

    def update_form_values(self, values_new: dict):
        # Update the widget values from a dictionary

        # list of widgets that are not mentioned in argument values_new
        no_dict_key_for_widget = set(
            [key for key, obj in self.interactable_widgets.items() if not isinstance(obj, qtw.QAbstractButton)]
            )  # works???????????????????????
        no_widget_for_dict_key = set()
        for key, value_new in values_new.items():
            obj = self.interactable_widgets[key]

            if isinstance(obj, qtw.QComboBox):
                assert isinstance(value_new, dict)
                existing_item_index = obj.findText(value_new["current_text"])

                logger.debug("Items in widget: " + str([(obj.itemText(i), obj.itemData(i)) for i in range(obj.count())]))
                logger.debug("New text: " + str(value_new))
                logger.debug("Found in index: " + str(existing_item_index))

                if existing_item_index == -1:  # the combobox does not yet have this stored option
                    
                    # clear the combobox
                    obj.clear()
                    # add all options from storage
                    items = value_new.get("items", [])
                    current_text = value_new["current_text"]
                    current_data = value_new.get("current_data", None)

                    # if items are available in loaded values
                    if items:
                        for item in items:
                            obj.addItem(*item)

                        # if "current_index" not in value_new.keys():
                        #     # to cover cases where index was not stored. for backwards compatibility.
                        obj.setCurrentText(current_text)
                        # else:
                        #     obj.setCurrentIndex(value_new["current_index"])

                    # otherwise add only the item of last selection
                    else:
                        obj.addItem(current_text, current_data)
                        obj.setCurrentIndex(0)

                else:  # the combobox already has this name as an item
                    # we just set to the correct one
                    obj.setCurrentIndex(existing_item_index)
                    # # also set its data again just in case
                    # obj.setItemData(existing_item_index, value_new.get("current_data", None))

            elif isinstance(obj, qtw.QLineEdit):
                assert isinstance(value_new, str)
                obj.setText(value_new)

            elif isinstance(obj, qtw.QPushButton):
                raise TypeError(
                    f"Don't know what to do with value_new={value_new} for button {key}.")

            elif isinstance(obj, qtw.QButtonGroup):
                obj.button(value_new).setChecked(True)

            elif isinstance(obj, qtw.QCheckBox):
                obj.setChecked(value_new)

            elif type(value_new) in [int, float]:
                obj.setValue(value_new / obj.coeff_for_SI)

            else:
                obj.setValue(value_new)

            # finally
            no_dict_key_for_widget.discard(key)

        if no_widget_for_dict_key | no_dict_key_for_widget:
            raise ValueError(f"No data found to update the widget(s): '{no_dict_key_for_widget}'"
                             )

    def get_value(self, name: str):
        obj = self.interactable_widgets.get(name, None)
        if obj is None:
            raise ValueError(f"Object with name '{name}' not found.")

        if isinstance(obj, qtw.QAbstractButton):
            return

        if isinstance(obj, qtw.QComboBox):
            obj_value = dict()
            obj_value["current_index"] = obj.currentIndex()
            obj_value["current_data"] = obj.currentData()
            obj_value["current_text"] = obj.currentText()

            obj_value["items"] = list()
            for i_item in range(obj.count()):
                item_text = obj.itemText(i_item)
                item_data = obj.itemData(i_item)
                obj_value["items"].append((item_text, item_data))  # index 0 is name, 1 is data

        elif isinstance(obj, qtw.QLineEdit):
            obj_value = obj.text()

        elif isinstance(obj, qtw.QButtonGroup):
            obj_value = obj.checkedId()

        elif isinstance(obj, qtw.QCheckBox):
            obj_value = obj.isChecked()

        else:
            if obj.coeff_for_SI:
                obj_value = obj.value() * obj.coeff_for_SI
            else:
                obj_value = obj.value()

        return obj_value

    def get_form_values(self) -> dict:
        """Collects all values from the widgets in the form that have user input values.
        Puts them in a dictionary and returns.
        """
        values = {}
        for key in self.interactable_widgets.keys():

            obj_value = self.get_value(key)
            if obj_value is None:
                raise ValueError(f"Received data with type 'None' from object '{key}' in form.")
            
            values[key] = obj_value

        return values


class SoundEngine(qtc.QObject):
    def __init__(self, settings):
        super().__init__()
        self.app_settings = settings
        self.verify_stream()

    def verify_stream(self):
        self.FS = sd.query_devices(device=sd.default.device, kind='output',
                                   )["default_samplerate"]
        # needs to be improved and tested for device changes!
        if not hasattr(self, "stream"):
            self.stream = sd.OutputStream(samplerate=self.FS, channels=2)
        if not self.stream.active:
            self.stream.start()

    @qtc.Slot(float, float, float)
    def beep(self, A, T, freq):
        self.verify_stream()
        t = np.arange(T * self.FS) / self.FS
        y = A * np.sin(t * 2 * np.pi * freq)
        fade_window = signal_tools.make_fade_window_n(1, 0, len(y), fade_start_end_idx=(len(y) - int(self.FS / 10), len(y)))
        y = y * fade_window
        pad = np.zeros(int(self.FS / 10))
        y = np.concatenate([y, pad])
        y = np.tile(y, self.stream.channels)
        y = y.reshape((len(y) // self.stream.channels,
                      self.stream.channels), order='F').astype(self.stream.dtype)
        y = np.ascontiguousarray(y, self.stream.dtype)
        self.stream.write(y)

    @qtc.Slot()
    def good_beep(self):
        self.beep(self.app_settings.A_beep / 2, 0.1, 587.3)

    @qtc.Slot()
    def bad_beep(self):
        self.beep(self.app_settings.A_beep, 0.1, 293.7)

    @qtc.Slot()
    def release_all(self):
        self.stream.stop(ignore_errors=True)

class ResultTextBox(qtw.QDialog):
    def __init__(self, title, result_text, monospace=True, parent=None, markdown=False):
        super().__init__(parent=parent)
        # self.setWindowModality(qtc.Qt.WindowModality.NonModal)

        layout = qtw.QVBoxLayout(self)
        self.setWindowTitle(title)
        self.setMinimumSize(700, 480)
        text_box = qtw.QTextEdit()
        text_box.setReadOnly(True)
        if markdown is False:
            text_box.setText(result_text)
            if monospace:
                family = "Monospace" if "Monospace" in qtg.QFontDatabase.families() else "Consolas"
                font = text_box.font()
                font.setFamily(family)
                text_box.setFont(font)
        else:
            text_box.setMarkdown(result_text)
            if monospace is True:
                logging.warning("Ignoring monospace argument when using Markdown.")

        layout.addWidget(text_box)

        # ---- Buttons
        button_group = PushButtonGroup({"ok": "OK",
                                            },
                                           {},
                                           )
        button_group.buttons()["ok_pushbutton"].setDefault(True)
        layout.addWidget(button_group)

        # ---- Connections
        button_group.buttons()["ok_pushbutton"].clicked.connect(
            self.accept)

class ErrorHandlerDeveloper:
    def __init__(self, app, logger):
        self.app = app
    
    def excepthook(self, etype, value, tb):
        error_msg_developer = ''.join(traceback.format_exception(etype, value, tb))
        message_box = qtw.QMessageBox(qtw.QMessageBox.Warning,
                                      "Error    :(",
                                      error_msg_developer +
                                      "\n\nThis event may be logged unless ignore is chosen.",
                                      )
        message_box.addButton(qtw.QMessageBox.Ignore)
        close_button = message_box.addButton(qtw.QMessageBox.Close)
    
        message_box.setEscapeButton(qtw.QMessageBox.Ignore)
        message_box.setDefaultButton(qtw.QMessageBox.Close)
    
        close_button.clicked.connect(logger.warning(error_msg_developer))
    
        message_box.exec()

class ErrorHandlerUser:
    def __init__(self, app, logger):
        self.app = app
    
    def excepthook(self, etype, value, tb):
        error_msg_developer = ''.join(traceback.format_exception(etype, value, tb))
        error_info = traceback.format_exception(etype, value, tb)
        
        if isinstance(error_info, list) and len(error_info) > 2:
            error_msg_short = error_info[-2] + "\n\n" + error_info[-1]
            # bad solution
        else:
            error_msg_short = error_info
            
        message_box = qtw.QMessageBox(qtw.QMessageBox.Warning,
                                      "Error    :(",
                                      error_msg_short +
                                      "\n\nThis event may be logged unless ignore is chosen.",
                                      )
        message_box.addButton(qtw.QMessageBox.Ignore)
        close_button = message_box.addButton(qtw.QMessageBox.Close)
    
        message_box.setEscapeButton(qtw.QMessageBox.Ignore)
        message_box.setDefaultButton(qtw.QMessageBox.Close)
    
        close_button.clicked.connect(logger.warning(error_msg_developer))
    
        message_box.exec()

class LoadSaveEngine:
    """
    Data to save for the graph in general:
        Plot title: sget_title
        Plot x label: sget_xlabel
        Plot y label: sget_ylabel
        x linear/log: sget_xscale
        y linear/log: sget_yscale

    Data to save per curve item:
        Curve object in CurveAnalyze.curves
        Line2D:
            style: sget_linestyle
            draw style: sget_drawstyle
            width: sget_linewidth
            color: sget_color
        Line2D marker:
            style: sget_marker
            size: sget_markersize
            face col: sget_markerfacecolor
            edge col: sget_markeredgecolor
    """

    def collect_graph_info(self, ax):
        graph_info = {"title": ax.get_title(),
                      "xlabel": ax.get_xlabel(),
                      "ylabel": ax.get_ylabel(),
                      "xscale": ax.get_xscale(),
                      "yscale": ax.get_yscale(),
                      }
        return graph_info

    def collect_line2d_info(self, line):
        line_info = {"style": line.get_style(),
                     "drawstyle": line.get_drawstyle(),
                     "width": line.get_width(),
                     "color": line.get_color(),
                     "marker": line.get_marker(),
                     "markersize": line.get_markersize(),
                     "markerfacecolor": line.get_markerfacecolor(),
                     "markeredgecolor": line.get_markeredgecolor(),
                     }
        return line_info

    def collect_curve_info(self, curve):
        curve_info = {"visible": curve.is_visible(),
                      "identification": curve._identification,
                      "x": tuple(curve.get_x()),
                      "y": tuple(curve.get_y()),
                      }
        return curve_info

    def collect_all_info(self, ax, lines, curves):
        graph_info = self.collect_graph_info(ax)
        lines_info = []
        curves_info = []
        for line, curve in zip(lines, curves):
            lines_info.append(self.collect_line2d_info(line))
            curves_info.append(self.collect_curve_info(curve))

        package = pickle.dumps([graph_info, lines_info, curves_info], protocol=5)
        return package
