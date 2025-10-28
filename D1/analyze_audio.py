import numpy as np
import matplotlib.pyplot as plt
from scipy.io import wavfile
from scipy.signal import spectrogram, freqz, tf2zpk
import warnings
warnings.filterwarnings('ignore')

def analyze_audio_files(file_in: str, file_out: str):
    """
    Строит волновые формы, спектрограммы и АЧХ для входного и выходного аудио.
    """
    print("Analyzing audio files...")

    # 1. Читаем файлы
    rate_in, data_in = wavfile.read(file_in)
    rate_out, data_out = wavfile.read(file_out)

    # 2. Преобразуем в моно если stereo
    if len(data_in.shape) > 1:
        data_in = data_in.mean(axis=1)
    
    if len(data_out.shape) > 1:
        data_out = data_out.mean(axis=1)

    # 3. Создаем временные оси
    time_in = np.linspace(0, len(data_in) / rate_in, num=len(data_in))
    time_out = np.linspace(0, len(data_out) / rate_out, num=len(data_out))

    # --- График 1: Волновые формы ---
    plt.figure(figsize=(15, 6))
    plt.subplot(2, 1, 1)
    plt.plot(time_in, data_in, label=f"Вход ({file_in})")
    plt.title("Волновая форма (Амплитуда от Времени)")
    plt.legend()
    plt.grid(True)

    plt.subplot(2, 1, 2)
    plt.plot(time_out, data_out, label=f"Выход ({file_out})", color='orange')
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
    plt.title(f'Спектрограмма ВХОДНОГО сигнала ({file_in})')
    plt.ylim(0, 500)

    plt.subplot(2, 1, 2)
    plt.pcolormesh(t_out, f_out, 10 * np.log10(Sxx_out + 1e-9), shading='gouraud', cmap='viridis')
    plt.xlabel('Время (с)')
    plt.ylabel('Частота (Гц)')
    plt.title(f'Спектрограмма ВЫХОДНОГО сигнала ({file_out})')
    plt.ylim(0, 500)

    plt.tight_layout()
    plt.show()

    # --- График 3: АЧХ системы ---
    plt.figure(figsize=(15, 10))
    
    # Вычисляем АЧХ через FFT
    n_fft = min(len(data_in), len(data_out), 8192)
    
    # Вычисляем FFT для входного и выходного сигналов
    fft_in = np.fft.fft(data_in[:n_fft])
    fft_out = np.fft.fft(data_out[:n_fft])
    
    # Вычисляем АЧХ как отношение выходного FFT к входному
    # Добавляем маленькое значение для избежания деления на ноль
    epsilon = 1e-10
    h_freq = fft_out / (fft_in + epsilon)
    
    # Частотная ось
    freqs = np.fft.fftfreq(n_fft, 1/rate_in)
    
    # Берем только положительные частоты
    positive_freq_idx = freqs > 0
    freqs_positive = freqs[positive_freq_idx]
    h_freq_positive = h_freq[positive_freq_idx]
    
    # Амплитудная характеристика в dB
    amplitude_response_db = 20 * np.log10(np.abs(h_freq_positive) + 1e-12)
    
    # Фазовая характеристика
    phase_response = np.angle(h_freq_positive, deg=True)
    
    # График АЧХ
    plt.subplot(3, 1, 1)
    plt.semilogx(freqs_positive, amplitude_response_db)
    plt.title('Амплитудно-Частотная Характеристика (АЧХ) системы')
    plt.ylabel('Усиление, dB')
    plt.grid(True, which='both', linestyle='--', alpha=0.7)
    plt.xlim(20, rate_in/2)
    
    # График ФЧХ
    plt.subplot(3, 1, 2)
    plt.semilogx(freqs_positive, phase_response)
    plt.title('Фазо-Частотная Характеристика (ФЧХ) системы')
    plt.ylabel('Фаза, градусы')
    plt.grid(True, which='both', linestyle='--', alpha=0.7)
    plt.xlim(20, rate_in/2)
    
    # График импульсной характеристики (обратное FFT от H(f))
    impulse_response = np.fft.ifft(h_freq)
    time_ir = np.arange(len(impulse_response)) / rate_in
    
    plt.subplot(3, 1, 3)
    plt.plot(time_ir * 1000, np.real(impulse_response))
    plt.title('Импульсная характеристика системы')
    plt.xlabel('Время, мс')
    plt.ylabel('Амплитуда')
    plt.grid(True)
    plt.xlim(0, min(100, time_ir[-1] * 1000))  # Показываем первые 100 мс
    
    plt.tight_layout()
    plt.show()

    # Дополнительная информация о файлах и системе
    print(f"\nИнформация о файлах:")
    print(f"Входной: {len(data_in)/rate_in:.2f} сек, {rate_in} Гц, {len(data_in)} сэмплов")
    print(f"Выходной: {len(data_out)/rate_out:.2f} сек, {rate_out} Гц, {len(data_out)} сэмплов")
    
    # Анализ АЧХ
    max_gain_freq = freqs_positive[np.argmax(np.abs(h_freq_positive))]
    max_gain_db = np.max(amplitude_response_db)
    min_gain_freq = freqs_positive[np.argmin(amplitude_response_db)]
    min_gain_db = np.min(amplitude_response_db)
    
    print(f"\nАнализ АЧХ системы:")
    print(f"Максимальное усиление: {max_gain_db:.2f} dB на частоте {max_gain_freq:.1f} Гц")
    print(f"Максимальное ослабление: {min_gain_db:.2f} dB на частоте {min_gain_freq:.1f} Гц")
    print(f"Полоса анализа: 20 - {rate_in/2} Гц")

# Альтернативная функция для оценки АЧХ с использованием Welch метода (более устойчивая)
def estimate_frequency_response(file_in: str, file_out: str, nperseg=1024):
    """
    Альтернативный метод оценки АЧХ с использованием Welch метода
    """
    from scipy.signal import welch, csd
    
    rate_in, data_in = wavfile.read(file_in)
    rate_out, data_out = wavfile.read(file_out)
    
    # Преобразуем в моно
    if len(data_in.shape) > 1:
        data_in = data_in.mean(axis=1)
    if len(data_out.shape) > 1:
        data_out = data_out.mean(axis=1)
    
    # Выравниваем длины сигналов
    min_len = min(len(data_in), len(data_out))
    data_in = data_in[:min_len]
    data_out = data_out[:min_len]
    
    # Вычисляем спектральную плотность мощности
    freqs, Pxx = welch(data_in, rate_in, nperseg=nperseg)
    _, Pyy = welch(data_out, rate_out, nperseg=nperseg)
    _, Pxy = csd(data_in, data_out, rate_in, nperseg=nperseg)
    
    # Оценка передаточной функции
    H_est = Pxy / (Pxx + 1e-12)
    
    # АЧХ в dB
    H_mag_db = 20 * np.log10(np.abs(H_est) + 1e-12)
    
    plt.figure(figsize=(12, 8))
    plt.semilogx(freqs, H_mag_db)
    plt.title('АЧХ системы (Welch метод)')
    plt.xlabel('Частота, Гц')
    plt.ylabel('Усиление, dB')
    plt.grid(True, which='both', linestyle='--', alpha=0.7)
    plt.xlim(20, rate_in/2)
    plt.show()
    
    return freqs, H_est