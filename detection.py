# -*- coding: utf-8 -*-
from typing import Final

import numpy as np


LINE_WIDTH: Final[float] = 2.6


def remove_spikes(sequence: np.ndarray, iterations: int = 1) -> np.ndarray:
    from scipy import ndimage

    sequence = ndimage.binary_dilation(sequence, iterations=iterations)
    sequence = ndimage.binary_erosion(sequence, iterations=iterations + 1)
    sequence = ndimage.binary_dilation(sequence, iterations=1)
    return sequence


def correlation(model_y, another_x: np.ndarray, another_y: np.ndarray) -> np.ndarray:
    from scipy.signal import butter, lfilter

    def butter_bandpass_filter(data: np.ndarray, low_cut: float, high_cut: float, order: int = 5):
        def butter_bandpass():
            nyq: float = 0.5 * fs
            low: float = low_cut / nyq
            high: float = high_cut / nyq
            if low > 0. and high < fs:
                return butter(order, [low, high], btype='bandpass')
            if low > 0. and high >= fs:
                return butter(order, low, btype='highpass')
            if low <= 0. and high < fs:
                return butter(order, high, btype='lowpass')
            raise ValueError

        return lfilter(*butter_bandpass(), data)

    if another_y.size:
        fs: float = 1.0 / (another_x[1] - another_x[0])
        another_y_filtered: np.ndarray = butter_bandpass_filter(another_y,
                                                                low_cut=0.005 * fs, high_cut=np.inf,
                                                                order=5)
        _corr: np.ndarray = np.correlate(another_y_filtered, model_y, 'same')
        _corr -= np.mean(_corr)
        _corr /= np.std(_corr)
        return _corr
    return np.empty(0)


def peaks_positions(data_x: np.ndarray, data_y: np.ndarray, threshold: float = 0.0046228) -> np.ndarray:
    import pandas as pd
    if data_x.size < 2 or data_y.size < 2:
        # nothing to do
        return np.empty(0)

    std: np.ndarray = pd.Series(data_y).rolling(round(LINE_WIDTH / (data_x[1] - data_x[0])),
                                                center=True).std().to_numpy()
    match: np.ndarray = np.array((std >= np.nanquantile(std, 1.0 - threshold)))
    match = remove_spikes(match, iterations=8)
    match[0] = match[-1] = False
    islands: np.ndarray = np.argwhere(np.diff(match)).reshape(-1, 2)
    peaks: np.ndarray = np.array([i[0] + np.argmax(data_y[i[0]:i[1]])
                                  for i in islands
                                  if (np.argmax(data_y[i[0]:i[1]]) not in (0, i[1] - i[0]))])
    return peaks


if __name__ == '__main__':
    def main():
        """ try and error function """
        from matplotlib import pyplot as plt

        # data: np.ndarray = np.loadtxt('lines.csv')

        # f: np.ndarray = np.arange(118000.0, 118150.0, 0.1)
        # v: np.ndarray = np.random.normal(size=(f.size,))
        # model: np.ndarray = np.loadtxt('averaged fs signal.csv')
        # data: np.ndarray = np.column_stack((f, correlation(model, f, v)))
        # plt.plot(f, v, label='initial')

        f: np.ndarray = np.arange(118000.0, 175000.0, 0.1)
        v: np.ndarray = np.loadtxt('mo4/030820/OCS2.frd', usecols=(0,)).ravel()
        v -= np.median(v)
        model = np.loadtxt('averaged fs signal filtered.csv')
        plt.xlim(134198.5 - 10, 134198.5 + 10)
        data: np.ndarray = correlation(model, f, v)
        plt.plot(f, v, label='initial')

        found_lines = peaks_positions(f, data)
        if found_lines.size:
            print(f'found {found_lines.size} lines:')
            for ff, fd in zip(f[found_lines], v[found_lines]):
                print(f'{ff:.3f}\t{-fd:.6f}')
            plt.plot(f[found_lines], v[found_lines], ls='', marker='o')
        plt.tight_layout()
        plt.legend(loc='upper left')
        plt.grid()
        plt.show()


    main()
