# main_2d.py
import numpy as np
import pandas as pd
import config
from system_builder_2d import build_2d_system
from simulation_2d import ChainSimulation2D
from analyze_2d import (plot_2d_wave, create_animation_2d, 
                       plot_3d_surface, analyze_wave_properties,
                       plot_vector_field)

def load_simulation_data(filename: str) -> pd.DataFrame:
    """Загружает данные симуляции с правильными типами."""
    print(f"Loading simulation data from {filename}...")
    
    # Определяем типы данных для каждой колонки
    dtype = {
        'time': np.float64,
        'block_x': np.int64,
        'block_y': np.int64,
        'position_x': np.float64,
        'position_y': np.float64,
        'velocity_x': np.float64,
        'velocity_y': np.float64,
        'acceleration_x': np.float64,
        'acceleration_y': np.float64
    }
    
    try:
        df = pd.read_csv(filename, dtype=dtype, low_memory=False)
        print(f"Successfully loaded {len(df)} rows")
        return df
    except FileNotFoundError:
        print(f"Error: File {filename} not found.")
        raise
    except Exception as e:
        print(f"Error loading data with specified dtypes: {e}")
        # Попробуем загрузить без указания типов
        df = pd.read_csv(filename, low_memory=False)
        # Преобразуем типы вручную
        for col in df.columns:
            if col in ['block_x', 'block_y']:
                df[col] = pd.to_numeric(df[col], errors='coerce').astype(np.int64)
            elif col != 'time':
                df[col] = pd.to_numeric(df[col], errors='coerce').astype(np.float64)
        return df

def main():
    # Строим систему
    print("Building 2D system...")
    masses, spring_constants, spacings_x, spacings_y = build_2d_system()
    
    # Запускаем симуляцию
    print("Starting simulation...")
    simulation = ChainSimulation2D(
        masses=masses,
        spring_constants=spring_constants,
        spacings_x=spacings_x,
        spacings_y=spacings_y
    )
    simulation.run()
    
    # Анализ и визуализация
    try:
        # Загружаем данные с правильными типами
        df = load_simulation_data(config.CSV_FILENAME)
        
        # Проверяем данные
        print("\nData overview:")
        print(f"Columns: {df.columns.tolist()}")
        print(f"Shape: {df.shape}")
        print(f"Time range: {df['time'].min():.2f} - {df['time'].max():.2f}")
        print(f"Unique blocks: {df[['block_x', 'block_y']].drop_duplicates().shape[0]}")
        
        # Проверяем типы данных
        print("\nData types:")
        print(df.dtypes)
        
        # Проверяем наличие NaN значений
        print(f"\nNaN values per column:")
        nan_found = False
        for col in df.columns:
            nan_count = df[col].isna().sum()
            if nan_count > 0:
                print(f"  {col}: {nan_count} NaN values")
                nan_found = True
        
        # Удаляем строки с NaN значениями
        original_len = len(df)
        df = df.dropna()
        if len(df) < original_len:
            print(f"Removed {original_len - len(df)} rows with NaN values")
        
        if len(df) == 0:
            print("No valid data remaining after cleaning")
            return
        
        print("Creating visualizations...")
        
        # 1. Статические снимки
        print("Creating 2D wave plots...")
        plot_2d_wave(df)
        
        # 2. Анализ свойств волны
        print("Analyzing wave properties...")
        analyze_wave_properties(df)
        
        # 3. Векторное поле для одного момента времени
        times = df['time'].unique()
        if len(times) > 0:
            mid_time = times[len(times) // 2]
            print(f"Creating vector field for time {mid_time:.2f}s...")
            plot_vector_field(df, mid_time)
        
        # 4. 3D визуализация для нескольких моментов времени
        print("Creating 3D surface plots...")
        if len(times) >= 3:
            sample_times = times[::len(times)//3][:3]  # 3 снимка
            for time in sample_times:
                plot_3d_surface(df, time)
        else:
            print("Not enough time points for 3D visualization")
        
        # 5. Анимация (опционально - может быть медленной)
        user_input = input("Create animation? This may be slow. (y/n): ")
        if user_input.lower() == 'y':
            print("Creating animation...")
            create_animation_2d(df)
        else:
            print("Skipping animation")
        
        print("\nAnalysis completed successfully!")
        
    except Exception as e:
        print(f"Error during analysis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()