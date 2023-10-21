import sys
import numpy as np
from functools import partial
from generictools import signal_tools
from functools import lru_cache

from PySide6 import QtCore as qtc
from matplotlib.backends.qt_compat import QtWidgets as qtw
from matplotlib.backends.backend_qtagg import (
    FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
plt.rcParams["figure.constrained_layout.h_pad"] = 0.3
plt.rcParams["figure.constrained_layout.w_pad"] = 0.4
import time

# https://matplotlib.org/stable/gallery/user_interfaces/embedding_in_qt_sgskip.html


import logging
if __name__ == "__main__":
    logger = logging.getLogger(__name__)
else:
    logging.basicConfig(level=logging.WARNING)
    logger = logging.getLogger()

class MatplotlibWidget(qtw.QWidget):
    signal_is_reference_curve_active = qtc.Signal(bool)
    signal_good_beep = qtc.Signal()
    signal_bad_beep = qtc.Signal()
    available_styles = list(plt.style.available)

    def __init__(self, settings):
        self.app_settings = settings
        super().__init__()
        layout = qtw.QVBoxLayout(self)
        self._ref_index_and_curve = None
        self._qlistwidget_indexes_of_lines = np.array([], dtype=int)

        # ---- Set the desired style
        desired_style = self.app_settings.matplotlib_style
        if desired_style in plt.style.available:
            plt.style.use(desired_style)
        else:
            raise KeyError(f"Desired style '{desired_style}' not available.")

        # ---- Create the figure and axes
        fig = Figure()
        fig.set_layout_engine("constrained")
        self.canvas = FigureCanvas(fig)
        # Ideally one would use self.addToolBar here, but it is slightly
        # incompatible between PyQt6 and other bindings, so we just add the
        # toolbar as a plain widget instead.
        self.navigation_toolbar = NavigationToolbar(self.canvas, self)
        layout.addWidget(self.navigation_toolbar)
        # print(self.navigation_toolbar.layout().itemAt(3).tooltip())  - test access to buttons in toolbar
        layout.addWidget(self.canvas)

        self.ax = self.canvas.figure.subplots()
        self.set_grid_type()

        # https://matplotlib.org/stable/api/_as_gen/matplotlib._lines.line2d.html

    @qtc.Slot()
    def set_grid_type(self):
        self.ax.grid(visible=False, which="both", axis='both')

        if self.app_settings.graph_grids == "default":
            visible = plt.rcParams["axes.grid"]
            axis = plt.rcParams["axes.grid.axis"]
            which = plt.rcParams["axes.grid.which"]
            self.ax.grid(visible=visible, which=which, axis=axis)

        else:
            if "major" in self.app_settings.graph_grids:
                self.ax.grid(visible=True, which="major", axis='both')
            if "minor" in self.app_settings.graph_grids:
                self.ax.grid(visible=True, which="minor", axis='both')

    @qtc.Slot()
    def update_figure(self, recalculate_limits=True, update_legend=True):
        start_time = time.perf_counter()
        
        if recalculate_limits:
            y_arrays = [line.get_ydata() for line in self.ax.get_lines()]
            y_min_max = signal_tools.calculate_graph_limits(y_arrays, multiple=5, clearance_up_down=(2, 1))
            self.ax.set_ylim(y_min_max)

        if update_legend:
            # Update zorders
            n_lines = self._qlistwidget_indexes_of_lines.size
            for i, line in enumerate(self.get_lines_in_user_defined_order()):
                hide_offset = -1_000_000 if line.get_label()[0] == "_" else 0
                line.set_zorder(n_lines - i + hide_offset)

            if self.ax.has_data() and self.app_settings.show_legend:
                self._show_legend_ordered()
            else:
                self.ax.legend().remove()

        self.canvas.draw()
        logger.info(f"Graph updated. {len(self.ax.get_lines())} lines. Took {(time.perf_counter()-start_time)*1000:.4g}ms.")

    @qtc.Slot()
    def add_line2d(self, i_insert: int, label: str, data: tuple, update_figure=True, line2d_kwargs={}):
        # Make sure reference curve position stored stays correct
        if self._ref_index_and_curve and i_insert <= self._ref_index_and_curve[0]:
            self._ref_index_and_curve[0] += 1

        # Modify curve before pasting if graph has a reference curve
        x_in, y_in = data
        if self._ref_index_and_curve:
            reference_curve_x, reference_curve_y = self._ref_index_and_curve[1].get_xy()
            ref_y_intp = self._reference_curve_interpolated(tuple(x_in), tuple(reference_curve_x), tuple(reference_curve_y))
            y_in = y_in - ref_y_intp

        # Paste the curve into graph
        _, = self.ax.semilogx(x_in, y_in, label=label, **line2d_kwargs)
        self._qlistwidget_indexes_of_lines[self._qlistwidget_indexes_of_lines >= i_insert] += 1
        self._qlistwidget_indexes_of_lines = np.append(self._qlistwidget_indexes_of_lines, i_insert)

        if update_figure:
            self.update_figure()

    @qtc.Slot(list)
    def remove_line2d(self, ix: list):
        if self._ref_index_and_curve:
            if self._ref_index_and_curve[0] in ix:
                self.toggle_reference_curve(None)
            else:
                self._ref_index_and_curve[0] -= sum(i < self._ref_index_and_curve[0] for i in ix)  # summing booleans

        lines_in_user_defined_order = self.get_lines_in_user_defined_order()
        for index_to_remove in sorted(ix, reverse=True):
            lines_in_user_defined_order[index_to_remove].remove()
            self._qlistwidget_indexes_of_lines = \
                self._qlistwidget_indexes_of_lines[np.nonzero(self._qlistwidget_indexes_of_lines != index_to_remove)]
            self._qlistwidget_indexes_of_lines[self._qlistwidget_indexes_of_lines > index_to_remove] -= 1

        if ix:
            self.update_figure()
            # self.signal_good_beep.emit()

    @lru_cache
    def _reference_curve_interpolated(self, x:tuple, reference_curve_x:tuple, reference_curve_y:tuple):
        return np.interp(np.log(x), np.log(reference_curve_x), reference_curve_y, left=np.nan, right=np.nan)
         
    @qtc.Slot()
    def toggle_reference_curve(self, ref_index_and_curve: (tuple, None)):
        if ref_index_and_curve is not None:
            # new ref. curve introduced
            reference_curve_x, reference_curve_y = ref_index_and_curve[1].get_xy()

            self._ref_index_and_curve = ref_index_and_curve
            for line2d in self.ax.get_lines():
                x, y = line2d.get_xdata(), line2d.get_ydata()
                ref_y_intp = self._reference_curve_interpolated(tuple(x), tuple(reference_curve_x), tuple(reference_curve_y))
                line2d.set_ydata(y - ref_y_intp)

            self.hide_show_line2d({self._ref_index_and_curve[0]: False})

        elif ref_index_and_curve is None and self._ref_index_and_curve is not None:
            # there was a reference curve active and now it is deactivated.
            reference_curve_x, reference_curve_y = self._ref_index_and_curve[1].get_xy()
            for line2d in self.ax.get_lines():
                x, y = line2d.get_xdata(), line2d.get_ydata()
                ref_y_intp = self._reference_curve_interpolated(tuple(x), tuple(reference_curve_x), tuple(reference_curve_y))
                line2d.set_ydata(y + ref_y_intp)

            self.hide_show_line2d({self._ref_index_and_curve[0]: True})

            self._ref_index_and_curve = None
            
        else:
            # all other scenarios. no reference should be set.
            self._ref_index_and_curve = None

        self.signal_is_reference_curve_active.emit(self._ref_index_and_curve is not None)
        self.update_figure()

    def _get_line_indexes_in_user_defined_order(self):
        line_indexes_in_qlist_order = np.argsort(self._qlistwidget_indexes_of_lines)
        return line_indexes_in_qlist_order

    def get_lines_in_user_defined_order(self, qlist_index=None):
        if qlist_index is None:
            line_indexes_in_qlist_order = self._get_line_indexes_in_user_defined_order()
            return [self.ax.get_lines()[i] for i in line_indexes_in_qlist_order]
        else:
            graph_index = np.where(self._qlistwidget_indexes_of_lines == qlist_index)[0][0]
            return self.ax.get_lines()[graph_index]

    def _get_visible_lines_in_user_defined_order(self):
        lines_in_user_defined_order = self.get_lines_in_user_defined_order()
        return [line for line in lines_in_user_defined_order if line.get_alpha() in (None, 1)]

    def _show_legend_ordered(self):
        handles = self._get_visible_lines_in_user_defined_order()
        if self.app_settings.max_legend_size > 0:
            handles = handles[:self.app_settings.max_legend_size]

        labels = [line.get_label() for line in handles]

        if self._ref_index_and_curve:
            title = "Relative to: " + self._ref_index_and_curve[1].get_full_name()
            title = title.removesuffix(" - reference")
        else:
            title = None

        self.ax.legend(handles, labels, title=title)

    @qtc.Slot(dict)
    def change_lines_order(self, new_indexes: dict):
        # new_indexes: each key is the old location of a qlist item. value is the new location

        # Scan the whole list of lines to replace them one by one
        for line_index_in_graph in range(self._qlistwidget_indexes_of_lines.size):
            current_location_in_qlist_widget = self._qlistwidget_indexes_of_lines[line_index_in_graph]            
            new_location_in_qlist_widget = new_indexes[current_location_in_qlist_widget]
            self._qlistwidget_indexes_of_lines[line_index_in_graph] = new_location_in_qlist_widget

            # keep the reference index always correct
            if self._ref_index_and_curve and current_location_in_qlist_widget == self._ref_index_and_curve[0]:
                self._ref_index_and_curve[0] = new_location_in_qlist_widget
        
        self.update_figure(recalculate_limits=False)

    @qtc.Slot(int)
    def flash_curve(self, i: int):
        line = self.get_lines_in_user_defined_order(i)
        begin_lw = line.get_lw()
        line.set_lw(begin_lw * 2.5)
        old_alpha = line.get_alpha()
        if old_alpha:
            line.set_alpha(1)
        old_zorder = line.get_zorder()
        line.set_zorder(len(self.ax.get_lines()))

        self.update_figure(recalculate_limits=False, update_legend=False)

        timer = qtc.QTimer()
        timer.singleShot(1000, partial(self._stop_flash, line, (old_alpha, begin_lw, old_zorder)))

    def _stop_flash(self, line, old_states):
        line.set_alpha(old_states[0])
        line.set_lw(old_states[1])
        line.set_zorder(old_states[2])
        self.update_figure(recalculate_limits=False, update_legend=False)

    @qtc.Slot()
    def hide_show_line2d(self, visibility_states: dict):
        lines_in_user_defined_order = self.get_lines_in_user_defined_order()
        for i, visible in visibility_states.items():
            line = lines_in_user_defined_order[i]

            alpha = 1 if visible else 0.1
            line.set_alpha(alpha)

            if visible:
                while (label := line.get_label())[0] == "_":
                    line.set_label(label.removeprefix("_"))
            if not visible and (label := line.get_label())[0] != "_":
                line.set_label("_" + label)

        if visibility_states:
            self.update_figure(recalculate_limits=False)

    @qtc.Slot(dict)
    def update_labels(self, labels: dict):
        lines_in_user_defined_order = self.get_lines_in_user_defined_order()

        any_visible = False
        for i, label in labels.items():
            line = lines_in_user_defined_order[i]
            
            visible = line.get_alpha() in (None, 1)
            if visible:
                new_label = label
                any_visible = True
            else:
                new_label = "_" + label
            line.set_label(new_label)

        if any_visible:
            self.update_figure(recalculate_limits=False)

    @qtc.Slot()
    def reset_colors(self):
        colors = plt.rcParams["axes.prop_cycle"]()

        for line in self.get_lines_in_user_defined_order():
            line.set_color(next(colors)["color"])

        self.update_figure(recalculate_limits=False)


if __name__ == "__main__":

    if not (app := qtw.QApplication.instance()):
        app = qtw.QApplication(sys.argv)
        # there is a new recommendation with qApp but how to do the sys.argv with that?

    mw = MatplotlibWidget()

    # do a test plot
    x = 100 * 2**np.arange(stop=7, step=7 / 16)
    for i in range(1, 5):
        y = 45 + 10 * np.random.random(size=len(x))
        mw.add_line2d(i, f"Random line {i}", (x, y))

    mw.show()
    app.exec()
