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
mpl.rcParams["figure.dpi"] = 150
mpl.rcParams["figure.figsize"] = [8, 4]

def process_Klippel_curve(klippel_curve_string):
    if klippel_curve_string[:34] != "SourceDesc='dB-Lab_Clipboard_data'":
        raise TypeError("Data in clipboard not valid")
    array_string = klippel_curve_string.split("[")[1].split("]")[0]
    array_list = array_string.splitlines()
    arr = np.loadtxt(array_list, delimiter="\t", skiprows=1)
    return arr

with open("test_klippel_mic_signal.txt", "r") as file:
    contents = file.read()

# contents = pyperclip.paste()

xy = process_Klippel_curve(contents)
x = xy[:, 0] / 1000
y = xy[:, 1]

wavelet = "cmor1.5-1.0"
sampling_period = np.median(np.diff(x)) # seconds
FS = int(round(1 / sampling_period))

frequencies = signal_tools.generate_log_spaced_freq_list(20, 10000, 12)
scales = pywt.frequency2scale(wavelet, frequencies / FS)  # normalized to sampling freq. 1 is nyquist.

cwtmatr, freqs = pywt.cwt(y, scales, wavelet, sampling_period=sampling_period)
# absolute take absolute value of complex result
cwtmatr = np.abs(cwtmatr[:-1, :-1])

# plot result using matplotlib's pcolormesh (image with annoted axes)
fig, ax = plt.subplots()
pcm = ax.pcolormesh(x, freqs, cwtmatr, edgecolors=None)
# plt.minorticks_on()
plt.grid(which="minor", axis="both", color="b", alpha=0.3)
ax.set_yscale("log")
ax.set_xlabel("Time (s)")
ax.set_ylabel("Frequency (Hz)")
ax.set_title("Continuous Wavelet Transform (Scaleogram)")
fig.colorbar(pcm, ax=ax)
