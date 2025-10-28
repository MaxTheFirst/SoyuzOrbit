# D1/analyze_audio.py
import numpy as np
import matplotlib.pyplot as plt
from scipy.io import wavfile
from scipy.signal import spectrogram

def analyze_audio_files(file_in: str, file_out: str):
    """
    Строит волновые формы и спектрограммы для входного и выходного аудио.
    """
    print("Analyzing audio files...")

    # 1. Читаем файлы
    rate_in, data_in = wavfile.read(file_in)
    rate_out, data_out = wavfile.read(file_out)

    # 2. Создаем временные оси
    time_in = np.linspace(0, len(data_in) / rate_in, num=len(data_in))
    time_out = np.linspace(0, len(data_out) / rate_out, num=len(data_out))

    # --- График 1: Волновые формы ---
    plt.figure(figsize=(15, 6))
    plt.subplot(2, 1, 1)
    # --- ИСПРАВЛЕНИЕ ЛЕГЕНДЫ ---
    plt.plot(time_in, data_in, label=f"Вход ({file_in})")
    # ---
    plt.title("Волновая форма (Амплитуда от Времени)")
    plt.legend()
    plt.grid(True)

    plt.subplot(2, 1, 2)
    # --- ИСПРАВЛЕНИЕ ЛЕГЕНДЫ ---
    plt.plot(time_out, data_out, label=f"Выход ({file_out})", color='orange')
    # ---
    plt.xlabel("Время (с)")
    plt.legend()
    plt.grid(True)
    plt.show()

    # --- График 2: Спектрограммы (FFT-анализ) ---
    f_in, t_in, Sxx_in = spectrogram(data_in, rate_in, nperseg=1024)
    f_out, t_out, Sxx_out = spectrogram(data_out, rate_out, nperseg=1024)

    plt.figure(figsize=(15, 8))

    plt.subplot(2, 1, 1)
    plt.pcolormesh(t_in, f_in, 10 * np.log10(Sxx_in + 1e-9), shading='gouraud', cmap='viridis')
    plt.ylabel('Частота (Гц)')
    # --- ИСПРАВЛЕНИЕ ЛЕГЕНДЫ ---
    plt.title(f'Спектрограмма ВХОДНОГО сигнала ({file_in})')
    # ---
    plt.ylim(0, 500)

    plt.subplot(2, 1, 2)
    plt.pcolormesh(t_out, f_out, 10 * np.log10(Sxx_out + 1e-9), shading='gouraud', cmap='viridis')
    plt.xlabel('Время (с)')
    plt.ylabel('Частота (Гц)')
    # --- ИСПРАВЛЕНИЕ ЛЕГЕНДЫ ---
    plt.title(f'Спектрограмма ВЫХОДНОГО сигнала ({file_out})')
    # ---
    plt.ylim(0, 500)

    plt.tight_layout()
    plt.show()