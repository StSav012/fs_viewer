# -*- coding: utf-8 -*-
import os
import numpy as np
import pandas as pd
from matplotlib.pyplot import Line2D
from matplotlib.legend import DraggableLegend

FRAME_SIZE = 50.
LINES_COUNT = 2
GRID_LINES_COUNT = 32


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


class Plot:
    def __init__(self, figure, canvas):
        self._canvas = canvas

        self._figure = figure
        self._figure.set_xlabel('Frequency [MHz]')
        self._figure.set_ylabel('Voltage [mV]')
        self._figure.format_coord = lambda x, y: '{:.3f} V\n{:.3f} MHz'.format(x, y)

        self._legend = None

        self._plot_lines = [self._figure.plot(np.empty(0), label='_*empty*_ {} (not marked)'.format(i + 1))[0]
                            for i in range(LINES_COUNT)]
        self._plot_mark_lines = [self._figure.plot(np.empty(0), label='_*empty*_ {} (marked)'.format(i + 1))[0]
                                 for i in range(LINES_COUNT)]
        self._plot_lines_labels = ['_*empty*_'] * LINES_COUNT
        self._plot_frequencies = [np.empty(0)] * LINES_COUNT
        self._plot_voltages = [np.empty(0)] * LINES_COUNT

        self._min_frequency = None
        self._max_frequency = None
        self._min_voltage = None
        self._max_voltage = None
        self._min_mark = None
        self._max_mark = None

        self._figure.callbacks.connect('xlim_changed', self.on_xlim_changed)
        # self._figure.callbacks.connect('ylim_changed', self.on_ylim_changed)
        self._axvlines = [self._figure.axvline(np.nan, color='grey', linewidth=0.5,
                                               label='_ vertical line {}'.format(i + 1))
                          for i in range(GRID_LINES_COUNT)]

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

    # @staticmethod
    # def on_xlim_changed(axes):
    #     xlim = axes.get_xlim()
    #     autoscale = True
    #     for line in axes.lines:
    #         data = np.array(line.get_xdata())
    #         if data.size < 2:
    #             continue
    #         if len(data) > 0 and (min(xlim) > np.min(data) or max(xlim) < np.max(data)):
    #             autoscale = False
    #     axes.set_autoscalex_on(autoscale)

    def on_xlim_changed(self, axes):
        xlim = axes.get_xlim()
        self.make_grid(xlim)

    # @staticmethod
    # def on_ylim_changed(axes):
    #     ylim = axes.get_ylim()
    #     autoscale = True
    #     for line in axes.lines:
    #         data = np.array(line.get_ydata())
    #         if data.size < 2:
    #             continue
    #         if len(data) > 0 and (min(ylim) > np.min(data) and max(ylim) < np.max(data)):
    #             autoscale = False
    #     axes.set_autoscaley_on(autoscale)

    @property
    def lines(self):
        for member in self.__dict__.values():
            if isinstance(member, Line2D):
                yield member
            elif isinstance(member, list):
                yield from filter(lambda submember: isinstance(submember, Line2D), member)

    @property
    def marked_lines(self):
        for member in self._plot_mark_lines:
            if isinstance(member, Line2D):
                yield member
            elif isinstance(member, list):
                yield from filter(lambda submember: isinstance(submember, Line2D), member)

    @property
    def labels(self):
        yield from self._plot_lines_labels

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

    def draw_data(self, xs, ys,
                  marks):
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
            self._plot_mark_lines[i].set_data(middle_x, middle_y)
            self._plot_mark_lines[i].set_label(self._plot_lines_labels[i] + ' (marked)')
        self._canvas.draw_idle()

    def clear(self):
        self._plot_voltages = [np.empty(0)] * LINES_COUNT
        self._plot_frequencies = [np.empty(0)] * LINES_COUNT
        for line in self._plot_lines:
            line.set_data(np.empty(0), np.empty(0))
        for line in self._plot_mark_lines:
            line.set_data(np.empty(0), np.empty(0))
        self._plot_lines_labels = ['_*empty*_'] * LINES_COUNT
        if self._legend is not None:
            self._legend.legend.remove()
        self._canvas.draw_idle()

    def load_data(self, filename, _filter):
        if not filename:
            return None
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
            self.make_grid((self._min_frequency, self._max_frequency))
            self.draw_data(self._plot_frequencies, self._plot_voltages, (self._min_mark, self._max_mark))
            if any(map(lambda l: not l.startswith('_'), self._plot_lines_labels)):
                if self._legend is not None:
                    self._legend.legend.remove()
                labels = []
                lines = []
                for i, lbl in enumerate(self._plot_lines_labels):
                    if not lbl.startswith('_'):
                        labels.append(lbl)
                        lines.append(self._plot_mark_lines[i])
                self._legend = DraggableLegend(self._figure.legend(lines, labels), use_blit=True)
            return self._min_frequency, self._max_frequency, self._min_voltage, self._max_voltage
        return None

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
            np.savetxt(filename, data,
                       delimiter=sep,
                       header=sep.join(('frequency', 'voltage')) + '\n' + sep.join(('MHz', 'mV')),
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

    @staticmethod
    def save_arbitrary_data(x, y, filename, _filter, *,
                            csv_header='', csv_sep='\t',
                            xlsx_header=True, sheet_name='Markings'):
        if not filename:
            return
        filename_parts = os.path.splitext(filename)
        if 'CSV' in _filter:
            if filename_parts[1] != '.csv':
                filename += '.csv'
            data = np.vstack((x, y)).transpose()
            np.savetxt(filename, data,
                       delimiter=csv_sep,
                       header=csv_header,
                       fmt='%s')
        elif 'XLSX' in _filter:
            if filename_parts[1] != '.xlsx':
                filename += '.xlsx'
            with pd.ExcelWriter(filename) as writer:
                data = np.vstack((x, y)).transpose()
                df = pd.DataFrame(data)
                df.to_excel(writer, index=False, header=xlsx_header,
                            sheet_name=sheet_name)
