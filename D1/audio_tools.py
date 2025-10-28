import sys

import numpy as np
from scipy.io import wavfile
from scipy.signal import chirp


def generate_input_chirp(duration_sec: float, start_freq: float, end_freq: float,
                         sample_rate: int) -> tuple[np.ndarray, np.ndarray, int]:
    """
    Генерирует "свип-сигнал" (chirp) и сохраняет его в .wav.
    Возвращает (временные метки, сам сигнал, sample_rate)
    """
    print(f"Generating input chirp: {start_freq} Hz to {end_freq} Hz over {duration_sec}s")

    # 1. Создаем временные метки
    t = np.linspace(0, duration_sec, int(duration_sec * sample_rate), endpoint=False)

    # 2. Создаем "свип"
    signal = chirp(t, f0=start_freq, f1=end_freq, t1=duration_sec, method='linear')

    # 3. Нормализуем и сохраняем
    signal_norm = (signal * (2 ** 15 - 1) / np.max(np.abs(signal))).astype(np.int16)
    wavfile.write("input_chirp.wav", sample_rate, signal_norm)

    print("Saved input_chirp.wav")

    # Возвращаем ненормированный сигнал для симуляции
    return t, signal, sample_rate


def save_output_audio(signal_data: np.ndarray, sample_rate: int):
    """
    Сохраняет выходной сигнал симуляции в .wav.
    """
    print("Saving output_sound.wav...")

    # 1. Нормализуем
    # (Делаем его тише, т.к. он может "взрываться" на резонансах)
    max_val = np.max(np.abs(signal_data))
    if max_val == 0:
        print("Warning: Output signal is silent.")
        max_val = 1.0

    signal_norm = (signal_data / max_val * (2 ** 15 - 1) * 0.5).astype(np.int16)

    # 2. Сохраняем
    wavfile.write("output_sound.wav", sample_rate, signal_norm)
    print("Saved output_sound.wav")


def load_wav_file(filename: str) -> tuple:
    """
    Загружает .wav файл.

    Возвращает:
    - time_arr (np.ndarray): Массив временных отметок (в секундах)
    - signal_arr (np.ndarray): Нормализованный сигнал (float от -1.0 до 1.0)
    - rate (int): Частота дискретизации (например, 44100)
    """
    print(f"Loading WAV file: {filename}...")
    try:
        rate, data = wavfile.read(filename)
    except FileNotFoundError:
        print(f"Ошибка: Файл '{filename}' не найден.", file=sys.stderr)
        return None, None, None
    except ValueError:
        print(f"Ошибка: Не удалось прочитать '{filename}'. Убедитесь, что это .wav файл.", file=sys.stderr)
        return None, None, None

    # 1. Конвертируем в моно (если стерео)
    if data.ndim == 2:
        print("  Info: Стерео-файл обнаружен, конвертируем в моно (усреднение).")
        signal_int = data.mean(axis=1).astype(data.dtype)
    else:
        signal_int = data

    # 2. Нормализуем в float (от -1.0 до 1.0)
    # Это 'signal_arr', который нужен симуляции
    max_val = np.iinfo(signal_int.dtype).max
    if max_val == 0:
        print(f"Ошибка: Неизвестный тип данных {signal_int.dtype}", file=sys.stderr)
        return None, None, None

    signal_arr = signal_int.astype(np.float64) / max_val

    # 3. Создаем массив времени
    num_samples = len(signal_arr)
    duration_sec = num_samples / rate
    time_arr = np.linspace(0, duration_sec, num=num_samples, endpoint=False)

    print(f"  Success: Rate: {rate} Гц, Длительность: {duration_sec:.2f}с, {num_samples} сэмплов.")

    return time_arr, signal_arr, rate