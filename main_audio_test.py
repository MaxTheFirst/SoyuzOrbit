import config
import sys
from math import sqrt

# Импортируем 1D-модель
from D1.system_builder import build_system
from D1.simulation import ChainSimulation

# Импортируем аудио-инструменты
from D1.audio_tools import generate_input_chirp, load_wav_file, save_output_audio
from D1.analyze_audio import analyze_audio_files

# --- Настройки аудио-эксперимента ---
USE_CUSTOM_WAV = True
CUSTOM_WAV_FILE = "D1/input_chirp.wav"  # <-- Укажите здесь ваш файл

RECORD_AFTER_ARRIVAL = 10.0

# --- Настройки "Свипа" (если USE_CUSTOM_WAV = False) ---
AUDIO_DURATION_CHIRP = 10.0
AUDIO_SAMPLE_RATE_CHIRP = 4410
CHIRP_START_HZ = 1.0
CHIRP_END_HZ = 300.0

if __name__ == "__main__":

    # --- 1. Генерация или Загрузка Входного Файла ---
    input_filename = "input_chirp.wav"

    if USE_CUSTOM_WAV:
        input_filename = CUSTOM_WAV_FILE
        time_arr, signal_arr, audio_sample_rate = load_wav_file(input_filename)
        if audio_sample_rate is None:
            sys.exit(1)
    else:
        # Используем "Свип"
        audio_sample_rate = AUDIO_SAMPLE_RATE_CHIRP
        time_arr, signal_arr, rate = generate_input_chirp(
            AUDIO_DURATION_CHIRP, CHIRP_START_HZ, CHIRP_END_HZ, audio_sample_rate
        )

    print(f"Audio Sample Rate: {audio_sample_rate} Гц")

    masses, spring_constants, spacings = build_system()
    simulation = ChainSimulation(
        masses=masses,
        spring_constants=spring_constants,
        spacings=spacings
    )

    # --- 3. Запуск Аудио-Симуляции ---
    output_signal = simulation.run_audio_simulation(
        time_arr, signal_arr, audio_sample_rate
    )

    # --- 4. Сохранение Выходного Файла ---
    save_output_audio(output_signal, audio_sample_rate)

    # --- 5. Поэтапный Анализ ---
    analyze_audio_files(input_filename, "output_sound.wav")