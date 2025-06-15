import sys
import time
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

import matplotlib
matplotlib.rcParams['savefig.format'] = 'svg'

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

    def print_line_states(self):
        print()
        n_lines = self._qlistwidget_indexes_of_lines.size
        for i, line in enumerate(self.get_lines_in_user_defined_order()):
            print(i, line.get_label(), line.get_zorder())

    def __init__(self, settings, layout_engine="constrained"):
        self.app_settings = settings
        super().__init__()
        layout = qtw.QVBoxLayout(self)
        self._ref_index_and_curve = None
        self._qlistwidget_indexes_of_lines = np.array([], dtype=int)
        self.set_y_limits_policy(None)

        # ---- Set the desired style
        desired_style = self.app_settings.matplotlib_style
        if desired_style in plt.style.available:
            plt.style.use(desired_style)
        else:
            raise KeyError(f"Desired style '{desired_style}' not available.")

        # ---- Create the figure and axes
        fig = Figure()
        fig.set_layout_engine(layout_engine)
        self.canvas = FigureCanvas(fig)
        # Ideally one would use self.addToolBar here, but it is
        # incompatible between PyQt6 and other bindings, so we add the
        # toolbar as a plain widget instead.
        self.navigation_toolbar = NavigationToolbar(self.canvas, self)
        layout.addWidget(self.navigation_toolbar)
        # print(self.navigation_toolbar.layout().itemAt(3).tooltip())  - test access to buttons in toolbar
        layout.addWidget(self.canvas)

        self.ax = self.canvas.figure.subplots()
        self.set_grid_type()

        # https://matplotlib.org/stable/api/_as_gen/matplotlib._lines.line2d.html
        
        # Print info continuously
        # timer = qtc.QTimer(self)
        # timer.timeout.connect(self.print_line_states)
        # timer.start(2000)

    @qtc.Slot()
    def set_grid_type(self):
        self.ax.grid(visible=False, which="both", axis='both')

        if self.app_settings.graph_grids == "default":
            visible = plt.rcParams["axes.grid"]
            axis = plt.rcParams["axes.grid.axis"]
            which = plt.rcParams["axes.grid.which"]
            self.ax.grid(visible=visible, which=which, axis=axis)

        else:
            if "ajor" in self.app_settings.graph_grids:
                self.ax.grid(visible=True, which="major", axis='both')
            if "inor" in self.app_settings.graph_grids:
                self.ax.grid(visible=True, which="minor", axis='both')
    
    def set_y_limits_policy(self, policy_name, **kwargs):
        self.y_limits_policy = {"name": policy_name,
                                "kwargs": kwargs,
                                }

    def set_title(self, title):
        self.ax.set_title(title)

    @qtc.Slot()
    def update_figure(self, recalculate_limits=True, update_legend=True):
        start_time = time.perf_counter()

        if update_legend:
            # print("----Start update legend")
            
            # Update zorders
            n_lines = self._qlistwidget_indexes_of_lines.size
            for i, line in enumerate(self.get_lines_in_user_defined_order()):
                # print(i, line.get_label(), line.get_zorder())
                # print("Settings zorders")
                zorder_offset = -1_000_000 if line.get_label()[0] == "_" else 0
                line.set_zorder(n_lines - i + zorder_offset)

            if self.ax.has_data() and getattr(self.app_settings, "show_legend", True):
              # print("Updating legend.")
              self._create_ordered_legend()
              # self.ax.draw_artist(legend)

            else:
                # print("Removing legend")
                self.ax.legend().remove()
                # print("----End update legend")

        if recalculate_limits:
            self.ax.yaxis.set_major_locator(plt.AutoLocator())
            self.ax.relim()


            if self.y_limits_policy["name"] is None:
                self.ax.autoscale(enable=True, axis="both")

            elif self.y_limits_policy["name"] == "SPL":
                y_arrays = [line.get_ydata() for line in self.ax.get_lines() if "Xpeak limited" not in line.get_label()]
                if y_arrays:
                    y_max = max([max(arr) for arr in y_arrays])
                    y_min = min([min(arr) for arr in y_arrays])
                    graph_max = 5 * np.ceil((y_max + 3) / 5)
                    graph_range = 5 * np.floor(min(50, max(30, graph_max - y_min)) / 5)
                    self.ax.set_ylim((graph_max - graph_range, graph_max))

            elif self.y_limits_policy["name"] == "impedance":
                y_arrays = [line.get_ydata() for line in self.ax.get_lines()]
                if y_arrays:
                    y_max = max([max(arr) for arr in y_arrays])
                    graph_max = 5 * np.ceil((y_max + 2) / 5)
                    self.ax.set_ylim((0, graph_max))

            elif self.y_limits_policy["name"] == "phase":
                y_min_max = (-180, 180)
                self.ax.set_yticks(range(-180, 180+1, 90))
                self.ax.set_ylim(y_min_max)

            elif self.y_limits_policy["name"] == "fixed":
                kwargs = self.y_limits_policy["kwargs"]
                y_min_max = (kwargs["min"], kwargs["max"])
                self.ax.set_ylim(y_min_max)

        self.canvas.draw_idle()
        logger.debug(f"Graph updated. {len(self.ax.get_lines())} lines."
                     f"\nTook {(time.perf_counter()-start_time)*1000:.4g}ms.")

    def _create_ordered_legend(self):
        handles = self.get_visible_lines_in_user_defined_order()
        if self.app_settings.max_legend_size > 0:
            handles = handles[:self.app_settings.max_legend_size]

        # print([(line.get_label(), line.get_zorder()) for line in handles])

        # labels = [line.get_label() for line in handles]

        if self._ref_index_and_curve:
            title = "Relative to: " + self._ref_index_and_curve[1].get_full_name()
            title = title.removesuffix(" - reference")
        else:
            title = None

        if handles:
            self.ax.legend(handles=handles, title=title)
        else:
            self.ax.legend.remove()

    @qtc.Slot()
    def add_line2d(self, i_insert: int, label: str, data: tuple, update_figure=True, line2d_kwargs={}):
        # Make sure reference curve position stored stays correct
        if self._ref_index_and_curve and i_insert <= self._ref_index_and_curve[0]:
            self._ref_index_and_curve[0] += 1

        # Modify curve before pasting if graph has a reference curve
        x_in, y_in = data
        if self._ref_index_and_curve:
            reference_curve_x, reference_curve_y = self._ref_index_and_curve[1].get_xy()
            ref_y_intp = self._reference_curve_interpolated(tuple(x_in),
                                                            tuple(reference_curve_x),
                                                            tuple(reference_curve_y),
                                                            )
            y_in = y_in - ref_y_intp

        # Paste the curve into graph
        _, = self.ax.semilogx(x_in, y_in, label=label, **line2d_kwargs)
        self._qlistwidget_indexes_of_lines[self._qlistwidget_indexes_of_lines >= i_insert] += 1
        self._qlistwidget_indexes_of_lines = np.append(self._qlistwidget_indexes_of_lines, i_insert)

        if update_figure:
            self.update_figure()

    @qtc.Slot()
    def clear_graph(self):
        ix_to_remove = self._get_line_indexes_in_user_defined_order()
        self.remove_multiple_line2d(ix_to_remove)
        self.ax.clear()
        self.canvas.toolbar.update()  # resets the toolbar
        # necessary to reset the history for home and back/forward buttons
        # self.ax.set_prop_cycle(None)  # ax.clear() made this redundant

    @qtc.Slot(list)
    def remove_multiple_line2d(self, ix: list):
        if self._ref_index_and_curve:
            if self._ref_index_and_curve[0] in ix:
                self.toggle_reference_curve(None)
            else:
                self._ref_index_and_curve[0] -= sum(i < self._ref_index_and_curve[0] for i in ix)
                # summing booleans

        lines_in_user_defined_order = self.get_lines_in_user_defined_order()
        for index_to_remove in sorted(ix, reverse=True):
            lines_in_user_defined_order[index_to_remove].remove()
            self._qlistwidget_indexes_of_lines = \
                self._qlistwidget_indexes_of_lines[
                    np.nonzero(self._qlistwidget_indexes_of_lines != index_to_remove)
                    ]
            self._qlistwidget_indexes_of_lines[self._qlistwidget_indexes_of_lines > index_to_remove] -= 1

        if len(ix) > 0:
            self.update_figure()

    @lru_cache
    def _reference_curve_interpolated(self, x: tuple, reference_curve_x: tuple, reference_curve_y: tuple):
        return np.interp(np.log(x), np.log(reference_curve_x), reference_curve_y, left=np.nan, right=np.nan)

    @qtc.Slot()
    def toggle_reference_curve(self, ref_index_and_curve: (tuple, None)):
        # ref_index_and_curve: [index, curve] or None
        if ref_index_and_curve is not None:
            # new ref. curve introduced
            reference_curve_x, reference_curve_y = ref_index_and_curve[1].get_xy()

            self._ref_index_and_curve = ref_index_and_curve
            for line2d in self.ax.get_lines():
                x, y = line2d.get_xdata(), line2d.get_ydata()
                ref_y_intp = self._reference_curve_interpolated(tuple(x),
                                                                tuple(reference_curve_x),
                                                                tuple(reference_curve_y),
                                                                )
                line2d.set_ydata(y - ref_y_intp)

            self.update_labels_and_visibilities({self._ref_index_and_curve[0]: (None, False)})

        elif ref_index_and_curve is None and self._ref_index_and_curve is not None:
            # there was a reference curve active and now it is deactivated.
            reference_curve_x, reference_curve_y = self._ref_index_and_curve[1].get_xy()
            for line2d in self.ax.get_lines():
                x, y = line2d.get_xdata(), line2d.get_ydata()
                ref_y_intp = self._reference_curve_interpolated(tuple(x),
                                                                tuple(reference_curve_x),
                                                                tuple(reference_curve_y),
                                                                )
                line2d.set_ydata(y + ref_y_intp)

            self.update_labels_and_visibilities({self._ref_index_and_curve[0]: (None,
                                                                  self._ref_index_and_curve[1].is_visible()
                                                                  )
                                   })

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

    def get_visible_lines_in_user_defined_order(self):
        lines_in_user_defined_order = self.get_lines_in_user_defined_order()
        return [line for line in lines_in_user_defined_order if line.get_alpha() in (None, 1)]

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

        self.ax.draw_artist(line)
        self.canvas.draw_idle()

        def stop_flash(self, line, old_states):
            line.set_alpha(old_states[0])
            line.set_lw(old_states[1])
            line.set_zorder(old_states[2])
    
            self.ax.draw_artist(line)
            self.canvas.draw_idle()


        timer = qtc.QTimer()
        timer.singleShot(3000, partial(stop_flash, self, line, (old_alpha, begin_lw, old_zorder)))

    @qtc.Slot(dict)
    def update_labels_and_visibilities(self, label_and_visibility:dict, update_figure=True):
        # label_and_visibility
        # keys are index of line in user defined order
        # contains tuples as values
        # first value is label. give label without "_" prefixes
        # second value is visibility. give boolean
        
        lines_in_user_defined_order = self.get_lines_in_user_defined_order()
        for i, (new_label, visible) in label_and_visibility.items():
            
            line = lines_in_user_defined_order[i]
            # print(line.get_label(), i, new_label, visible)

            if new_label is None:
                new_label = line.get_label()

            while new_label[0] == "_":
                new_label = new_label.removeprefix("_")

            if visible is True:
                line.set_alpha(1)
                line.set_label(new_label)

            elif visible is False:
                line.set_alpha(0.1)
                line.set_label("_" + new_label)
            else:
                raise ValueError("Must remind the visibility due to Matplotlib canvas"
                                 " tending to reset it on its own.")
            # self.ax.draw_artist(line)  # optimization here???

        if label_and_visibility and update_figure:
            self.update_figure(recalculate_limits=False, update_legend=True)

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
