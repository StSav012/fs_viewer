#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
import os

import numpy as np

from PyQt5.QtCore import Qt, QCoreApplication, \
    QSettings, \
    QMetaObject
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import QMainWindow, QApplication, \
    QWidget, QDesktopWidget, \
    QGridLayout, \
    QGroupBox, QLabel, \
    QCheckBox, QPushButton, \
    QDoubleSpinBox, \
    QFileDialog, QMessageBox, \
    QAction
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.style as mplstyle
import mplcursors
import pyperclip

import backend

mplstyle.use('fast')

MAX_FREQUENCY = 175000.0
MIN_FREQUENCY = 115000.0
MAX_VOLTAGE = 617.0
MIN_VOLTAGE = -MAX_VOLTAGE

TRACE_AVERAGING_RANGE = 25.

IMAGE_EXT = '.svg'


# https://www.reddit.com/r/learnpython/comments/4kjie3/how_to_include_gui_images_with_pyinstaller/d3gjmom
def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(getattr(sys, '_MEIPASS'), relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


class App(QMainWindow):
    def __init__(self):
        super().__init__(flags=Qt.WindowFlags())
        self.central_widget = QWidget(self, flags=Qt.WindowFlags())
        self.grid_layout = QGridLayout(self.central_widget)
        self.grid_layout.setColumnStretch(0, 1)

        # Frequency box
        self.group_frequency = QGroupBox(self.central_widget)
        self.grid_layout_frequency = QGridLayout(self.group_frequency)

        self.label_frequency_min = QLabel(self.group_frequency)
        self.label_frequency_max = QLabel(self.group_frequency)
        self.label_frequency_center = QLabel(self.group_frequency)
        self.label_frequency_span = QLabel(self.group_frequency)

        self.spin_frequency_min = QDoubleSpinBox(self.group_frequency)
        self.spin_frequency_min.setMinimum(MIN_FREQUENCY)
        self.spin_frequency_min.setMaximum(MAX_FREQUENCY)
        self.spin_frequency_max = QDoubleSpinBox(self.group_frequency)
        self.spin_frequency_max.setMinimum(MIN_FREQUENCY)
        self.spin_frequency_max.setMaximum(MAX_FREQUENCY)
        self.spin_frequency_center = QDoubleSpinBox(self.group_frequency)
        self.spin_frequency_center.setMinimum(MIN_FREQUENCY)
        self.spin_frequency_center.setMaximum(MAX_FREQUENCY)
        self.spin_frequency_span = QDoubleSpinBox(self.group_frequency)
        self.spin_frequency_span.setMinimum(0.01)
        self.spin_frequency_span.setMaximum(MAX_FREQUENCY - MIN_FREQUENCY)

        self.check_frequency_persists = QCheckBox(self.group_frequency)

        # Zoom X
        self.button_zoom_x_out_coarse = QPushButton(self.group_frequency)
        self.button_zoom_x_out_fine = QPushButton(self.group_frequency)
        self.button_zoom_x_in_fine = QPushButton(self.group_frequency)
        self.button_zoom_x_in_coarse = QPushButton(self.group_frequency)

        # Move X
        self.button_move_x_left_coarse = QPushButton(self.group_frequency)
        self.button_move_x_left_fine = QPushButton(self.group_frequency)
        self.button_move_x_right_fine = QPushButton(self.group_frequency)
        self.button_move_x_right_coarse = QPushButton(self.group_frequency)

        # Voltage box
        self.group_voltage = QGroupBox(self.central_widget)
        self.grid_layout_voltage = QGridLayout(self.group_voltage)

        self.label_voltage_min = QLabel(self.group_voltage)
        self.label_voltage_max = QLabel(self.group_voltage)

        self.spin_voltage_min = QDoubleSpinBox(self.group_voltage)
        self.spin_voltage_min.setMinimum(MIN_VOLTAGE)
        self.spin_voltage_min.setMaximum(MAX_VOLTAGE)
        self.spin_voltage_max = QDoubleSpinBox(self.group_voltage)
        self.spin_voltage_max.setMinimum(MIN_VOLTAGE)
        self.spin_voltage_max.setMaximum(MAX_VOLTAGE)

        self.check_voltage_persists = QCheckBox(self.group_voltage)

        # Zoom Y
        self.button_zoom_y_out_coarse = QPushButton(self.group_voltage)
        self.button_zoom_y_out_fine = QPushButton(self.group_voltage)
        self.button_zoom_y_in_fine = QPushButton(self.group_voltage)
        self.button_zoom_y_in_coarse = QPushButton(self.group_voltage)

        # Frequency Mark box
        self.group_mark = QGroupBox(self.central_widget)
        self.grid_layout_mark = QGridLayout(self.group_mark)
        self.grid_layout_mark.setColumnStretch(0, 1)
        self.grid_layout_mark.setColumnStretch(1, 1)

        self.label_mark_min = QLabel(self.group_mark)
        self.label_mark_max = QLabel(self.group_mark)

        self.spin_mark_min = QDoubleSpinBox(self.group_mark)
        self.spin_mark_min.setMinimum(MIN_FREQUENCY)
        self.spin_mark_min.setMaximum(MAX_FREQUENCY)
        self.spin_mark_max = QDoubleSpinBox(self.group_mark)
        self.spin_mark_max.setMinimum(MIN_FREQUENCY)
        self.spin_mark_max.setMaximum(MAX_FREQUENCY)
        self.spin_mark_min.setValue(MIN_FREQUENCY)
        self.spin_mark_max.setValue(MAX_FREQUENCY)
        self.button_mark_min_reset = QPushButton(self.group_mark)
        self.button_mark_max_reset = QPushButton(self.group_mark)
        for b in (self.button_mark_min_reset, self.button_mark_max_reset):
            b.setIcon(self.load_icon('reset'))
        self.button_zoom_to_selection = QPushButton(self.group_mark)

        # plot
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setFocusPolicy(Qt.ClickFocus)
        self.plot_toolbar = NavigationToolbar(self.canvas, self)
        self.plot_open_action = QAction(self.plot_toolbar)
        self.plot_clear_action = QAction(self.plot_toolbar)
        self.plot_mark_action = QAction(self.plot_toolbar)
        self.plot_save_data_action = QAction(self.plot_toolbar)
        self.plot_trace_action = QAction(self.plot_toolbar)
        self.plot_trace_multiple_action = QAction(self.plot_toolbar)
        self.plot_copy_trace_action = QAction(self.plot_toolbar)
        self.plot_save_trace_action = QAction(self.plot_toolbar)
        self.plot_widget = self.figure.add_subplot(1, 1, 1)
        self.plot = backend.Plot(figure=self.plot_widget,
                                 canvas=self.canvas)
        self.plot_trace_cursor = mplcursors.cursor(self.plot.lines,
                                                   bindings={'left': 'left', 'right': 'right'})
        self.plot_trace_cursor.enabled = False
        self.plot_trace_multiple_cursor = mplcursors.cursor(self.plot.lines, multiple=True,
                                                            bindings={'left': 'left', 'right': 'right'})
        self.plot_trace_multiple_cursor.enabled = False

        self.setup_ui(self)

        self.settings = QSettings("SavSoft", "Fast Sweep Viewer")
        # prevent config from being re-written while loading
        self._loading = True
        # config
        self.load_config()

        # plot toolbar
        # TODO: add keyboard shortcuts
        for a, i in zip([self.plot_open_action, self.plot_clear_action,
                         self.plot_save_data_action, self.plot_mark_action,
                         self.plot_trace_action, self.plot_trace_multiple_action,
                         self.plot_copy_trace_action, self.plot_save_trace_action],
                        ['open', 'delete',
                         'savetable', 'measureline',
                         'selectobject', 'selectmultiple',
                         'copyselected', 'saveselected']):
            a.setIcon(self.load_icon(i))
        self.plot_toolbar.addAction(self.plot_open_action)
        self.plot_toolbar.addAction(self.plot_clear_action)
        self.plot_toolbar.addSeparator()
        self.plot_toolbar.addAction(self.plot_mark_action)
        self.plot_toolbar.addAction(self.plot_save_data_action)
        self.plot_toolbar.addSeparator()
        self.plot_toolbar.addAction(self.plot_trace_action)
        self.plot_toolbar.addAction(self.plot_trace_multiple_action)
        self.plot_toolbar.addAction(self.plot_copy_trace_action)
        self.plot_toolbar.addAction(self.plot_save_trace_action)
        self.plot_clear_action.setEnabled(False)
        self.plot_mark_action.setEnabled(False)
        self.plot_save_data_action.setEnabled(False)
        self.plot_trace_action.setEnabled(False)
        self.plot_trace_multiple_action.setEnabled(False)
        self.plot_copy_trace_action.setEnabled(False)
        self.plot_save_trace_action.setEnabled(False)

        # actions
        self.spin_frequency_min.valueChanged.connect(self.spin_frequency_min_changed)
        self.spin_frequency_max.valueChanged.connect(self.spin_frequency_max_changed)
        self.spin_frequency_center.valueChanged.connect(self.spin_frequency_center_changed)
        self.spin_frequency_span.valueChanged.connect(self.spin_frequency_span_changed)
        self.button_zoom_x_out_coarse.clicked.connect(lambda: self.button_zoom_x_clicked(1. / 0.5))
        self.button_zoom_x_out_fine.clicked.connect(lambda: self.button_zoom_x_clicked(1. / 0.9))
        self.button_zoom_x_in_fine.clicked.connect(lambda: self.button_zoom_x_clicked(0.9))
        self.button_zoom_x_in_coarse.clicked.connect(lambda: self.button_zoom_x_clicked(0.5))
        self.button_move_x_left_coarse.clicked.connect(lambda: self.button_move_x_clicked(-500.))
        self.button_move_x_left_fine.clicked.connect(lambda: self.button_move_x_clicked(-50.))
        self.button_move_x_right_fine.clicked.connect(lambda: self.button_move_x_clicked(50.))
        self.button_move_x_right_coarse.clicked.connect(lambda: self.button_move_x_clicked(500.))
        self.spin_voltage_min.valueChanged.connect(self.spin_voltage_min_changed)
        self.spin_voltage_max.valueChanged.connect(self.spin_voltage_max_changed)
        self.button_zoom_y_out_coarse.clicked.connect(lambda: self.button_zoom_y_clicked(1. / 0.5))
        self.button_zoom_y_out_fine.clicked.connect(lambda: self.button_zoom_y_clicked(1. / 0.9))
        self.button_zoom_y_in_fine.clicked.connect(lambda: self.button_zoom_y_clicked(0.9))
        self.button_zoom_y_in_coarse.clicked.connect(lambda: self.button_zoom_y_clicked(0.5))
        self.spin_mark_min.valueChanged.connect(self.spin_mark_min_changed)
        self.spin_mark_max.valueChanged.connect(self.spin_mark_max_changed)
        self.button_mark_min_reset.clicked.connect(self.button_mark_min_reset_clicked)
        self.button_mark_max_reset.clicked.connect(self.button_mark_max_reset_clicked)
        self.button_zoom_to_selection.clicked.connect(self.button_zoom_to_selection_clicked)

        self.plot_open_action.triggered.connect(self.load_data)
        self.plot_clear_action.triggered.connect(self.clear)
        self.plot_save_data_action.triggered.connect(
            lambda: self.plot.save_data(*self.save_file_dialog(_filter="CSV (*.csv);;XLSX (*.xlsx)")))
        self.plot_mark_action.toggled.connect(self.plot_mark_action_toggled)
        self.plot_trace_action.toggled.connect(self.plot_trace_action_toggled)
        self.plot_trace_multiple_action.toggled.connect(self.plot_trace_multiple_action_toggled)
        self.plot_copy_trace_action.triggered.connect(self.plot_copy_trace_action_triggered)
        self.plot_save_trace_action.triggered.connect(self.plot_save_trace_action_triggered)

        # dirty hack: the event doesn't work directly for subplots
        self.mpl_connect_cid = self.canvas.mpl_connect('button_press_event', self.plot_on_click)

    def setup_ui(self, main_window):
        main_window.resize(484, 441)
        main_window.setWindowIcon(self.load_icon('sweep'))

        self.plot_mark_action.setCheckable(True)
        self.plot_trace_action.setCheckable(True)
        self.plot_trace_multiple_action.setCheckable(True)

        self.grid_layout_frequency.addWidget(self.label_frequency_min, 1, 0, 1, 2)
        self.grid_layout_frequency.addWidget(self.label_frequency_max, 0, 0, 1, 2)
        self.grid_layout_frequency.addWidget(self.label_frequency_center, 2, 0, 1, 2)
        self.grid_layout_frequency.addWidget(self.label_frequency_span, 3, 0, 1, 2)
        self.grid_layout_frequency.addWidget(self.spin_frequency_min, 1, 2, 1, 2)
        self.grid_layout_frequency.addWidget(self.spin_frequency_max, 0, 2, 1, 2)
        self.grid_layout_frequency.addWidget(self.spin_frequency_center, 2, 2, 1, 2)
        self.grid_layout_frequency.addWidget(self.spin_frequency_span, 3, 2, 1, 2)
        self.grid_layout_frequency.addWidget(self.check_frequency_persists, 4, 0, 1, 4)

        self.grid_layout_voltage.addWidget(self.label_voltage_min, 1, 0, 1, 2)
        self.grid_layout_voltage.addWidget(self.label_voltage_max, 0, 0, 1, 2)
        self.grid_layout_voltage.addWidget(self.spin_voltage_min, 1, 2, 1, 2)
        self.grid_layout_voltage.addWidget(self.spin_voltage_max, 0, 2, 1, 2)
        self.grid_layout_voltage.addWidget(self.check_voltage_persists, 2, 0, 1, 4)

        self.grid_layout_frequency.addWidget(self.button_zoom_x_out_coarse, 5, 0)
        self.grid_layout_frequency.addWidget(self.button_zoom_x_out_fine, 5, 1)
        self.grid_layout_frequency.addWidget(self.button_zoom_x_in_fine, 5, 2)
        self.grid_layout_frequency.addWidget(self.button_zoom_x_in_coarse, 5, 3)

        self.grid_layout_frequency.addWidget(self.button_move_x_left_coarse, 6, 0)
        self.grid_layout_frequency.addWidget(self.button_move_x_left_fine, 6, 1)
        self.grid_layout_frequency.addWidget(self.button_move_x_right_fine, 6, 2)
        self.grid_layout_frequency.addWidget(self.button_move_x_right_coarse, 6, 3)

        self.grid_layout_voltage.addWidget(self.button_zoom_y_out_coarse, 3, 0)
        self.grid_layout_voltage.addWidget(self.button_zoom_y_out_fine, 3, 1)
        self.grid_layout_voltage.addWidget(self.button_zoom_y_in_fine, 3, 2)
        self.grid_layout_voltage.addWidget(self.button_zoom_y_in_coarse, 3, 3)

        self.grid_layout_mark.addWidget(self.label_mark_min, 1, 0)
        self.grid_layout_mark.addWidget(self.label_mark_max, 0, 0)
        self.grid_layout_mark.addWidget(self.spin_mark_min, 1, 1)
        self.grid_layout_mark.addWidget(self.spin_mark_max, 0, 1)
        self.grid_layout_mark.addWidget(self.button_mark_min_reset, 1, 2)
        self.grid_layout_mark.addWidget(self.button_mark_max_reset, 0, 2)
        self.grid_layout_mark.addWidget(self.button_zoom_to_selection, 2, 0, 1, 3)

        _value_label_interaction_flags = (Qt.LinksAccessibleByKeyboard
                                          | Qt.LinksAccessibleByMouse
                                          | Qt.TextBrowserInteraction
                                          | Qt.TextSelectableByKeyboard
                                          | Qt.TextSelectableByMouse)

        self.grid_layout.addWidget(self.group_frequency, 1, 1)
        self.grid_layout.addWidget(self.group_voltage, 2, 1)
        self.grid_layout.addWidget(self.group_mark, 3, 1)

        self.grid_layout.addWidget(self.plot_toolbar, 0, 0, 1, 2)
        self.grid_layout.addWidget(self.canvas, 1, 0, 3, 1)

        self.setCentralWidget(self.central_widget)

        self.retranslate_ui(main_window)
        main_window.adjustSize()
        QMetaObject().connectSlotsByName(main_window)

    def retranslate_ui(self, main_window):
        _translate = QCoreApplication.translate
        main_window.setWindowTitle(_translate("main_window", "Fast Sweep Viewer"))

        suffix_mhz = ' ' + _translate("main_window", "MHz")
        suffix_mv = ' ' + _translate("main_window", "mV")

        self.group_frequency.setTitle(_translate("main_window", "Frequency"))
        self.label_frequency_min.setText(_translate("main_window", "Minimum") + ':')
        self.label_frequency_max.setText(_translate("main_window", "Maximum") + ':')
        self.label_frequency_center.setText(_translate("main_window", "Center") + ':')
        self.label_frequency_span.setText(_translate("main_window", "Span") + ':')
        self.check_frequency_persists.setText(_translate("main_window", "Keep frequency range"))

        self.button_zoom_x_out_coarse.setText(_translate("main_window", "−50%"))
        self.button_zoom_x_out_fine.setText(_translate("main_window", "−10%"))
        self.button_zoom_x_in_fine.setText(_translate("main_window", "+10%"))
        self.button_zoom_x_in_coarse.setText(_translate("main_window", "+50%"))

        self.button_move_x_left_coarse.setText(_translate("main_window", "−500") + suffix_mhz)
        self.button_move_x_left_fine.setText(_translate("main_window", "−50") + suffix_mhz)
        self.button_move_x_right_fine.setText(_translate("main_window", "+50") + suffix_mhz)
        self.button_move_x_right_coarse.setText(_translate("main_window", "+500") + suffix_mhz)

        self.group_voltage.setTitle(_translate("main_window", "Voltage"))
        self.label_voltage_min.setText(_translate("main_window", "Minimum") + ':')
        self.label_voltage_max.setText(_translate("main_window", "Maximum") + ':')
        self.check_voltage_persists.setText(_translate("main_window", "Keep voltage range"))

        self.button_zoom_y_out_coarse.setText(_translate("main_window", "−50%"))
        self.button_zoom_y_out_fine.setText(_translate("main_window", "−10%"))
        self.button_zoom_y_in_fine.setText(_translate("main_window", "+10%"))
        self.button_zoom_y_in_coarse.setText(_translate("main_window", "+50%"))

        self.group_mark.setTitle(_translate("main_window", "Mark"))
        self.label_mark_min.setText(_translate("main_window", "Minimum") + ':')
        self.label_mark_max.setText(_translate("main_window", "Maximum") + ':')
        if self.button_mark_min_reset.icon().isNull():
            self.button_mark_min_reset.setText(_translate("main_window", "Reset"))
        if self.button_mark_max_reset.icon().isNull():
            self.button_mark_max_reset.setText(_translate("main_window", "Reset"))
        self.button_zoom_to_selection.setText(_translate("main_window", "Zoom to Selection"))

        self.spin_frequency_min.setSuffix(suffix_mhz)
        self.spin_frequency_max.setSuffix(suffix_mhz)
        self.spin_frequency_center.setSuffix(suffix_mhz)
        self.spin_frequency_span.setSuffix(suffix_mhz)
        self.spin_voltage_min.setSuffix(suffix_mv)
        self.spin_voltage_max.setSuffix(suffix_mv)
        self.spin_mark_min.setSuffix(suffix_mhz)
        self.spin_mark_max.setSuffix(suffix_mhz)

        self.plot_open_action.setIconText(_translate("plot toolbar action", "Open"))
        self.plot_open_action.setToolTip(_translate("plot toolbar action", "Load spectrometer data"))
        self.plot_clear_action.setIconText(_translate("plot toolbar action", "Clear"))
        self.plot_mark_action.setIconText(_translate("plot toolbar action", "Mark"))
        self.plot_save_data_action.setIconText(_translate("plot toolbar action", "Save Data"))
        self.plot_save_data_action.setToolTip(_translate("plot toolbar action", "Export data"))
        self.plot_trace_action.setIconText(_translate("plot toolbar action", "Trace"))
        self.plot_trace_multiple_action.setIconText(_translate("plot toolbar action", "Trace Multiple"))
        self.plot_copy_trace_action.setIconText(_translate("plot toolbar action", "Copy Traced"))
        self.plot_copy_trace_action.setToolTip(_translate("plot toolbar action", "Copy trace points into clipboard"))
        self.plot_save_trace_action.setIconText(_translate("plot toolbar action", "Save Traced"))
        self.plot_save_trace_action.setToolTip(_translate("plot toolbar action", "Save trace points"))

        def annotation_text(sel):
            x = sel.target[0]
            y = sel.target[1]
            line = sel.artist
            good = np.abs(line.get_xdata() - x) < TRACE_AVERAGING_RANGE
            average_y = np.mean(line.get_ydata()[good])
            setattr(sel.target, 'offset', average_y)
            return ('{:.3f}' + suffix_mhz + '\n'
                    + '{:.3f}' + suffix_mv + '\n'
                    + '{:.3f}' + suffix_mv + ' ' + _translate("main_window", "to mean")).format(x, y, y - average_y)

        def cursor_add_action(sel):
            sel.annotation.set_text(annotation_text(sel))

        self.plot_trace_cursor.connect("add", cursor_add_action)
        self.plot_trace_multiple_cursor.connect("add", cursor_add_action)

    def closeEvent(self, event):
        """ senseless joke in the loop """
        close_code = QMessageBox.No
        while close_code == QMessageBox.No:
            close = QMessageBox()
            close.setText("Are you sure?")
            close.setIcon(QMessageBox.Question)
            close.setWindowIcon(self.windowIcon())
            close.setWindowTitle(self.windowTitle())
            close.setStandardButtons(QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            close_code = close.exec()

            if close_code == QMessageBox.Yes:
                self.settings.setValue("windowGeometry", self.saveGeometry())
                self.settings.setValue("windowState", self.saveState())
                self.settings.sync()
                event.accept()
            elif close_code == QMessageBox.Cancel:
                event.ignore()
        return

    def load_config(self):
        self._loading = True
        # common settings
        if self.settings.contains('windowGeometry'):
            self.restoreGeometry(self.settings.value("windowGeometry", ""))
        else:
            window_frame = self.frameGeometry()
            desktop_center = QDesktopWidget().availableGeometry().center()
            window_frame.moveCenter(desktop_center)
            self.move(window_frame.topLeft())
        _v = self.settings.value("windowState", "")
        if isinstance(_v, str):
            self.restoreState(_v.encode())
        else:
            self.restoreState(_v)

        min_freq = self.get_config_value('frequency', 'lower',
                                         self.spin_frequency_min.minimum(),
                                         float)
        max_freq = self.get_config_value('frequency', 'upper',
                                         self.spin_frequency_min.maximum(),
                                         float)
        self.spin_frequency_min.setValue(min_freq)
        self.spin_frequency_max.setValue(max_freq)
        self.spin_frequency_min.setMaximum(max_freq)
        self.spin_frequency_max.setMinimum(min_freq)
        self.spin_frequency_span.setValue(max_freq - min_freq)
        self.spin_frequency_center.setValue(0.5 * (max_freq + min_freq))
        self.plot.set_frequency_range(lower_value=min_freq, upper_value=max_freq)

        min_voltage = self.get_config_value('voltage', 'lower',
                                            self.spin_voltage_min.minimum(),
                                            float)
        max_voltage = self.get_config_value('voltage', 'upper',
                                            self.spin_voltage_min.maximum(),
                                            float)
        self.spin_voltage_min.setValue(min_voltage)
        self.spin_voltage_max.setValue(max_voltage)
        self.spin_voltage_min.setMaximum(max_voltage)
        self.spin_voltage_max.setMinimum(min_voltage)
        self.plot.set_voltage_range(lower_value=min_voltage, upper_value=max_voltage)

        self._loading = False
        return

    def get_config_value(self, section, key, default, _type):
        if section not in self.settings.childGroups():
            return default
        self.settings.beginGroup(section)
        # print(section, key)
        v = self.settings.value(key, default, _type)
        self.settings.endGroup()
        return v

    def set_config_value(self, section, key, value):
        if self._loading:
            return
        self.settings.beginGroup(section)
        # print(section, key, value, type(value))
        self.settings.setValue(key, value)
        self.settings.endGroup()

    @staticmethod
    def load_icon(filename):
        icon = QIcon()
        icon.addPixmap(QPixmap(resource_path(os.path.join('img', filename + IMAGE_EXT))), QIcon.Normal, QIcon.Off)
        return icon

    def load_data(self):
        if self._loading:
            return
        lims = self.plot.load_data(*self.open_file_dialog(_filter="Spectrometer Settings (*.fmd);;All Files (*)"))
        if lims is not None:
            min_freq, max_freq, min_voltage, max_voltage = lims
            self.set_config_value('frequency', 'lower', min_freq)
            self.set_config_value('frequency', 'upper', max_freq)
            self.set_config_value('voltage', 'lower', min_voltage)
            self.set_config_value('voltage', 'upper', max_voltage)
            self._loading = True
            if not self.check_frequency_persists.isChecked():
                self.spin_frequency_min.setValue(min_freq)
                self.spin_frequency_max.setValue(max_freq)
                self.spin_frequency_span.setValue(max_freq - min_freq)
                self.spin_frequency_center.setValue(0.5 * (max_freq + min_freq))
                self.spin_frequency_min.setMaximum(max_freq)
                self.spin_frequency_max.setMinimum(min_freq)
            else:
                self.spin_frequency_min.setMaximum(max(max_freq, self.spin_frequency_min.value()))
                self.spin_frequency_max.setMinimum(min(min_freq, self.spin_frequency_max.value()))
            if not self.check_voltage_persists.isChecked():
                self.spin_voltage_min.setValue(min_voltage)
                self.spin_voltage_max.setValue(max_voltage)
                self.spin_voltage_min.setMaximum(max_voltage)
                self.spin_voltage_max.setMinimum(min_voltage)
            else:
                self.spin_voltage_min.setMaximum(max(max_voltage, self.spin_voltage_min.value()))
                self.spin_voltage_max.setMinimum(min(min_voltage, self.spin_voltage_max.value()))
            self.spin_mark_max.setMinimum(max(max_freq, self.spin_mark_max.minimum()))
            self.spin_mark_max.setMinimum(max(max_freq, self.spin_mark_max.minimum()))
            self._loading = False
            self.plot.set_frequency_range(lower_value=self.spin_frequency_min.value(),
                                          upper_value=self.spin_frequency_max.value())
            self.plot.set_voltage_range(lower_value=self.spin_voltage_min.value(),
                                        upper_value=self.spin_voltage_max.value())
        self.figure.tight_layout()
        self.plot_clear_action.setEnabled(True)
        self.plot_mark_action.setEnabled(True)
        self.plot_save_data_action.setEnabled(True)
        self.plot_trace_action.setEnabled(True)
        self.plot_trace_multiple_action.setEnabled(True)
        self.plot_copy_trace_action.setEnabled(True)
        self.plot_save_trace_action.setEnabled(True)

    def spin_frequency_min_changed(self, new_value):
        if self._loading:
            return
        self.set_config_value('frequency', 'lower', new_value)
        self._loading = True
        self.spin_frequency_max.setMinimum(new_value)
        self.spin_frequency_center.setValue(0.5 * (new_value + self.spin_frequency_max.value()))
        self.spin_frequency_span.setValue(self.spin_frequency_max.value() - new_value)
        self.plot.set_frequency_range(lower_value=new_value)
        self._loading = False

    def spin_frequency_max_changed(self, new_value):
        if self._loading:
            return
        self.set_config_value('frequency', 'upper', new_value)
        self._loading = True
        self.spin_frequency_min.setMaximum(new_value)
        self.spin_frequency_center.setValue(0.5 * (self.spin_frequency_min.value() + new_value))
        self.spin_frequency_span.setValue(new_value - self.spin_frequency_min.value())
        self.plot.set_frequency_range(upper_value=new_value)
        self._loading = False

    def spin_frequency_center_changed(self, new_value):
        if self._loading:
            return
        freq_span = self.spin_frequency_span.value()
        min_freq = new_value - 0.5 * freq_span
        max_freq = new_value + 0.5 * freq_span
        self._loading = True
        self.set_config_value('frequency', 'lower', min_freq)
        self.set_config_value('frequency', 'upper', max_freq)
        self.spin_frequency_min.setMaximum(max_freq)
        self.spin_frequency_max.setMinimum(min_freq)
        self.spin_frequency_min.setValue(min_freq)
        self.spin_frequency_max.setValue(max_freq)
        self.plot.set_frequency_range(upper_value=max_freq, lower_value=min_freq)
        self._loading = False

    def spin_frequency_span_changed(self, new_value):
        if self._loading:
            return
        freq_center = self.spin_frequency_center.value()
        min_freq = freq_center - 0.5 * new_value
        max_freq = freq_center + 0.5 * new_value
        self._loading = True
        self.set_config_value('frequency', 'lower', min_freq)
        self.set_config_value('frequency', 'upper', max_freq)
        self.spin_frequency_min.setMaximum(max_freq)
        self.spin_frequency_max.setMinimum(min_freq)
        self.spin_frequency_min.setValue(min_freq)
        self.spin_frequency_max.setValue(max_freq)
        self.plot.set_frequency_range(upper_value=max_freq, lower_value=min_freq)
        self._loading = False

    def button_zoom_x_clicked(self, factor):
        if self._loading:
            return
        freq_span = self.spin_frequency_span.value() * factor
        freq_center = self.spin_frequency_center.value()
        min_freq = freq_center - 0.5 * freq_span
        max_freq = freq_center + 0.5 * freq_span
        self._loading = True
        self.set_config_value('frequency', 'lower', min_freq)
        self.set_config_value('frequency', 'upper', max_freq)
        self.spin_frequency_min.setMaximum(max_freq)
        self.spin_frequency_max.setMinimum(min_freq)
        self.spin_frequency_min.setValue(min_freq)
        self.spin_frequency_max.setValue(max_freq)
        self.spin_frequency_span.setValue(freq_span)
        self.plot.set_frequency_range(upper_value=max_freq, lower_value=min_freq)
        self._loading = False

    def button_move_x_clicked(self, shift):
        if self._loading:
            return
        freq_span = self.spin_frequency_span.value()
        freq_center = self.spin_frequency_center.value() + shift
        min_freq = freq_center - 0.5 * freq_span
        max_freq = freq_center + 0.5 * freq_span
        self._loading = True
        self.set_config_value('frequency', 'lower', min_freq)
        self.set_config_value('frequency', 'upper', max_freq)
        self.spin_frequency_min.setMaximum(max_freq)
        self.spin_frequency_max.setMinimum(min_freq)
        self.spin_frequency_min.setValue(min_freq)
        self.spin_frequency_max.setValue(max_freq)
        self.spin_frequency_center.setValue(freq_center)
        self.plot.set_frequency_range(upper_value=max_freq, lower_value=min_freq)
        self._loading = False

    def spin_voltage_min_changed(self, new_value):
        if self._loading:
            return
        self.set_config_value('voltage', 'lower', new_value)
        self._loading = True
        self.spin_voltage_max.setMinimum(new_value)
        self.plot.set_voltage_range(lower_value=new_value)
        self._loading = False

    def spin_voltage_max_changed(self, new_value):
        if self._loading:
            return
        self.set_config_value('voltage', 'upper', new_value)
        self._loading = True
        self.spin_voltage_min.setMaximum(new_value)
        self.plot.set_voltage_range(upper_value=new_value)
        self._loading = False

    def button_zoom_y_clicked(self, factor):
        if self._loading:
            return
        min_voltage = self.spin_voltage_min.value()
        max_voltage = self.spin_voltage_max.value()
        voltage_span = abs(max_voltage - min_voltage) * factor
        voltage_center = (max_voltage + min_voltage) * 0.5
        min_voltage = voltage_center - 0.5 * voltage_span
        max_voltage = voltage_center + 0.5 * voltage_span
        self._loading = True
        self.set_config_value('voltage', 'lower', min_voltage)
        self.set_config_value('voltage', 'upper', max_voltage)
        self.spin_voltage_min.setMaximum(max_voltage)
        self.spin_voltage_max.setMinimum(min_voltage)
        self.spin_voltage_min.setValue(min_voltage)
        self.spin_voltage_max.setValue(max_voltage)
        self.plot.set_voltage_range(upper_value=max_voltage, lower_value=min_voltage)
        self._loading = False

    def spin_mark_min_changed(self, new_value):
        if self._loading:
            return
        self._loading = True
        self.spin_mark_max.setMinimum(new_value)
        self.plot.set_mark(lower_value=new_value, upper_value=self.spin_mark_max.value())
        self._loading = False

    def spin_mark_max_changed(self, new_value):
        if self._loading:
            return
        self._loading = True
        self.spin_mark_min.setMaximum(new_value)
        self.plot.set_mark(lower_value=self.spin_mark_min.value(), upper_value=new_value)
        self._loading = False

    def button_mark_min_reset_clicked(self):
        self.spin_mark_min.setValue(self.spin_mark_min.minimum())

    def button_mark_max_reset_clicked(self):
        self.spin_mark_max.setValue(self.spin_mark_max.maximum())

    def button_zoom_to_selection_clicked(self):
        self.spin_frequency_min.setValue(self.spin_mark_min.value())
        self.spin_frequency_max.setValue(self.spin_mark_max.value())

    def plot_mark_action_toggled(self, new_value):
        if self.plot_toolbar.mode == 'zoom rect':
            self.plot_toolbar.zoom()
        elif self.plot_toolbar.mode == 'pan/zoom':
            self.plot_toolbar.pan()
        if new_value:
            self.plot_trace_action.setChecked(False)
            self.plot_trace_multiple_action.setChecked(False)

    def plot_trace_action_toggled(self, new_value):
        if new_value:
            self.plot_mark_action.setChecked(False)
            self.plot_trace_multiple_action.setChecked(False)
            self.canvas.setFocus()
        if self.plot_toolbar.mode == 'zoom rect':
            self.plot_toolbar.zoom()
        elif self.plot_toolbar.mode == 'pan/zoom':
            self.plot_toolbar.pan()
        self.plot_trace_cursor.enabled = new_value
        self.plot_trace_cursor.visible = new_value
        self.plot_trace_multiple_cursor.enabled = False
        self.plot_trace_multiple_cursor.visible = False

    def plot_trace_multiple_action_toggled(self, new_value):
        if new_value:
            self.plot_mark_action.setChecked(False)
            self.plot_trace_action.setChecked(False)
            self.canvas.setFocus()
        if self.plot_toolbar.mode == 'zoom rect':
            self.plot_toolbar.zoom()
        elif self.plot_toolbar.mode == 'pan/zoom':
            self.plot_toolbar.pan()
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
            table += '{1}{0}{2}{0}{3}\n'.format(sep, x, y, y - offset)
        if table:
            pyperclip.copy(table)

    def plot_save_trace_action_triggered(self):
        picked_x = []
        picked_y = []
        picked_dy = []
        selections = []
        if self.plot_trace_multiple_cursor.enabled:
            selections = self.plot_trace_multiple_cursor.selections
        elif self.plot_trace_cursor.enabled:
            selections = self.plot_trace_cursor.selections
        for sel in selections:
            x, y = sel.target.tolist()
            picked_x.append(x)
            picked_y.append(y)
            picked_dy.append(y - sel.target.offset)
        if not picked_x or not picked_y:
            return
        filename, _filter = self.save_file_dialog(_filter="CSV (*.csv);;XLSX (*.xlsx)")
        if filename:
            sep = '\t'
            self.plot.save_arbitrary_data((picked_x, picked_y, picked_dy), filename, _filter,
                                          csv_header=(sep.join(('frequency', 'voltage', 'voltage_to_mean')) + '\n'
                                                      + sep.join(('MHz', 'mV', 'mV'))),
                                          csv_sep=sep,
                                          xlsx_header=['Frequency [MHz]', 'Voltage [mV]', 'Voltage to Mean [mV]'])

    def plot_on_click(self, event):
        if self._loading:
            return
        if event.inaxes is not None:
            if event.dblclick \
                    and not self.plot_mark_action.isChecked() \
                    and not self.plot_trace_action.isChecked() \
                    and not self.plot_trace_multiple_action.isChecked():
                min_freq, max_freq, min_voltage, max_voltage = self.plot.on_dblclick(event)
                self.set_config_value('frequency', 'lower', min_freq)
                self.set_config_value('frequency', 'upper', max_freq)
                self.set_config_value('voltage', 'lower', min_voltage)
                self.set_config_value('voltage', 'upper', max_voltage)
                self._loading = True
                self.spin_frequency_min.setValue(min_freq)
                self.spin_frequency_max.setValue(max_freq)
                self.spin_frequency_min.setMaximum(max_freq)
                self.spin_frequency_max.setMinimum(min_freq)
                self.spin_frequency_span.setValue(max_freq - min_freq)
                self.spin_frequency_center.setValue(0.5 * (max_freq + min_freq))
                self.spin_voltage_min.setValue(min_voltage)
                self.spin_voltage_max.setValue(max_voltage)
                self.spin_voltage_min.setMaximum(max_voltage)
                self.spin_voltage_max.setMinimum(min_voltage)
                self._loading = False
            elif self.plot_mark_action.isChecked():
                if self.plot_toolbar.mode:
                    self.plot_mark_action.setChecked(False)
                else:
                    if event.button == 1:
                        self.spin_mark_min.setValue(event.xdata)
                    else:
                        self.spin_mark_max.setValue(event.xdata)

    def clear(self):
        self.plot.clear()
        for sel in self.plot_trace_multiple_cursor.selections:
            self.plot_trace_multiple_cursor.remove_selection(sel)
        for sel in self.plot_trace_cursor.selections:
            self.plot_trace_cursor.remove_selection(sel)
        self.plot_mark_action.setChecked(False)
        self.plot_trace_action.setChecked(False)
        self.plot_trace_multiple_action.setChecked(False)
        self.plot_clear_action.setEnabled(False)
        self.plot_mark_action.setEnabled(False)
        self.plot_save_data_action.setEnabled(False)
        self.plot_trace_action.setEnabled(False)
        self.plot_trace_multiple_action.setEnabled(False)
        self.plot_copy_trace_action.setEnabled(False)
        self.plot_save_trace_action.setEnabled(False)

    def open_file_dialog(self, _filter=''):
        directory = self.get_config_value('open', 'location', '', str)
        # native dialog misbehaves when running inside snap but Qt dialog is tortoise-like in NT
        options = QFileDialog.DontUseNativeDialog if os.name != 'nt' else QFileDialog.DontUseSheet
        filename, _filter = QFileDialog.getOpenFileName(filter=_filter,
                                                        directory=directory,
                                                        options=options)
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
        self.set_config_value('save', 'location', os.path.split(filename)[0])
        self.set_config_value('save', 'filter', _filter)
        return filename, _filter


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = App()
    window.show()
    app.exec_()
