import sys
import time
import numpy as np
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
    signal_reference_curve_activated = qtc.Signal(int)
    signal_reference_curve_deactivated = qtc.Signal()
    signal_reference_curve_failed = qtc.Signal(str)
    signal_good_beep = qtc.Signal()
    signal_bad_beep = qtc.Signal()
    available_styles = list(plt.style.available)

    def print_line_states(self):
        print()
        n_lines = self._qlistwidget_indexes_of_lines.size
        for i, line in enumerate(self.get_lines_in_qlist_order()):
            print(i, line.get_label(), line.get_zorder())

    def __init__(self, settings, layout_engine="constrained"):
        self.app_settings = settings
        super().__init__()
        layout = qtw.QVBoxLayout(self)
        self._ref_index_x_y = None
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
        self._setup_grid()

        # https://matplotlib.org/stable/api/_as_gen/matplotlib._lines.line2d.html
        
        # Print info continuously
        # timer = qtc.QTimer(self)
        # timer.timeout.connect(self.print_line_states)
        # timer.start(2000)

    @qtc.Slot()
    def _setup_grid(self):
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
            default_line_width = plt.rcParams['lines.linewidth']

            # Update zorders and highlights
            n_lines = self._qlistwidget_indexes_of_lines.size
            for i, line in enumerate(self.get_lines_in_qlist_order()):

                # 4 states exist
                # reference, 0.1 alpha, not shown on legend
                # highlighted, 1.0 alpha
                # normal shown, 0.9 alpha
                # hidden, 0.1 alpha, not shown on legend

                # reference or hidden
                if line.get_label()[0] == "_" or self._ref_index_x_y is not None and self._ref_index_x_y[0] == i:
                    zorder_offset = -1_000_000

                # highlighted
                elif line.get_alpha() == 1.0:
                    zorder_offset = 1_000_000

                # normal
                else:
                    zorder_offset = 0

                line.set_zorder(n_lines - i + zorder_offset)

            if self.ax.has_data() and getattr(self.app_settings, "show_legend", True):
                self._place_ordered_legend()
            elif legend := self.ax.get_legend():
                legend.remove()

        if recalculate_limits:
            self.ax.yaxis.set_major_locator(plt.AutoLocator())
            self.ax.relim()


            if self.y_limits_policy["name"] is None:
                self.ax.autoscale(enable=True, axis="both")

            if self.y_limits_policy["name"] == "reference_curve":
                y_max = np.max([np.max(np.abs(line.get_ydata())) for line in self.ax.get_lines()])
                graph_max = max(5 * np.ceil((y_max - 2) / 5), 1)
                self.ax.set_ylim((-graph_max, graph_max))

            elif self.y_limits_policy["name"] == "SPL":
                y_arrays = [line.get_ydata() for line in self.ax.get_lines() if "Xpeak limited" not in line.get_label()]
                if y_arrays:
                    y_max = np.max([max(arr) for arr in y_arrays])
                    y_min = np.min([min(arr) for arr in y_arrays])
                    graph_max = 5 * np.ceil((y_max + 3) / 5)
                    graph_range = 5 * np.ceil(min(45, max(20, graph_max - y_min)) / 5)
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

        self._setup_grid()
        self.canvas.draw_idle()
        logger.debug(f"Graph updated. {len(self.ax.get_lines())} lines."
                     f"\nTook {(time.perf_counter()-start_time)*1000:.4g}ms.")

    def _place_ordered_legend(self):
        handles = self.get_visible_lines_in_qlist_order()

        if self._ref_index_x_y:
            i_ref_curve = self._ref_index_x_y[0]
            ref_line2D = self.get_line_in_qlist_order(i_ref_curve)

            title = "Relative to: " + ref_line2D.get_label().removeprefix("_")
            title = title.removesuffix(" - reference")
        else:
            title = None

        max_legend_size = getattr(self.app_settings, "max_legend_size", 0)
        if len(handles) > 0:
            if max_legend_size > 0:
                handles = handles[:self.app_settings.max_legend_size]
            self.ax.legend(handles=handles, title=title)

    @qtc.Slot()
    def add_line2d(self, i_insert: int, label: str, data: tuple, update_figure=True, line2d_kwargs={}):
        # Make sure reference curve position stored stays correct
        if self._ref_index_x_y and i_insert <= self._ref_index_x_y[0]:
            self._ref_index_x_y[0] += 1

        # Modify curve before pasting if graph has a reference curve
        x_in, y_in = data
        if self._ref_index_x_y:
            reference_curve_x, reference_curve_y = self._ref_index_x_y[1:3]
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
        ix_to_remove = self._get_line_indexes_in_qlist_order()
        self.remove_multiple_line2d(ix_to_remove)
        self.ax.clear()
        self.canvas.toolbar.update()  # resets the toolbar
        # necessary to reset the history for home and back/forward buttons
        # self.ax.set_prop_cycle(None)  # ax.clear() made this redundant

    @qtc.Slot(list)
    def remove_multiple_line2d(self, ix: list):
        if self._ref_index_x_y:
            if self._ref_index_x_y[0] in ix:
                self.deactivate_reference_curve()
            else:
                self._ref_index_x_y[0] -= sum(i < self._ref_index_x_y[0] for i in ix)
                # summing booleans

        lines_in_qlist_order = self.get_lines_in_qlist_order()
        for index_to_remove in sorted(ix, reverse=True):
            lines_in_qlist_order[index_to_remove].remove()
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
    def activate_reference_curve(self, i_ref_curve: int):
        try:
            if self._ref_index_x_y is not None:
                raise RuntimeError("There is already an active reference curve. Deactivate that one first.")

            ref_curve = self.get_line_in_qlist_order(i_ref_curve)
            ref_x, ref_y = ref_curve.get_xdata(), ref_curve.get_ydata()

            # # Check if reference curve covers the whole frequency range
            # current_curves_x_arrays = [line2d.get_xdata() for line2d in self.ax.get_lines()]
            # x_min_among_current_curves = min(x[0] for x in current_curves_x_arrays)
            # x_max_among_current_curves = max(x[-1] for x in current_curves_x_arrays)
            # if x_min_among_current_curves < ref_x[0] or \
            #     x_max_among_current_curves > ref_x[-1]:
            #     raise RuntimeError(f"Reference curve doesn't cover the whole frequency range of"
            #                        f" ({x_min_among_current_curves:.5g} - {x_max_among_current_curves:.5g}) Hz"
            #                        )

            for line2d in self.ax.get_lines():
                x, y = line2d.get_xdata(), line2d.get_ydata()
                line2d._original_xy = (x, y)  # to be able to revert back
                ref_y_intp = self._reference_curve_interpolated(tuple(x),
                                                                tuple(ref_x),
                                                                tuple(ref_y),
                                                                )
                new_xy = np.array([x, (y - ref_y_intp)])
                mask = ~np.isnan(new_xy[1])
                new_xy = new_xy[:, mask]

                line2d.set_xdata(new_xy[0])
                line2d.set_ydata(new_xy[1])

            self._ref_index_x_y = [i_ref_curve, ref_x, ref_y]
            self.set_y_limits_policy("reference_curve")
            self.update_figure()
            self.signal_reference_curve_activated.emit(i_ref_curve)
        except RuntimeError as e:
            self.signal_reference_curve_failed.emit(str(e))

    @qtc.Slot()
    def deactivate_reference_curve(self):
        try:
            if self._ref_index_x_y is None:
                raise RuntimeError("There is no active reference curve. Nothing to deactivate.")

            # _, ref_x, ref_y = self._ref_index_x_y


            for line2d in self.ax.get_lines():
                x, y = line2d._original_xy
                line2d.set_xdata(x)
                line2d.set_ydata(y)
                # x, y = line2d.get_xdata(), line2d.get_ydata()
                # ref_y_intp = self._reference_curve_interpolated(tuple(x),
                #                                                 tuple(ref_x),
                #                                                 tuple(ref_y),
                #                                                 )
                # line2d.set_ydata(y + ref_y_intp)

            self._ref_index_x_y = None
            self.set_y_limits_policy("SPL")
            self.update_figure()
            self.signal_reference_curve_deactivated.emit()
        except RuntimeError as e:
            self.signal_reference_curve_failed.emit(str(e))

    def _get_line_indexes_in_qlist_order(self):
        """
        Line2D's in matplotlib graph are not sorted in the same order with curves in Qlist widget.
        This function returns the Qlist positions of each line2D as a list.
        """
        line_indexes_in_qlist_order = np.argsort(self._qlistwidget_indexes_of_lines)
        return line_indexes_in_qlist_order

    def get_line_in_qlist_order(self, qlist_index):
        """
        Line2D's in matplotlib graph are not sorted in the same order with curves in Qlist widget.
        This function returns the line2D at a certain location on the Qlist widget.
        """
        graph_index = np.where(self._qlistwidget_indexes_of_lines == qlist_index)[0][0]
        return self.ax.get_lines()[graph_index]

    def get_lines_in_qlist_order(self):
        """
        Line2D's in matplotlib graph are not sorted in the same order with curves in Qlist widget.
        This function returns each line2D as a list, ordered as in Qlist widget.
        """
        line_indexes_in_qlist_order = self._get_line_indexes_in_qlist_order()
        return [self.ax.get_lines()[i] for i in line_indexes_in_qlist_order]

    def get_visible_lines_in_qlist_order(self):
        """
        Same with get_lines_in_qlist_order, but return only visible lines.
        """
        lines_in_qlist_order = self.get_lines_in_qlist_order()
        return [line for line in lines_in_qlist_order if line.get_alpha() != 0.1]

    @qtc.Slot(dict)
    def change_lines_order(self, new_indexes: dict):
        # Scan the whole list of lines to replace them one by one
        for line_index_in_graph in range(self._qlistwidget_indexes_of_lines.size):
            current_location_in_qlist_widget = self._qlistwidget_indexes_of_lines[line_index_in_graph]
            new_location_in_qlist_widget = new_indexes[current_location_in_qlist_widget]
            self._qlistwidget_indexes_of_lines[line_index_in_graph] = new_location_in_qlist_widget

        if self._ref_index_x_y:
            location_ref_curve = None if self._ref_index_x_y is None else self._ref_index_x_y[0]
            new_location_ref_curve = new_indexes.get(location_ref_curve, None)
            if new_location_ref_curve != location_ref_curve:
                self._ref_index_x_y[0] = new_location_ref_curve

        self.update_figure(recalculate_limits=False)

    @qtc.Slot(tuple)
    def update_lines_xy(self, tuple_per_i_line: dict, update_figure=True):
        qlistwidget_indexes_of_lines = self._qlistwidget_indexes_of_lines
        for i, (x, y) in tuple_per_i_line.items():
            qlistwidget_indexes_of_lines[i].set_xdata(x)
            qlistwidget_indexes_of_lines[i].set_ydata(y)

    @qtc.Slot(dict)
    def update_labels_and_visibilities(self, label_and_visibility:dict, update_figure=True):
        # label_and_visibility
        # keys are index of line in user defined order
        # contains tuples as values

        # 0th value is label. give label without "_" prefixes
        # 1st value is visibility. give boolean
        # 2nd value is highlight state. give boolean.
        # 3rd value is reference state. give boolean.

        default_line_width = plt.rcParams['lines.linewidth']
        lines_in_qlist_order = self.get_lines_in_qlist_order()
        for i, (new_label, visible, highlighted, reference) in label_and_visibility.items():
            
            line = lines_in_qlist_order[i]

            # Label
            if new_label is None:
                new_label = line.get_label()
            while new_label[0] == "_":
                new_label = new_label.removeprefix("_")


            # 4 states exist for alpha
            # reference, 0.1 alpha, not shown on legend
            # highlighted, 1.0 alpha
            # normal shown, 0.9 alpha
            # hidden, 0.1 alpha, not shown on legend

            if reference is True:
                line.set_alpha(0.1)
                line.set_label("_" + new_label)

            elif highlighted is True:
                line.set_alpha(1)
                line.set_label(new_label)
                if line.get_lw() < default_line_width * 2:
                    line.set_lw(max(default_line_width * 2, line.get_lw() * 1.4))

            elif visible is True:
                line.set_alpha(0.9)
                line.set_label(new_label)
                if line.get_lw() > default_line_width:
                    line.set_lw(default_line_width)

            elif visible is False:
                line.set_alpha(0.1)
                line.set_label("_" + new_label)

        if label_and_visibility and update_figure:
            self.update_figure(recalculate_limits=False, update_legend=True)

    @qtc.Slot()
    def reset_colors(self):
        colors = plt.rcParams["axes.prop_cycle"]()

        for line in self.get_lines_in_qlist_order():
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
