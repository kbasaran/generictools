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


# ---- get curve
with open("test_klippel_mic_signal.txt", "r") as file:
    curve_copied_from_Klippel = file.read()

# curve_copied_from_Klippel = pyperclip.paste()

# ---- parse
xy = parse_curve_copied_from_Klippel(curve_copied_from_Klippel)
x = xy[:, 0] / 1000  # change ms to seconds
y = xy[:, 1]

BW = 1/12
C = 1
B = 4 / (C * BW)**2

# wavelets = [f"cmor{b:.1f}-{c:.1f}"
#             for b in [2, 4, 8, 16]
#             for c in [0.5, 1, 1.5, 2]
#             ]

# ---- wavelet calculation
wavelet = f"cmor{B:.1f}-{C:.1f}"
sampling_period = np.median(np.diff(x))  # seconds
FS = int(round(1 / sampling_period))

frequencies = signal_tools.generate_log_spaced_freq_list(10, FS/3, 1/BW)
# normalized to sampling freq. 1 is nyquist.
scales = pywt.frequency2scale(wavelet, frequencies / FS)

start_time = time.perf_counter()
cwtmatr, freqs = pywt.cwt(
    y, scales, wavelet, sampling_period=sampling_period)
# absolute take absolute value of complex result
cwtmatr = np.abs(cwtmatr[:-1, :-1])
print(f"{wavelet} calculated in"
      f" { (time.perf_counter() - start_time) / 60:.2g} minutes."
      )

# ---- plot result using matplotlib's pcolormesh (image with annoted axes)
fig, ax = plt.subplots()
pcm = ax.pcolormesh(x,
                    freqs,
                    cwtmatr,
                    vmin=np.max(cwtmatr) / 1e3,
                    vmax=np.max(cwtmatr),
                    edgecolors=None)
plt.minorticks_on()
plt.grid(which="minor", axis="both", color="k", alpha=0.1)
ax.set_yscale("log")
ax.set_xlabel("Time (s)")
ax.set_ylabel("Frequency (Hz)")
ax.set_title(f"Continuous Wavelet Transform (Scaleogram)\n{wavelet}, {1/BW:.2g} ppo")
fig.colorbar(pcm, ax=ax)
plt.show()
