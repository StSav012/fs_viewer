# -*- coding: utf-8 -*-

import os
import numpy as np
import pandas as pd
import sys

import matplotlib
from matplotlib.artist import Artist
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT
import figureoptions

from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import QCoreApplication, QSettings, Qt, QSize
from PyQt5.QtWidgets import QAction, QFileDialog, QLabel, QSizePolicy, QMessageBox,\
    QGroupBox, QFormLayout, QDoubleSpinBox, QPushButton, QHBoxLayout, QVBoxLayout, QDialog

import pyperclip

import mplcursors

FRAME_SIZE = 50.
LINES_COUNT = 2
GRID_LINES_COUNT = 32

TRACE_AVERAGING_RANGE = 25.

IMAGE_EXT = '.svg'


def nonemin(x):
    m = np.nan
    if np.iterable(x):
        for _ in x:
            if _ is not None:
                _2 = float(np.nanmin((m, _)))
                if np.isnan(m) or m > _2:
                    m = _2
        return m
    else:
        return x


def nonemax(x):
    m = np.nan
    if np.iterable(x):
        for _ in x:
            if _ is not None:
                _2 = float(np.nanmax((m, _)))
                if np.isnan(m) or m < _2:
                    m = _2
        return m
    else:
        return x


# https://www.reddit.com/r/learnpython/comments/4kjie3/how_to_include_gui_images_with_pyinstaller/d3gjmom
def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(getattr(sys, '_MEIPASS'), relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def load_icon(filename):
    icon = QIcon()
    icon.addPixmap(QPixmap(resource_path(os.path.join('img', filename + IMAGE_EXT))), QIcon.Normal, QIcon.Off)
    return icon


class SubplotToolQt(QDialog):
    def __init__(self, targetfig, parent):
        super().__init__(parent)
        self.setObjectName("SubplotTool")

        _translate = QCoreApplication.translate

        self._widgets = {}

        layout = QHBoxLayout()
        self.setLayout(layout)

        left = QVBoxLayout()
        layout.addLayout(left)
        right = QVBoxLayout()
        layout.addLayout(right)

        box = QGroupBox(_translate("plot borders settings", "Borders"))
        left.addWidget(box)
        inner = QFormLayout(box)
        self._attrs = [_translate("plot borders settings", "top"),
                       _translate("plot borders settings", "bottom"),
                       _translate("plot borders settings", "left"),
                       _translate("plot borders settings", "right")]
        self._actions = [_translate("plot borders settings", "Tight layout"),
                         _translate("plot borders settings", "Reset"),
                         _translate("plot borders settings", "Close")]
        for side in self._attrs:
            self._widgets[side] = widget = QDoubleSpinBox()
            widget.setMinimum(0)
            widget.setMaximum(1)
            widget.setDecimals(3)
            widget.setSingleStep(.005)
            widget.setKeyboardTracking(False)
            inner.addRow(side, widget)
        left.addStretch(1)

        for action in self._actions:
            self._widgets[action] = widget = QPushButton(action)
            widget.setAutoDefault(False)
            right.addWidget(widget)

        self._widgets[self._actions[2]].setFocus()

        self._figure = targetfig

        for lower, higher in [(self._attrs[1], self._attrs[0]), (self._attrs[2], self._attrs[3])]:
            self._widgets[lower].valueChanged.connect(lambda val: self._widgets[higher].setMinimum(val + .005))
            self._widgets[higher].valueChanged.connect(lambda val: self._widgets[lower].setMaximum(val - .005))

        self._defaults = {attr: vars(self._figure.subplotpars)[attr] for attr in self._attrs}

        # Set values after setting the range callbacks, but before setting up the redraw callbacks.
        # self._reset()
        self.load_settings()

        for attr in self._attrs:
            self._widgets[attr].valueChanged.connect(self._on_value_changed)
        for action, method in zip(self._actions, [self._tight_layout, self._reset, self.close]):
            self._widgets[action].clicked.connect(method)

    def _on_value_changed(self):
        self._figure.subplots_adjust(**{attr: self._widgets[attr].value() for attr in self._attrs})
        self._figure.canvas.draw_idle()
        self.save_settings()

    def _tight_layout(self):
        self._figure.tight_layout()
        for attr in self._attrs:
            widget = self._widgets[attr]
            widget.blockSignals(True)
            widget.setValue(vars(self._figure.subplotpars)[attr])
            widget.blockSignals(False)
        self._figure.canvas.draw_idle()
        self.save_settings()

    def _reset(self):
        for attr, value in self._defaults.items():
            self._widgets[attr].setValue(value)

    def load_settings(self):
        if super().parent is not None and hasattr(super().parent(), 'get_config_value'):
            for attr in self._attrs:
                widget = self._widgets[attr]
                widget.blockSignals(True)
                widget.setValue(
                    super().parent().get_config_value('margins', attr, self._defaults[attr], float))
                widget.blockSignals(False)

    def save_settings(self):
        if super().parent() is not None and hasattr(super().parent(), 'set_config_value'):
            for attr in self._attrs:
                super().parent().set_config_value('margins', attr, self._widgets[attr].value())


class NavigationToolbar(NavigationToolbar2QT):
    def __init__(self, canvas, parent, coordinates=True, *,
                 parameters_title="Figure options", parameters_icon=None):
        NavigationToolbar2QT.__init__(self, canvas, parent, coordinates)
        self.parameters_title = parameters_title
        self.parameters_icon = parameters_icon

    def _init_toolbar(self):
        self.basedir = os.path.join(matplotlib.rcParams['datapath'], 'images')

        self.open_action = QAction(self)
        self.clear_action = QAction(self)
        self.zoom_action = QAction(self)
        self.pan_action = QAction(self)
        self.mark_action = QAction(self)
        self.save_data_action = QAction(self)
        self.save_figure_action = QAction(self)
        self.trace_action = QAction(self)
        self.trace_multiple_action = QAction(self)
        self.copy_trace_action = QAction(self)
        self.save_trace_action = QAction(self)
        self.subplots_action = QAction(self)
        self.configure_action = QAction(self)

        # TODO: add keyboard shortcuts
        for a, i in zip([self.open_action,
                         self.clear_action,
                         self.pan_action,
                         self.zoom_action,
                         self.save_data_action,
                         self.mark_action,
                         self.save_figure_action,
                         self.trace_action,
                         self.trace_multiple_action,
                         self.copy_trace_action,
                         self.save_trace_action,
                         self.subplots_action,
                         self.configure_action],
                        ['open', 'delete',
                         'pan', 'zoom',
                         'savetable', 'measureline',
                         'saveimage',
                         'selectobject', 'selectmultiple',
                         'copyselected', 'saveselected',
                         'size', 'configure']):
            a.setIcon(load_icon(i))
        # TODO: add the conventional buttons, too
        self.addAction(self.open_action)
        self.addAction(self.clear_action)
        self.addSeparator()
        self.addAction(self.pan_action)
        self.addAction(self.zoom_action)
        self.addSeparator()
        self.addAction(self.mark_action)
        self.addAction(self.save_data_action)
        self.addSeparator()
        self.addAction(self.save_figure_action)
        self.addSeparator()
        self.addAction(self.trace_action)
        self.addAction(self.trace_multiple_action)
        self.addAction(self.copy_trace_action)
        self.addAction(self.save_trace_action)
        self.addSeparator()
        self.addAction(self.subplots_action)
        self.addAction(self.configure_action)

        self.clear_action.setEnabled(False)
        self.zoom_action.setEnabled(False)
        self.pan_action.setEnabled(False)
        self.mark_action.setEnabled(False)
        self.save_data_action.setEnabled(False)
        self.save_figure_action.setEnabled(False)
        self.trace_action.setEnabled(False)
        self.trace_multiple_action.setEnabled(False)
        self.copy_trace_action.setEnabled(False)
        self.save_trace_action.setEnabled(False)
        self.configure_action.setEnabled(False)

        self.zoom_action.setCheckable(True)
        self.pan_action.setCheckable(True)
        self.mark_action.setCheckable(True)
        self.trace_action.setCheckable(True)
        self.trace_multiple_action.setCheckable(True)

        # Add the x,y location widget at the right side of the toolbar
        # The stretch factor is 1 which means any resizing of the toolbar
        # will resize this label instead of the buttons.
        if self.coordinates:
            self.locLabel = QLabel("", self)
            self.locLabel.setAlignment(Qt.AlignRight | Qt.AlignTop)
            self.locLabel.setSizePolicy(
                QSizePolicy(QSizePolicy.Expanding,
                            QSizePolicy.Ignored))
            label_action = self.addWidget(self.locLabel)
            label_action.setVisible(True)

        # Esthetic adjustments - we need to set these explicitly in PyQt5
        # otherwise the layout looks different - but we don't want to set it if
        # not using HiDPI icons otherwise they look worse than before.
        self.setIconSize(QSize(24, 24))
        self.layout().setSpacing(12)

    def _update_buttons_checked(self):
        # sync button checkstates to match active mode
        self.pan_action.setChecked(self._active == 'PAN')
        self.zoom_action.setChecked(self._active == 'ZOOM')

    def load_parameters(self):
        if not self.canvas.figure.get_axes():
            return
        ax, = self.canvas.figure.get_axes()
        figureoptions.load_settings(ax, self)

    def edit_parameters(self):
        ax, = self.canvas.figure.get_axes()
        figureoptions.figure_edit(ax, self, title=self.parameters_title, icon=self.parameters_icon)

    def configure_subplots(self):
        dia = SubplotToolQt(self.canvas.figure, self.parent)
        dia.setWindowIcon(self.parent.windowIcon())
        dia.setWindowTitle(self.parent.windowTitle())
        dia.exec_()


class Plot:
    def __init__(self, figure, toolbar, *, legend_figure=None, settings=None, **kwargs):
        if settings is None:
            self.settings = QSettings("SavSoft", "Fast Sweep Viewer")
        else:
            self.settings = settings

        self._canvas = figure.canvas
        self._canvas.draw()

        self._legend_figure = legend_figure
        if self._legend_figure is not None:
            self._legend_figure.canvas.setMaximumWidth(0)
            self._legend_figure.canvas.setMaximumHeight(0)
            self._legend_figure.canvas.setStyleSheet("background-color:transparent;")
            self._legend_figure.canvas.draw()
            # self._legend_figure.canvas.setVisible(False)

        self._figure = figure.add_subplot(1, 1, 1)

        self._toolbar = toolbar

        self._toolbar.open_action.triggered.connect(self.load_data)
        self._toolbar.clear_action.triggered.connect(self.clear)
        self._toolbar.zoom_action.triggered.connect(self._toolbar.zoom)
        self._toolbar.pan_action.triggered.connect(self._toolbar.pan)
        self._toolbar.save_data_action.triggered.connect(
            lambda: self.save_data(*self.save_file_dialog(_filter="CSV (*.csv);;XLSX (*.xlsx)")))
        self._toolbar.save_figure_action.triggered.connect(self.save_figure)
        self._toolbar.mark_action.toggled.connect(self.plot_mark_action_toggled)
        self._toolbar.trace_action.toggled.connect(self.plot_trace_action_toggled)
        self._toolbar.trace_multiple_action.toggled.connect(self.plot_trace_multiple_action_toggled)
        self._toolbar.copy_trace_action.triggered.connect(self.plot_copy_trace_action_triggered)
        self._toolbar.save_trace_action.triggered.connect(self.plot_save_trace_action_triggered)
        self._toolbar.subplots_action.triggered.connect(self._toolbar.configure_subplots)
        self._toolbar.configure_action.triggered.connect(self._toolbar.edit_parameters)

        self._legend = None

        self._plot_lines = [self._figure.plot(np.empty(0), label='_*empty*_ {} (not marked)'.format(i + 1),
                                              animated=False)[0]
                            for i in range(LINES_COUNT)]
        self._plot_mark_lines = [self._figure.plot(np.empty(0), label='_*empty*_ {} (marked)'.format(i + 1),
                                                   animated=False)[0]
                                 for i in range(LINES_COUNT)]
        self._plot_lines_labels = ['_*empty*_'] * LINES_COUNT
        self._plot_frequencies = [np.empty(0)] * LINES_COUNT
        self._plot_voltages = [np.empty(0)] * LINES_COUNT

        def on_pick(event):
            # on the pick event, find the orig line corresponding to the
            # legend proxy line, and toggle the visibility
            _legline = event.artist
            if self._legend is None:
                return
            _index = LINES_COUNT - self._legend.get_lines()[::-1].index(_legline) - 1
            for _lines_set in [self._plot_lines, self._plot_mark_lines]:
                _origline = _lines_set[_index]
                vis = not _origline.get_visible()
                _origline.set_visible(vis)
                if vis:
                    _max_z_order = None
                    for _i in range(LINES_COUNT):
                        if _i != _index:
                            if _max_z_order is None:
                                _max_z_order = _lines_set[_i].zorder
                            else:
                                _max_z_order = max(_lines_set[_i].zorder, _max_z_order)
                    if _max_z_order is not None:
                        _origline.set_zorder(_max_z_order + 1)
            if vis:
                _legline.set_alpha(1.0)
            else:
                _legline.set_alpha(0.2)
            self._legend_figure.canvas.draw()
            self._canvas.draw_idle()

        if self._legend_figure is not None:
            self._legend_figure.canvas.mpl_connect('pick_event', on_pick)

        if hasattr(Artist, 'set_in_layout'):
            annotation_kwargs = dict(
                annotation_clip=True,
                in_layout=False,
                clip_on=True,
                animated=False,
            )
        else:
            annotation_kwargs = dict(
                annotation_clip=True,
                clip_on=True,
                animated=False,
            )
        self.plot_trace_cursor = mplcursors.Cursor(self.lines,
                                                   bindings={'left': 'left', 'right': 'right'},
                                                   annotation_kwargs=annotation_kwargs)
        self.plot_trace_cursor.enabled = False
        self.plot_trace_multiple_cursor = mplcursors.Cursor(self.lines, multiple=True,
                                                            bindings={'left': 'left', 'right': 'right'},
                                                            annotation_kwargs=annotation_kwargs)
        self.plot_trace_multiple_cursor.enabled = False

        self._min_frequency = None
        self._max_frequency = None
        self._min_voltage = None
        self._max_voltage = None
        self._min_mark = None
        self._max_mark = None

        self._figure.callbacks.connect('xlim_changed', self.on_xlim_changed)
        self._figure.callbacks.connect('ylim_changed', self.on_ylim_changed)
        self._axvlines = [self._figure.axvline(np.nan, color='grey', linewidth=0.5,
                                               label='_ vertical line {}'.format(i + 1))
                          for i in range(GRID_LINES_COUNT)]

        self._ignore_scale_change = False

        self.retranslate_ui()

        self.on_xlim_changed_callback = kwargs.pop('on_xlim_changed', None)
        self.on_ylim_changed_callback = kwargs.pop('on_ylim_changed', None)
        self.on_data_loaded_callback = kwargs.pop('on_data_loaded', None)

        self._toolbar.load_parameters()
        self.load_settings()

    def retranslate_ui(self):
        _translate = QCoreApplication.translate

        suffix_mhz = ' ' + _translate("main_window", "MHz")
        suffix_mv = ' ' + _translate("main_window", "mV")

        self._figure.set_xlabel(_translate("plot axes labels", 'Frequency [MHz]'))
        self._figure.set_ylabel(_translate("plot axes labels", 'Voltage [mV]'))
        self._figure.format_coord = lambda x, y: ('{:.3f}' + suffix_mv + '\n{:.3f}' + suffix_mhz).format(y, x)

        self._toolbar.open_action.setIconText(_translate("plot toolbar action", "Open"))
        self._toolbar.open_action.setToolTip(_translate("plot toolbar action", "Load spectrometer data"))
        self._toolbar.clear_action.setIconText(_translate("plot toolbar action", "Clear"))
        self._toolbar.clear_action.setToolTip(_translate("plot toolbar action", "Clear"))
        self._toolbar.zoom_action.setIconText(_translate("plot toolbar action", "Zoom"))
        self._toolbar.zoom_action.setToolTip(_translate("plot toolbar action", "Zoom to rectangle"))
        self._toolbar.pan_action.setIconText(_translate("plot toolbar action", "Pan"))
        self._toolbar.pan_action.setToolTip(_translate("plot toolbar action",
                                                       "Pan axes with left mouse, zoom with right"))
        self._toolbar.mark_action.setIconText(_translate("plot toolbar action", "Mark"))
        self._toolbar.mark_action.setToolTip(_translate("plot toolbar action", "Mark"))
        self._toolbar.save_data_action.setIconText(_translate("plot toolbar action", "Save Data"))
        self._toolbar.save_data_action.setToolTip(_translate("plot toolbar action", "Export data"))
        self._toolbar.save_figure_action.setIconText(_translate("plot toolbar action", "Save Figure"))
        self._toolbar.save_figure_action.setToolTip(_translate("plot toolbar action", "Export figure"))
        self._toolbar.trace_action.setIconText(_translate("plot toolbar action", "Trace"))
        self._toolbar.trace_multiple_action.setIconText(_translate("plot toolbar action", "Trace Multiple"))
        self._toolbar.copy_trace_action.setIconText(_translate("plot toolbar action", "Copy Traced"))
        self._toolbar.copy_trace_action.setToolTip(_translate("plot toolbar action",
                                                              "Copy trace points into clipboard"))
        self._toolbar.save_trace_action.setIconText(_translate("plot toolbar action", "Save Traced"))
        self._toolbar.save_trace_action.setToolTip(_translate("plot toolbar action", "Save trace points"))
        self._toolbar.subplots_action.setIconText(_translate("plot toolbar action", "Position and Size"))
        self._toolbar.subplots_action.setToolTip(_translate("plot toolbar action", "Position and size"))
        self._toolbar.configure_action.setIconText(_translate("plot toolbar action", "Configure"))
        self._toolbar.configure_action.setToolTip(_translate("plot toolbar action",
                                                             "Edit axis, curve and image parameters"))

        def annotation_text(sel):
            x = sel.target[0]
            y = sel.target[1]
            line = sel.artist
            good = np.abs(line.get_xdata() - x) < TRACE_AVERAGING_RANGE
            average_y = np.mean(line.get_ydata()[good])
            setattr(sel.target, 'offset', average_y)
            return (line.original_label + '\n'
                    + '{:.3f}' + suffix_mhz + '\n'
                    + '{:.3f}' + suffix_mv + '\n'
                    + '{:.3f}' + suffix_mv + ' ' + _translate("main_window", "to mean")).format(x, y, y - average_y)

        def cursor_add_action(sel):
            sel.annotation.set_text(annotation_text(sel))
            if hasattr(sel.artist, 'original_label'):
                setattr(sel.annotation, 'original_label', sel.artist.original_label)

        self.plot_trace_cursor.connect("add", cursor_add_action)
        self.plot_trace_multiple_cursor.connect("add", cursor_add_action)

    def make_grid(self, xlim):
        if any(map(lambda lim: lim is None, xlim)):
            return
        if np.ptp(xlim) // FRAME_SIZE <= len(self._axvlines):
            minor_xticks = np.arange(
                np.floor_divide(min(xlim), FRAME_SIZE) * FRAME_SIZE,
                (np.floor_divide(max(xlim), FRAME_SIZE) + 1) * FRAME_SIZE,
                FRAME_SIZE)
            if minor_xticks.size < len(self._axvlines):
                minor_xticks = np.concatenate((minor_xticks, np.full(len(self._axvlines) - minor_xticks.size, np.nan)))
            for index, line in enumerate(self._axvlines):
                line.set_xdata(minor_xticks[index])
        else:
            for line in self._axvlines:
                line.set_xdata(np.nan)

    def on_xlim_changed(self, axes):
        if self._ignore_scale_change:
            return
        xlim = axes.get_xlim()
        self.make_grid(xlim)
        if self.on_xlim_changed_callback is not None and callable(self.on_xlim_changed_callback):
            self._ignore_scale_change = True
            self.on_xlim_changed_callback(xlim)
            self._ignore_scale_change = False

    def on_ylim_changed(self, axes):
        if self._ignore_scale_change:
            return
        ylim = axes.get_ylim()
        if self.on_ylim_changed_callback is not None and callable(self.on_ylim_changed_callback):
            self._ignore_scale_change = True
            self.on_ylim_changed_callback(ylim)
            self._ignore_scale_change = False

    def load_settings(self):
        attrs = ["top", "bottom", "left", "right"]
        defaults = {attr: vars(self._canvas.figure.subplotpars)[attr] for attr in attrs}
        self._canvas.figure.subplots_adjust(**{attr: self.get_config_value('margins', attr, defaults[attr], float)
                                               for attr in attrs})
        self._canvas.draw_idle()

    @property
    def lines(self):
        return self._plot_lines + self._plot_mark_lines

    @property
    def marked_lines(self):
        return self._plot_mark_lines

    @property
    def labels(self):
        return self._plot_lines_labels

    def on_dblclick(self, event):
        event.inaxes.set_autoscaley_on(True)
        event.inaxes.relim(visible_only=True)
        event.inaxes.autoscale_view(None, None, None)
        event.inaxes.set_xlim(self._min_frequency, self._max_frequency)
        event.inaxes.set_ylim(self._min_voltage, self._max_voltage)
        self._canvas.draw_idle()
        return self._min_frequency, self._max_frequency, self._min_voltage, self._max_voltage

    def set_frequency_range(self, lower_value=None, upper_value=None):
        self._figure.set_xlim(left=lower_value, right=upper_value, emit=True)
        self._canvas.draw_idle()

    def set_voltage_range(self, lower_value=None, upper_value=None):
        self._figure.set_ylim(bottom=lower_value, top=upper_value, emit=False)
        self._canvas.draw_idle()

    def set_mark(self, lower_value=None, upper_value=None):
        self._min_mark = lower_value
        self._max_mark = upper_value
        self.draw_data(self._plot_frequencies, self._plot_voltages, (lower_value, upper_value))

    def draw_data(self, xs, ys, marks):
        self._ignore_scale_change = True
        for i, (x, y) in enumerate(zip(xs, ys)):
            left_x = np.empty(0)
            left_y = np.empty(0)
            middle_x = x
            middle_y = y
            right_x = np.empty(0)
            right_y = np.empty(0)
            if marks[0] is not None:
                good = (middle_x < marks[0])
                left_x = middle_x[good]
                left_y = middle_y[good]
                middle_x = middle_x[~good]
                middle_y = middle_y[~good]
                del good
            if marks[1] is not None:
                good = (middle_x > marks[1])
                right_x = middle_x[good]
                right_y = middle_y[good]
                middle_x = middle_x[~good]
                middle_y = middle_y[~good]
                del good
            side_x = np.concatenate((left_x, [np.nan], right_x))
            side_y = np.concatenate((left_y, [np.nan], right_y))
            if self._plot_lines[i].get_xdata().size == 0:
                self._figure.set_xlim(self._min_frequency, self._max_frequency)
                self._figure.set_ylim(self._min_voltage, self._max_voltage)
            self._plot_lines[i].set_data(side_x, side_y)
            self._plot_lines[i].set_label(self._plot_lines_labels[i] + ' (not marked)')
            setattr(self._plot_lines[i], 'original_label', self._plot_lines_labels[i])
            self._plot_mark_lines[i].set_data(middle_x, middle_y)
            self._plot_mark_lines[i].set_label(self._plot_lines_labels[i] + ' (marked)')
            setattr(self._plot_mark_lines[i], 'original_label', self._plot_lines_labels[i])
        self._canvas.draw_idle()
        self._ignore_scale_change = False

    def clear(self):
        self._plot_voltages = [np.empty(0)] * LINES_COUNT
        self._plot_frequencies = [np.empty(0)] * LINES_COUNT
        for line in self._plot_lines:
            line.set_data(np.empty(0), np.empty(0))
        for line in self._plot_mark_lines:
            line.set_data(np.empty(0), np.empty(0))
        self._plot_lines_labels = ['_*empty*_'] * LINES_COUNT
        if self._legend is not None:
            self._legend.remove()
            self._legend = None
        self._canvas.draw_idle()
        if self._legend_figure is not None:
            self._legend_figure.canvas.draw()
            self._legend_figure.canvas.setMaximumWidth(0)
            self._legend_figure.canvas.setMaximumHeight(0)
            self._legend_figure.canvas.setMinimumWidth(0)
            self._legend_figure.canvas.setMinimumHeight(0)
            # self._legend_figure.canvas.setVisible(False)
        for sel in self.plot_trace_multiple_cursor.selections:
            self.plot_trace_multiple_cursor.remove_selection(sel)
        for sel in self.plot_trace_cursor.selections:
            self.plot_trace_cursor.remove_selection(sel)
        self._toolbar.zoom_action.setChecked(False)
        self._toolbar.pan_action.setChecked(False)
        self._toolbar.mark_action.setChecked(False)
        self._toolbar.trace_action.setChecked(False)
        self._toolbar.trace_multiple_action.setChecked(False)
        self._toolbar.clear_action.setEnabled(False)
        self._toolbar.zoom_action.setEnabled(False)
        self._toolbar.pan_action.setEnabled(False)
        self._toolbar.mark_action.setEnabled(False)
        self._toolbar.save_data_action.setEnabled(False)
        self._toolbar.save_figure_action.setEnabled(False)
        self._toolbar.trace_action.setEnabled(False)
        self._toolbar.trace_multiple_action.setEnabled(False)
        self._toolbar.copy_trace_action.setEnabled(False)
        self._toolbar.save_trace_action.setEnabled(False)
        self._toolbar.configure_action.setEnabled(False)

    def load_data(self):
        filename, _filter = self.open_file_dialog(_filter="Spectrometer Settings (*.fmd);;All Files (*)")
        fn = os.path.splitext(filename)[0]
        _min_frequency = self._min_frequency
        _max_frequency = self._max_frequency
        if os.path.exists(fn + '.fmd'):
            with open(fn + '.fmd', 'r') as fin:
                for line in fin:
                    if line and not line.startswith('*'):
                        t = list(map(lambda w: w.strip(), line.split(':', maxsplit=1)))
                        if len(t) > 1:
                            if t[0] == 'Fstart [GHz]':
                                _min_frequency = float(t[1])
                            elif t[0] == 'Fstop [GHz]':
                                _max_frequency = float(t[1])
        else:
            return None
        if os.path.exists(fn + '.frd'):
            self._plot_voltages = self._plot_voltages[1:] + [np.loadtxt(fn + '.frd', usecols=(0,))]
            self._plot_frequencies = self._plot_frequencies[1:] + [np.linspace(_min_frequency, _max_frequency,
                                                                               num=self._plot_voltages[-1].size,
                                                                               endpoint=False)]
            new_label_base = os.path.split(fn)[-1]
            new_label = new_label_base
            i = 1
            while new_label in self._plot_lines_labels[1:]:
                i += 1
                new_label = '{} ({})'.format(new_label_base, i)
            self._plot_lines_labels = self._plot_lines_labels[1:] + [new_label]
            self._min_frequency = nonemin((_min_frequency, self._min_frequency))
            self._max_frequency = nonemax((_max_frequency, self._max_frequency))
            self._min_voltage = nonemin((self._min_voltage, np.min(self._plot_voltages[-1])))
            self._max_voltage = nonemax((self._max_voltage, np.max(self._plot_voltages[-1])))
            self.draw_data(self._plot_frequencies, self._plot_voltages, (self._min_mark, self._max_mark))

            if any(map(lambda l: not l.startswith('_'), self._plot_lines_labels)):
                if self._legend is not None:
                    self._legend.remove()
                labels = []
                lines = []
                for i, lbl in enumerate(self._plot_lines_labels):
                    if not lbl.startswith('_'):
                        labels.append(lbl)
                        lines.append(self._plot_mark_lines[i])
                if self._legend_figure is not None:
                    self._legend = self._legend_figure.legend(lines, labels, frameon=False,
                                                              loc='center', facecolor='red')
                    self._legend_figure.canvas.draw()
                    we = self._legend.get_window_extent()
                    self._legend_figure.canvas.setMinimumWidth(we.width)
                    self._legend_figure.canvas.setMaximumWidth(we.width)
                    self._legend_figure.canvas.setMinimumHeight(we.height)
                    self._legend_figure.canvas.setMaximumHeight(we.height)
                    self._legend_figure.canvas.draw()
                    # self._legend_figure.canvas.setVisible(True)
                    for _legline in self._legend.get_lines():
                        _legline.set_picker(5)

            self._toolbar.clear_action.setEnabled(True)
            self._toolbar.zoom_action.setEnabled(True)
            self._toolbar.pan_action.setEnabled(True)
            self._toolbar.mark_action.setEnabled(True)
            self._toolbar.save_data_action.setEnabled(True)
            self._toolbar.save_figure_action.setEnabled(True)
            self._toolbar.trace_action.setEnabled(True)
            self._toolbar.trace_multiple_action.setEnabled(True)
            self._toolbar.copy_trace_action.setEnabled(True)
            self._toolbar.save_trace_action.setEnabled(True)
            self._toolbar.configure_action.setEnabled(True)

            if self.on_data_loaded_callback is not None and callable(self.on_data_loaded_callback):
                self.on_data_loaded_callback((self._min_frequency, self._max_frequency,
                                              self._min_voltage, self._max_voltage))

            return self._min_frequency, self._max_frequency, self._min_voltage, self._max_voltage
        return None

    @property
    def mode(self):
        return self._toolbar.mode

    @property
    def mark_mode(self):
        return self._toolbar.mark_action.isChecked()

    @property
    def trace_mode(self):
        return self._toolbar.trace_action.isChecked()

    @property
    def trace_multiple_mode(self):
        return self._toolbar.trace_multiple_action.isChecked()

    def actions_off(self):
        self._toolbar.mark_action.setChecked(False)
        self._toolbar.trace_action.setChecked(False)
        self._toolbar.trace_multiple_action.setChecked(False)

    def plot_mark_action_toggled(self, new_value):
        if self._toolbar.mode == 'zoom rect':
            self._toolbar.zoom()
        elif self._toolbar.mode == 'pan/zoom':
            self._toolbar.pan()
        if new_value:
            self._toolbar.trace_action.setChecked(False)
            self._toolbar.trace_multiple_action.setChecked(False)

    def plot_trace_action_toggled(self, new_value):
        if new_value:
            self._toolbar.mark_action.setChecked(False)
            self._toolbar.trace_multiple_action.setChecked(False)
            self._canvas.setFocus()
        if self._toolbar.mode == 'zoom rect':
            self._toolbar.zoom()
        elif self._toolbar.mode == 'pan/zoom':
            self._toolbar.pan()
        self.plot_trace_cursor.enabled = new_value
        self.plot_trace_cursor.visible = new_value
        self.plot_trace_multiple_cursor.enabled = False
        self.plot_trace_multiple_cursor.visible = False

    def plot_trace_multiple_action_toggled(self, new_value):
        if new_value:
            self._toolbar.mark_action.setChecked(False)
            self._toolbar.trace_action.setChecked(False)
            self._canvas.setFocus()
        if self._toolbar.mode == 'zoom rect':
            self._toolbar.zoom()
        elif self._toolbar.mode == 'pan/zoom':
            self._toolbar.pan()
        self.plot_trace_cursor.enabled = False
        self.plot_trace_cursor.visible = False
        self.plot_trace_multiple_cursor.enabled = new_value
        self.plot_trace_multiple_cursor.visible = new_value

    def plot_copy_trace_action_triggered(self):
        sep = '\t'
        table = ''
        selections = []
        if self.plot_trace_multiple_cursor.enabled:
            selections = self.plot_trace_multiple_cursor.selections
        elif self.plot_trace_cursor.enabled:
            selections = self.plot_trace_cursor.selections
        for sel in selections:
            x, y = sel.target.tolist()
            offset = sel.target.offset
            table += '{1}{0}{2}{0}{3}{0}"{4}"'.format(sep, x, y, y - offset, sel.annotation.original_label) + os.linesep
        if table:
            pyperclip.copy(table)

    def plot_save_trace_action_triggered(self):
        selections = []
        if self.plot_trace_multiple_cursor.enabled:
            selections = self.plot_trace_multiple_cursor.selections
        elif self.plot_trace_cursor.enabled:
            selections = self.plot_trace_cursor.selections

        labels = []
        for sel in selections:
            label = sel.annotation.original_label
            if label not in labels:
                labels.append(label)

        data = dict()
        for label in labels:
            picked_x = []
            picked_y = []
            picked_dy = []
            for sel in selections:
                if sel.annotation.original_label != label:
                    continue
                x, y = sel.target.tolist()
                picked_x.append(x)
                picked_y.append(y)
                picked_dy.append(y - sel.target.offset)
            if not picked_x or not picked_y:
                continue
            data[label] = (picked_x, picked_y, picked_dy)

        filename, _filter = self.save_file_dialog(_filter="CSV (*.csv);;XLSX (*.xlsx)")
        if filename:
            sep = '\t'
            self.save_arbitrary_data(data, filename, _filter,
                                     csv_header=(sep.join(('frequency', 'voltage', 'voltage_to_mean')) + os.linesep
                                                 + sep.join(('MHz', 'mV', 'mV'))),
                                     csv_sep=sep,
                                     xlsx_header=['Frequency [MHz]', 'Voltage [mV]', 'Voltage to Mean [mV]'])

    def save_data(self, filename, _filter):
        if self._plot_voltages[-1].size == 0 or not filename:
            return
        filename_parts = os.path.splitext(filename)
        if 'CSV' in _filter:
            if filename_parts[1] != '.csv':
                filename += '.csv'
            x = self._plot_frequencies[-1]
            y = self._plot_voltages[-1]
            if self._max_mark is not None:
                good = (x <= self._max_mark)
                x = x[good]
                y = y[good]
                del good
            if self._min_mark is not None:
                good = (x >= self._min_mark)
                x = x[good]
                y = y[good]
                del good
            data = np.vstack((x, y)).transpose()
            sep = '\t'
            # noinspection PyTypeChecker
            np.savetxt(filename, data,
                       delimiter=sep,
                       header=sep.join(('frequency', 'voltage')) + os.linesep + sep.join(('MHz', 'mV')),
                       fmt='%s')
        elif 'XLSX' in _filter:
            if filename_parts[1] != '.xlsx':
                filename += '.xlsx'
            with pd.ExcelWriter(filename) as writer:
                for i, (x, y) in enumerate(zip(self._plot_frequencies, self._plot_voltages)):
                    if self._plot_lines_labels[i].startswith('_*empty*_'):
                        continue
                    if self._max_mark is not None:
                        good = (x <= self._max_mark)
                        x = x[good]
                        y = y[good]
                        del good
                    if self._min_mark is not None:
                        good = (x >= self._min_mark)
                        x = x[good]
                        y = y[good]
                        del good
                    data = np.vstack((x, y)).transpose()
                    df = pd.DataFrame(data)
                    df.to_excel(writer, index=False, header=['Frequency [MHz]', 'Voltage [mV]'],
                                sheet_name=self._plot_lines_labels[i])

    def save_figure(self):
        # TODO: add legend to the figure to save
        filetypes = self._canvas.get_supported_filetypes_grouped()
        sorted_filetypes = sorted(filetypes.items())

        filters = []
        for name, exts in sorted_filetypes:
            exts_list = " ".join(['*.%s' % ext for ext in exts])
            _filter = '%s (%s)' % (name, exts_list)
            filters.append(_filter)
        filters = ';;'.join(filters)

        fname, _filter = self.save_file_dialog(_filter=filters)
        if fname:
            try:
                self._canvas.figure.savefig(fname)
            except Exception as e:
                QMessageBox.critical(self._canvas.parent(), "Error saving file", str(e),
                                     QMessageBox.Ok, QMessageBox.NoButton)

    @staticmethod
    def save_arbitrary_data(data, filename, _filter, *,
                            csv_header='', csv_sep='\t',
                            xlsx_header=None, sheet_name='Markings'):
        if not filename:
            return
        if xlsx_header is None:
            xlsx_header = True
        filename_parts = os.path.splitext(filename)
        if 'CSV' in _filter:
            if filename_parts[1].lower() != '.csv':
                filename += '.csv'
            if isinstance(data, dict):
                joined_data = None
                for key, value in data.items():
                    if joined_data is None:
                        joined_data = np.vstack(value).transpose()
                    else:
                        joined_data = np.vstack((joined_data, np.vstack(value).transpose()))
                data = joined_data
            else:
                data = np.vstack(data).transpose()
            # noinspection PyTypeChecker
            np.savetxt(filename, data,
                       delimiter=csv_sep,
                       header=csv_header,
                       fmt='%s')
        elif 'XLSX' in _filter:
            if filename_parts[1].lower() != '.xlsx':
                filename += '.xlsx'
            with pd.ExcelWriter(filename) as writer:
                if isinstance(data, dict):
                    for sheet_name in data:
                        sheet_data = np.vstack(data[sheet_name]).transpose()
                        df = pd.DataFrame(sheet_data)
                        df.to_excel(writer, index=False, header=xlsx_header,
                                    sheet_name=sheet_name)
                else:
                    data = np.vstack(data).transpose()
                    df = pd.DataFrame(data)
                    df.to_excel(writer, index=False, header=xlsx_header,
                                sheet_name=sheet_name)

    def get_config_value(self, section, key, default, _type):
        if section not in self.settings.childGroups():
            return default
        self.settings.beginGroup(section)
        # print(section, key)
        try:
            v = self.settings.value(key, default, _type)
        except TypeError:
            v = default
        self.settings.endGroup()
        return v

    def set_config_value(self, section, key, value):
        self.settings.beginGroup(section)
        # print(section, key, value, type(value))
        self.settings.setValue(key, value)
        self.settings.endGroup()

    def open_file_dialog(self, _filter=''):
        directory = self.get_config_value('open', 'location', '', str)
        # native dialog misbehaves when running inside snap but Qt dialog is tortoise-like in NT
        options = QFileDialog.DontUseNativeDialog if os.name != 'nt' else QFileDialog.DontUseSheet
        filename, _filter = QFileDialog.getOpenFileName(filter=_filter,
                                                        directory=directory,
                                                        options=options)
        if os.path.split(filename)[0]:
            self.set_config_value('open', 'location', os.path.split(filename)[0])
        return filename, _filter

    def save_file_dialog(self, _filter=''):
        directory = self.get_config_value('save', 'location', '', str)
        initial_filter = self.get_config_value('save', 'filter', '', str)
        # native dialog misbehaves when running inside snap but Qt dialog is tortoise-like in NT
        options = QFileDialog.DontUseNativeDialog if os.name != 'nt' else QFileDialog.DontUseSheet
        filename, _filter = QFileDialog.getSaveFileName(filter=_filter,
                                                        directory=directory,
                                                        initialFilter=initial_filter,
                                                        options=options)
        if os.path.split(filename)[0]:
            self.set_config_value('save', 'location', os.path.split(filename)[0])
        self.set_config_value('save', 'filter', _filter)
        return filename, _filter
