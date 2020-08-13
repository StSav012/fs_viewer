# -*- coding: utf-8 -*-

import numpy as np
from scipy import ndimage

if __name__ == '__main__':
    from matplotlib import pyplot as plt


LINE_WIDTH = 2.6


def fragment(sequence, grid, center, half_width):
    i = np.searchsorted(grid, center - half_width)
    j = np.searchsorted(grid, center)
    k = 2 * j - i
    if i > j:
        i, j = j, i
    if j > k:
        j, k = k, j
    return sequence[i:k]


def fragments(sequence, grid, center, half_width):
    i = np.searchsorted(grid, center - half_width)
    j = np.searchsorted(grid, center)
    k = 2 * j - i
    if i > j:
        i, j = j, i
    if j > k:
        j, k = k, j
    return sequence[i:j], sequence[j:k]


def remove_spikes(sequence):
    sequence_right = np.roll(sequence, 1)
    sequence_left = np.roll(sequence, -1)
    spikes = np.not_equal(sequence, sequence_left) & np.equal(sequence_right, sequence_left)
    sequence[spikes] = sequence_left[spikes]
    return sequence


def correlation(model_y, another_x: np.ndarray, another_y: np.ndarray) -> np.ndarray:
    from scipy.signal import butter, lfilter

    def butter_bandpass_filter(data, low_cut, high_cut, order=5):
        def butter_bandpass():
            nyq = 0.5 * fs
            low = low_cut / nyq
            high = high_cut / nyq
            if low > 0. and high < fs:
                return butter(order, [low, high], btype='bandpass')
            if low > 0. and high >= fs:
                return butter(order, low, btype='highpass')
            if low <= 0. and high < fs:
                return butter(order, high, btype='lowpass')
            raise ValueError

        return lfilter(*butter_bandpass(), data)

    if another_y.size:
        _corr: np.ndarray = np.correlate(another_y, model_y, 'same')
        _corr -= np.mean(_corr)
        _corr /= np.std(_corr)
        fs: float = 1.0 / (another_x[1] - another_x[0])
        _corr = butter_bandpass_filter(_corr, low_cut=0.005 * fs, high_cut=np.inf,
                                       order=5)
        return _corr
    return np.empty(0)


def positions(data_x, data_y) -> np.ndarray:
    if not data_x.size or not data_y.size:
        # nothing to do
        return np.empty(0)
    # correlate the signal with itself reversed around each point: lines are symmetrical, steps are asymmetrical
    core: np.ndarray = np.copy(data_y)
    anti_core: np.ndarray = np.copy(data_y)
    for f in range(data_x.shape[0]):
        if data_x[f] - data_x[0] <= LINE_WIDTH:
            core[f] = np.nan
            anti_core[f] = np.nan
        elif data_x[-1] - data_x[f] <= LINE_WIDTH:
            core[f] = np.nan
            anti_core[f] = np.nan
        else:
            signal_fragments = fragments(data_y, data_x, data_x[f], 0.5 * LINE_WIDTH)
            core[f] = np.mean(signal_fragments[0] - signal_fragments[1][::-1])
            anti_core[f] = np.mean(signal_fragments[0] + signal_fragments[1][::-1])

    if __name__ == '__main__':
        plt.plot(data_x, core, label='core')
        plt.plot(data_x, anti_core, label='anti-core')

    not_nan_core: np.ndarray = np.abs(core[~np.isnan(core)])
    not_nan_anti_core: np.ndarray = np.abs(anti_core[~np.isnan(anti_core)])
    match: np.ndarray = np.array((not_nan_core > 3. * np.std(not_nan_core))
                                 # & (not_nan_anti_core > 3. * np.std(not_nan_anti_core))
                                 & (not_nan_anti_core < not_nan_core))
    match = np.concatenate((np.full(int(np.floor((data_x.shape[0] - match.shape[0]) / 2)), False),
                            match,
                            np.full(int(np.ceil((data_x.shape[0] - match.shape[0]) / 2)), False)))
    # for f in range(data_x.shape[0]):
    #     if data_x[f] - data_x[0] > 1.5 * LINE_WIDTH and data_x[-1] - data_x[f] > 1.5 * LINE_WIDTH:
    #         match[f] |= \
    #             (core[f] > 3 * np.std(fragment(core, data_x, data_x[f], 1.5 * LINE_WIDTH))
    #              and anti_core[f] > 3 * np.std(fragment(anti_core, data_x, data_x[f], 1.5 * LINE_WIDTH)))
    match = remove_spikes(match)
    match = ndimage.binary_dilation(match, iterations=4)
    match = remove_spikes(match)
    islands: np.ndarray = np.argwhere(np.diff(match)).reshape(-1, 2)
    peaks: np.ndarray = np.array([i[0] + np.argmax(data_y[i[0]:i[1]]) for i in islands])
    return peaks


if __name__ == '__main__':
    def main():
        data = np.loadtxt('lines.csv')

        plt.plot(data[..., 0], data[..., 1], label='data')
        found_lines = positions(data[..., 0], data[..., 1])
        plt.plot(data[found_lines, 0], data[found_lines, 1], ls='', marker='o')
        plt.legend()
        plt.show()


    main()
