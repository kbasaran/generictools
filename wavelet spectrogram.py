# -*- coding: utf-8 -*-
"""
Created on Tue Feb 18 21:38:51 2025

@author: kerem.basaran
"""
# source
# https://pywavelets.readthedocs.io/en/latest/ref/cwt.html#continuous-wavelet-transform-cwt

import pyperclip
import numpy as np
import pywt
import matplotlib.pyplot as plt
import signal_tools
import matplotlib as mpl
import time
mpl.rcParams["figure.dpi"] = 150
mpl.rcParams["figure.figsize"] = [8, 4]


def parse_curve_copied_from_Klippel(klippel_curve_string):
    if klippel_curve_string[:34] != "SourceDesc='dB-Lab_Clipboard_data'":
        raise TypeError("Data in clipboard not valid")
    array_string = klippel_curve_string.split("[")[1].split("]")[0]
    array_list = array_string.splitlines()
    arr = np.loadtxt(array_list, delimiter="\t", skiprows=1)
    return arr


with open("test_klippel_mic_signal.txt", "r") as file:
    curve_copied_from_Klippel = file.read()

# curve_copied_from_Klippel = pyperclip.paste()

xy = parse_curve_copied_from_Klippel(curve_copied_from_Klippel)
x = xy[:, 0] / 1000
y = xy[:, 1]

BW = 1/24
B = 36
C = 0.5


# wavelets = [f"cmor{b:.1f}-{c:.1f}"
#             for b in [B/4, B/2, B, B*2, B*4]
#             for c in [C/16, C/8, C/4, C/2, C, C*2, C*4]
#             ]
results = dict()
# for wavelet in wavelets:

wavelet = f"cmor{B:.1f}-{C:.1f}"
sampling_period = np.median(np.diff(x))  # seconds
FS = int(round(1 / sampling_period))

frequencies = signal_tools.generate_log_spaced_freq_list(20, 10000, 1/BW)
# normalized to sampling freq. 1 is nyquist.
scales = pywt.frequency2scale(wavelet, frequencies / FS)

start_time = time.perf_counter()
cwtmatr, freqs = pywt.cwt(
    y, scales, wavelet, sampling_period=sampling_period)
# absolute take absolute value of complex result
cwtmatr = np.abs(cwtmatr[:-1, :-1])
print(f"{wavelet} calculated in"
      f"{(time.perf_counter() - start_time) / 60:.2g} minutes."
      )
results[wavelet] = cwtmatr

# plot result using matplotlib's pcolormesh (image with annoted axes)
fig, ax = plt.subplots()
pcm = ax.pcolormesh(x, freqs, cwtmatr, edgecolors=None)
plt.minorticks_on()
plt.grid(which="minor", axis="both", color="w", alpha=0.07)
ax.set_yscale("log")
ax.set_xlabel("Time (s)")
ax.set_ylabel("Frequency (Hz)")
ax.set_title(f"Continuous Wavelet Transform (Scaleogram)\n{wavelet}")
fig.colorbar(pcm, ax=ax)
plt.show()
