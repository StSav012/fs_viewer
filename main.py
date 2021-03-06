﻿#!/usr/bin/python3
# -*- coding: utf-8 -*-

# TODO: save and load trace balloons

import os
import sys

import matplotlib.style
from PyQt5.QtCore import QCoreApplication, QLibraryInfo, QLocale, QSettings, QTranslator, Qt
from PyQt5.QtWidgets import QApplication, QCheckBox, QDesktopWidget, QDoubleSpinBox, QFileDialog, QGridLayout, \
    QGroupBox, QLabel, QMainWindow, QMessageBox, QPushButton, QWidget
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

import backend
from backend import NavigationToolbar as NavigationToolbar

matplotlib.style.use('fast')

MAX_FREQUENCY = 175000.0
MIN_FREQUENCY = 118000.0
MAX_VOLTAGE = 617.0
MIN_VOLTAGE = -MAX_VOLTAGE


class App(QMainWindow):
    def __init__(self):
        super().__init__(flags=Qt.WindowFlags())
        self.settings = QSettings("SavSoft", "Fast Sweep Viewer")

        # prevent config from being re-written while loading
        self._loading = True

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
            b.setIcon(backend.load_icon('reset'))
        self.button_zoom_to_selection = QPushButton(self.group_mark)

        # Find Lines box
        self.group_find_lines = QGroupBox(self.central_widget)
        self.grid_layout_find_lines = QGridLayout(self.group_find_lines)
        self.label_threshold = QLabel(self.group_find_lines)
        self.spin_threshold = QDoubleSpinBox(self.group_find_lines)
        self.spin_threshold.setMinimum(1.0)
        self.spin_threshold.setMaximum(1000.0)
        self.button_find_lines = QPushButton(self.group_find_lines)
        self.button_clear_lines = QPushButton(self.group_find_lines)
        self.button_prev_line = QPushButton(self.group_find_lines)
        self.button_next_line = QPushButton(self.group_find_lines)

        # plot
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setFocusPolicy(Qt.ClickFocus)
        self.plot_toolbar = NavigationToolbar(self.canvas, self, parameters_icon=backend.load_icon('configure'))
        self.legend_figure = Figure(constrained_layout=True, frameon=False)
        self.legend_canvas = FigureCanvas(self.legend_figure)
        self.plot = backend.Plot(figure=self.figure,
                                 legend_figure=self.legend_figure,
                                 toolbar=self.plot_toolbar,
                                 settings=self.settings,
                                 on_xlim_changed=self.on_xlim_changed,
                                 on_ylim_changed=self.on_ylim_changed,
                                 on_data_loaded=self.load_data)

        self.setup_ui()

        # config
        self.load_config()

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
        self.check_frequency_persists.toggled.connect(self.check_frequency_persists_toggled)

        self.spin_voltage_min.valueChanged.connect(self.spin_voltage_min_changed)
        self.spin_voltage_max.valueChanged.connect(self.spin_voltage_max_changed)
        self.button_zoom_y_out_coarse.clicked.connect(lambda: self.button_zoom_y_clicked(1. / 0.5))
        self.button_zoom_y_out_fine.clicked.connect(lambda: self.button_zoom_y_clicked(1. / 0.9))
        self.button_zoom_y_in_fine.clicked.connect(lambda: self.button_zoom_y_clicked(0.9))
        self.button_zoom_y_in_coarse.clicked.connect(lambda: self.button_zoom_y_clicked(0.5))
        self.check_voltage_persists.toggled.connect(self.check_voltage_persists_toggled)

        self.spin_mark_min.valueChanged.connect(self.spin_mark_min_changed)
        self.spin_mark_max.valueChanged.connect(self.spin_mark_max_changed)
        self.button_mark_min_reset.clicked.connect(self.button_mark_min_reset_clicked)
        self.button_mark_max_reset.clicked.connect(self.button_mark_max_reset_clicked)
        self.button_zoom_to_selection.clicked.connect(self.button_zoom_to_selection_clicked)

        self.spin_threshold.valueChanged.connect(lambda new_value:
                                                 self.set_config_value('lineSearch', 'threshold', new_value))
        self.button_find_lines.clicked.connect(lambda: self.plot.find_lines(self.spin_threshold.value()))
        self.button_clear_lines.clicked.connect(self.plot.clear_lines)
        self.button_prev_line.clicked.connect(self.prev_found_line)
        self.button_next_line.clicked.connect(self.next_found_line)

        self.mpl_connect_cid = self.canvas.mpl_connect('button_press_event', self.plot_on_click)

    def setup_ui(self):
        self.resize(484, 441)
        self.setWindowIcon(backend.load_icon('sweep'))

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

        self.grid_layout_find_lines.addWidget(self.label_threshold, 0, 0)
        self.grid_layout_find_lines.addWidget(self.spin_threshold, 0, 1)
        self.grid_layout_find_lines.addWidget(self.button_find_lines, 1, 0, 1, 2)
        self.grid_layout_find_lines.addWidget(self.button_clear_lines, 2, 0, 1, 2)
        self.grid_layout_find_lines.addWidget(self.button_prev_line, 3, 0)
        self.grid_layout_find_lines.addWidget(self.button_next_line, 3, 1)

        _value_label_interaction_flags = (Qt.LinksAccessibleByKeyboard
                                          | Qt.LinksAccessibleByMouse
                                          | Qt.TextBrowserInteraction
                                          | Qt.TextSelectableByKeyboard
                                          | Qt.TextSelectableByMouse)

        self.grid_layout.addWidget(self.group_frequency, 2, 1)
        self.grid_layout.addWidget(self.group_voltage, 3, 1)
        self.grid_layout.addWidget(self.group_mark, 4, 1)
        self.grid_layout.addWidget(self.group_find_lines, 5, 1)

        self.grid_layout.addWidget(self.plot_toolbar, 0, 0, 1, 2)
        self.grid_layout.addWidget(self.canvas, 1, 0, 5, 1)
        self.grid_layout.addWidget(self.legend_canvas, 1, 1)

        self.setCentralWidget(self.central_widget)

        self.translate_ui()
        self.adjustSize()

    def translate_ui(self):
        _translate = QCoreApplication.translate
        self.setWindowTitle(_translate('main window', 'Fast Sweep Viewer'))

        self.plot_toolbar.parameters_title = _translate('plot config window title', 'Figure options')

        suffix_mhz = ' ' + _translate('unit', 'MHz')
        suffix_mv = ' ' + _translate('unit', 'mV')

        self.group_frequency.setTitle(_translate('main window', 'Frequency'))
        self.label_frequency_min.setText(_translate('main window', 'Minimum') + ':')
        self.label_frequency_max.setText(_translate('main window', 'Maximum') + ':')
        self.label_frequency_center.setText(_translate('main window', 'Center') + ':')
        self.label_frequency_span.setText(_translate('main window', 'Span') + ':')
        self.check_frequency_persists.setText(_translate('main window', 'Keep frequency range'))

        self.button_zoom_x_out_coarse.setText(_translate('main window', '−50%'))
        self.button_zoom_x_out_fine.setText(_translate('main window', '−10%'))
        self.button_zoom_x_in_fine.setText(_translate('main window', '+10%'))
        self.button_zoom_x_in_coarse.setText(_translate('main window', '+50%'))

        self.button_move_x_left_coarse.setText(_translate('main window', '−500') + suffix_mhz)
        self.button_move_x_left_fine.setText(_translate('main window', '−50') + suffix_mhz)
        self.button_move_x_right_fine.setText(_translate('main window', '+50') + suffix_mhz)
        self.button_move_x_right_coarse.setText(_translate('main window', '+500') + suffix_mhz)

        self.group_voltage.setTitle(_translate('main window', 'Voltage'))
        self.label_voltage_min.setText(_translate('main window', 'Minimum') + ':')
        self.label_voltage_max.setText(_translate('main window', 'Maximum') + ':')
        self.check_voltage_persists.setText(_translate('main window', 'Keep voltage range'))

        self.button_zoom_y_out_coarse.setText(_translate('main window', '−50%'))
        self.button_zoom_y_out_fine.setText(_translate('main window', '−10%'))
        self.button_zoom_y_in_fine.setText(_translate('main window', '+10%'))
        self.button_zoom_y_in_coarse.setText(_translate('main window', '+50%'))

        self.group_mark.setTitle(_translate('main window', 'Selection'))
        self.label_mark_min.setText(_translate('main window', 'Minimum') + ':')
        self.label_mark_max.setText(_translate('main window', 'Maximum') + ':')
        if self.button_mark_min_reset.icon().isNull():
            self.button_mark_min_reset.setText(_translate('main window', 'Reset'))
        if self.button_mark_max_reset.icon().isNull():
            self.button_mark_max_reset.setText(_translate('main window', 'Reset'))
        self.button_zoom_to_selection.setText(_translate('main window', 'Zoom to Selection'))

        self.group_find_lines.setTitle(_translate('main window', 'Find Lines'))
        self.group_find_lines.setToolTip(_translate('main window',
                                                    'Try to detect lines automatically'))
        self.label_threshold.setText(_translate('main window', 'Search threshold') + ':')
        self.button_find_lines.setText(_translate('main window', 'Find Lines'))
        self.button_clear_lines.setText(_translate('main window', 'Clear Lines'))
        self.button_prev_line.setText(_translate('main window', 'Previous Line'))
        self.button_next_line.setText(_translate('main window', 'Next Line'))

        self.spin_frequency_min.setSuffix(suffix_mhz)
        self.spin_frequency_max.setSuffix(suffix_mhz)
        self.spin_frequency_center.setSuffix(suffix_mhz)
        self.spin_frequency_span.setSuffix(suffix_mhz)
        self.spin_voltage_min.setSuffix(suffix_mv)
        self.spin_voltage_max.setSuffix(suffix_mv)
        self.spin_mark_min.setSuffix(suffix_mhz)
        self.spin_mark_max.setSuffix(suffix_mhz)

    def closeEvent(self, event):
        """ senseless joke in the loop """
        _translate = QCoreApplication.translate
        close_code = QMessageBox.No
        while close_code == QMessageBox.No:
            close = QMessageBox()
            close.setText(_translate('main window', 'Are you sure?'))
            close.setIcon(QMessageBox.Question)
            close.setWindowIcon(self.windowIcon())
            close.setWindowTitle(self.windowTitle())
            close.setStandardButtons(QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            close_code = close.exec()

            if close_code == QMessageBox.Yes:
                self.settings.setValue('windowGeometry', self.saveGeometry())
                self.settings.setValue('windowState', self.saveState())
                self.settings.sync()
                event.accept()
            elif close_code == QMessageBox.Cancel:
                event.ignore()
        return

    def load_config(self):
        self._loading = True
        # common settings
        if self.settings.contains('windowGeometry'):
            self.restoreGeometry(self.settings.value('windowGeometry', ''))
        else:
            window_frame = self.frameGeometry()
            desktop_center = QDesktopWidget().availableGeometry().center()
            window_frame.moveCenter(desktop_center)
            self.move(window_frame.topLeft())
        _v = self.settings.value('windowState', '')
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
        self.check_frequency_persists.setChecked(self.get_config_value('frequency', 'persists', False, bool))

        min_voltage = self.get_config_value('voltage', 'lower', self.spin_voltage_min.minimum(), float)
        max_voltage = self.get_config_value('voltage', 'upper', self.spin_voltage_min.maximum(), float)
        self.spin_voltage_min.setValue(min_voltage)
        self.spin_voltage_max.setValue(max_voltage)
        self.spin_voltage_min.setMaximum(max_voltage)
        self.spin_voltage_max.setMinimum(min_voltage)
        self.plot.set_voltage_range(lower_value=min_voltage, upper_value=max_voltage)
        self.check_voltage_persists.setChecked(self.get_config_value('voltage', 'persists', False, bool))

        self.spin_threshold.setValue(self.get_config_value('lineSearch', 'threshold', 200.0, float))

        self._loading = False
        return

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
        if self._loading:
            return
        self.settings.beginGroup(section)
        # print(section, key, value, type(value))
        self.settings.setValue(key, value)
        self.settings.endGroup()

    def load_data(self, limits):
        if self._loading:
            return
        if limits is not None:
            min_freq, max_freq, min_voltage, max_voltage = limits
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
            self.spin_mark_min.setMinimum(min(min_freq, self.spin_mark_min.minimum()))
            self.spin_mark_max.setMaximum(max(max_freq, self.spin_mark_max.maximum()))
            self._loading = False
            self.plot.set_frequency_range(lower_value=self.spin_frequency_min.value(),
                                          upper_value=self.spin_frequency_max.value())
            self.plot.set_voltage_range(lower_value=self.spin_voltage_min.value(),
                                        upper_value=self.spin_voltage_max.value())
        self.figure.tight_layout()

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

    def check_frequency_persists_toggled(self, new_value):
        if self._loading:
            return
        self.set_config_value('frequency', 'persists', new_value)

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

    def check_voltage_persists_toggled(self, new_value):
        if self._loading:
            return
        self.set_config_value('voltage', 'persists', new_value)

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

    def prev_found_line(self):
        self.spin_frequency_center.setValue(self.plot.prev_found_line(self.spin_frequency_center.value()))

    def next_found_line(self):
        self.spin_frequency_center.setValue(self.plot.next_found_line(self.spin_frequency_center.value()))

    def plot_on_click(self, event):
        if self._loading:
            return
        if event.inaxes is not None:
            if event.dblclick \
                    and not self.plot.mark_mode \
                    and not self.plot.trace_mode \
                    and not self.plot.trace_multiple_mode:
                min_freq, max_freq, min_voltage, max_voltage = self.plot.on_double_click(event)
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
            elif self.plot.mark_mode:
                if self.plot.mode:
                    self.plot.actions_off()
                else:
                    if event.button == 1:
                        self.spin_mark_min.setValue(event.xdata)
                    else:
                        self.spin_mark_max.setValue(event.xdata)

    def open_file_dialog(self, _filter=''):
        directory = self.get_config_value('open', 'location', '', str)
        # native dialog misbehaves when running inside snap but Qt dialog is tortoise-like in NT
        options = QFileDialog.DontUseNativeDialog if os.name != 'nt' else QFileDialog.DontUseSheet
        filename, _filter = QFileDialog.getOpenFileName(filter=_filter,
                                                        directory=directory,
                                                        options=options)
        self.set_config_value('open', 'location', os.path.split(filename)[0])
        return filename, _filter

    def on_xlim_changed(self, xlim):
        if not hasattr(self, 'plot'):
            return
        min_freq, max_freq = xlim
        self.set_config_value('frequency', 'lower', min_freq)
        self.set_config_value('frequency', 'upper', max_freq)
        self._loading = True
        self.spin_frequency_min.setValue(min_freq)
        self.spin_frequency_max.setValue(max_freq)
        self.spin_frequency_span.setValue(max_freq - min_freq)
        self.spin_frequency_center.setValue(0.5 * (max_freq + min_freq))
        self.spin_frequency_min.setMaximum(max_freq)
        self.spin_frequency_max.setMinimum(min_freq)
        self.spin_mark_min.setMinimum(min(min_freq, self.spin_mark_min.minimum()))
        self.spin_mark_max.setMaximum(max(max_freq, self.spin_mark_max.maximum()))
        self._loading = False
        self.plot.set_frequency_range(lower_value=self.spin_frequency_min.value(),
                                      upper_value=self.spin_frequency_max.value())

    def on_ylim_changed(self, ylim):
        if not hasattr(self, 'plot'):
            return
        min_voltage, max_voltage = ylim
        self.set_config_value('voltage', 'lower', min_voltage)
        self.set_config_value('voltage', 'upper', max_voltage)
        self._loading = True
        self.spin_voltage_min.setValue(min_voltage)
        self.spin_voltage_max.setValue(max_voltage)
        self.spin_voltage_min.setMaximum(max_voltage)
        self.spin_voltage_max.setMinimum(min_voltage)
        self._loading = False
        self.plot.set_voltage_range(lower_value=self.spin_voltage_min.value(),
                                    upper_value=self.spin_voltage_max.value())


if __name__ == '__main__':
    app = QApplication(sys.argv)

    qt_translator = QTranslator()
    qt_translator.load("qt_" + QLocale.system().bcp47Name(),
                       QLibraryInfo.location(QLibraryInfo.TranslationsPath))
    app.installTranslator(qt_translator)
    qtbase_translator = QTranslator()
    qtbase_translator.load("qtbase_" + QLocale.system().bcp47Name(),
                           QLibraryInfo.location(QLibraryInfo.TranslationsPath))
    app.installTranslator(qtbase_translator)
    my_translator = QTranslator()
    my_translator.load(QLocale.system().bcp47Name(), backend.resource_path('translations'))
    app.installTranslator(my_translator)

    window = App()
    window.show()
    app.exec_()
