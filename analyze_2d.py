# analyze_2d.py
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.animation import FuncAnimation
import config

def plot_2d_wave(df: pd.DataFrame):
    """Создает несколько снимков волны в 2D."""
    times = df['time'].unique()
    
    # Берем только 6 моментов времени для визуализации
    num_plots = min(6, len(times))
    if num_plots == 0:
        print("No time points available for plotting")
        return
        
    sample_times = np.linspace(times.min(), times.max(), num_plots)
    
    # Создаем сетку subplots
    if num_plots <= 3:
        fig, axes = plt.subplots(1, num_plots, figsize=(5*num_plots, 4))
        if num_plots == 1:
            axes = [axes]
    else:
        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        axes = axes.flatten()
    
    for idx, time in enumerate(sample_times):
        if idx >= len(axes):
            break
            
        # Находим ближайший временной шаг
        closest_time = times[np.argmin(np.abs(times - time))]
        time_data = df[np.isclose(df['time'], closest_time)]
        
        # Создаем матрицу смещений
        displacement_magnitude = np.zeros((config.NUM_BLOCKS_X, config.NUM_BLOCKS_Y))
        
        for _, row in time_data.iterrows():
            i = int(row['block_x'])
            j = int(row['block_y'])
            
            # Вычисляем равновесную позицию
            eq_x = i * config.DEFAULT_BLOCK_SPACING_X
            eq_y = j * config.DEFAULT_BLOCK_SPACING_Y
            
            # Вычисляем смещение (убеждаемся, что это числа)
            disp_x = float(row['position_x']) - eq_x
            disp_y = float(row['position_y']) - eq_y
            displacement_magnitude[i, j] = np.sqrt(disp_x**2 + disp_y**2)
        
        # Визуализация
        im = axes[idx].imshow(displacement_magnitude.T, cmap='hot', origin='lower', 
                             aspect='auto', interpolation='bilinear')
        axes[idx].set_title(f'Time: {closest_time:.2f}s')
        axes[idx].set_xlabel('X Index')
        axes[idx].set_ylabel('Y Index')
        plt.colorbar(im, ax=axes[idx])
    
    plt.tight_layout()
    plt.show()

def create_animation_2d(df: pd.DataFrame):
    """Создает анимацию распространения волны."""
    times = df['time'].unique()
    
    # Ограничиваем количество кадров для производительности
    max_frames = min(30, len(times))
    if max_frames == 0:
        print("No data for animation")
        return None
        
    frame_indices = np.linspace(0, len(times)-1, max_frames, dtype=int)
    times_subset = times[frame_indices]
    
    # Подготовка данных для анимации
    frames_data = []
    for time in times_subset:
        time_data = df[np.isclose(df['time'], time)]
        
        # Создаем матрицу величин смещений
        magnitude_data = np.zeros((config.NUM_BLOCKS_X, config.NUM_BLOCKS_Y))
        
        for _, row in time_data.iterrows():
            i = int(row['block_x'])
            j = int(row['block_y'])
            
            # Равновесная позиция
            eq_x = i * config.DEFAULT_BLOCK_SPACING_X
            eq_y = j * config.DEFAULT_BLOCK_SPACING_Y
            
            # Смещение
            disp_x = float(row['position_x']) - eq_x
            disp_y = float(row['position_y']) - eq_y
            magnitude_data[i, j] = np.sqrt(disp_x**2 + disp_y**2)
        
        frames_data.append(magnitude_data)
    
    # Создаем анимацию
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Находим максимальное значение для фиксированной цветовой шкалы
    vmax = max(np.max(frame) for frame in frames_data)
    
    def update(frame):
        ax.clear()
        im = ax.imshow(frames_data[frame].T, cmap='hot', origin='lower', 
                      aspect='auto', interpolation='bilinear',
                      vmin=0, vmax=vmax)
        
        ax.set_title(f'2D Wave Propagation - Time: {times_subset[frame]:.2f}s')
        ax.set_xlabel('X Block Index')
        ax.set_ylabel('Y Block Index')
        
        # Добавляем colorbar только один раз
        if frame == 0:
            plt.colorbar(im, ax=ax, label='Displacement Magnitude')
        
        return [im]
    
    anim = FuncAnimation(fig, update, frames=len(frames_data), 
                        interval=200, blit=False, repeat=True)
    
    plt.tight_layout()
    plt.show()
    
    return anim

def plot_3d_surface(df: pd.DataFrame, time: float):
    """Создает 3D поверхность смещений."""
    try:
        from mpl_toolkits.mplot3d import Axes3D
    except ImportError:
        print("3D plotting requires mpl_toolkits. Install with: pip install matplotlib")
        return
    
    time_data = df[np.isclose(df['time'], time, atol=0.01)]
    
    if time_data.empty:
        print(f"No data found for time {time}")
        return
    
    # Создаем сетку для 3D
    X, Y = np.meshgrid(range(config.NUM_BLOCKS_X), range(config.NUM_BLOCKS_Y), indexing='ij')
    Z = np.zeros((config.NUM_BLOCKS_X, config.NUM_BLOCKS_Y))
    
    for _, row in time_data.iterrows():
        i = int(row['block_x'])
        j = int(row['block_y'])
        
        # Равновесная позиция
        eq_x = i * config.DEFAULT_BLOCK_SPACING_X
        eq_y = j * config.DEFAULT_BLOCK_SPACING_Y
        
        # Смещение
        disp_x = float(row['position_x']) - eq_x
        disp_y = float(row['position_y']) - eq_y
        Z[i, j] = np.sqrt(disp_x**2 + disp_y**2)
    
    # 3D график
    fig = plt.figure(figsize=(12, 8))
    ax = fig.add_subplot(111, projection='3d')
    
    surf = ax.plot_surface(X, Y, Z, cmap='viridis', edgecolor='none', alpha=0.8)
    ax.set_title(f'3D Surface Plot - Time: {time:.2f}s')
    ax.set_xlabel('X Block Index')
    ax.set_ylabel('Y Block Index')
    ax.set_zlabel('Displacement Magnitude')
    
    plt.colorbar(surf, ax=ax, shrink=0.5, aspect=5)
    plt.show()

def analyze_wave_properties(df: pd.DataFrame):
    """Анализирует свойства волны."""
    print("Analyzing wave properties...")
    
    # Находим центральный блок
    center_x = config.NUM_BLOCKS_X // 2
    center_y = config.NUM_BLOCKS_Y // 2
    
    center_data = df[(df['block_x'] == center_x) & (df['block_y'] == center_y)]
    
    if center_data.empty:
        print("No data for central block")
        return
    
    # Убеждаемся, что данные числовые
    center_data = center_data.copy()
    for col in ['position_x', 'position_y']:
        center_data[col] = pd.to_numeric(center_data[col], errors='coerce')
    
    # Удаляем NaN значения
    center_data = center_data.dropna()
    
    if len(center_data) == 0:
        print("No valid data for central block after cleaning")
        return
    
    # График смещения центрального блока
    plt.figure(figsize=(15, 5))
    
    # X смещение
    plt.subplot(1, 3, 1)
    disp_x = center_data['position_x'] - center_x * config.DEFAULT_BLOCK_SPACING_X
    plt.plot(center_data['time'], disp_x)
    plt.title('X Displacement of Central Block')
    plt.xlabel('Time (s)')
    plt.ylabel('Displacement X (m)')
    plt.grid(True)
    
    # Y смещение
    plt.subplot(1, 3, 2)
    disp_y = center_data['position_y'] - center_y * config.DEFAULT_BLOCK_SPACING_Y
    plt.plot(center_data['time'], disp_y)
    plt.title('Y Displacement of Central Block')
    plt.xlabel('Time (s)')
    plt.ylabel('Displacement Y (m)')
    plt.grid(True)
    
    # Величина смещения
    plt.subplot(1, 3, 3)
    disp_magnitude = np.sqrt(disp_x**2 + disp_y**2)
    plt.plot(center_data['time'], disp_magnitude)
    plt.title('Displacement Magnitude of Central Block')
    plt.xlabel('Time (s)')
    plt.ylabel('Displacement Magnitude (m)')
    plt.grid(True)
    
    plt.tight_layout()
    plt.show()
    
    # Анализ скорости затухания
    max_displacement = disp_magnitude.max()
    final_displacement = disp_magnitude.iloc[-1] if len(disp_magnitude) > 0 else 0
    
    print(f"Maximum displacement: {max_displacement:.4f} m")
    print(f"Final displacement: {final_displacement:.4f} m")
    if max_displacement > 0:
        print(f"Damping ratio: {final_displacement / max_displacement:.4f}")

def plot_vector_field(df: pd.DataFrame, time: float):
    """Создает векторное поле смещений."""
    time_data = df[np.isclose(df['time'], time, atol=0.01)]
    
    if time_data.empty:
        print(f"No data found for time {time}")
        return
    
    # Создаем матрицы смещений
    disp_x = np.zeros((config.NUM_BLOCKS_X, config.NUM_BLOCKS_Y))
    disp_y = np.zeros((config.NUM_BLOCKS_X, config.NUM_BLOCKS_Y))
    
    for _, row in time_data.iterrows():
        i = int(row['block_x'])
        j = int(row['block_y'])
        
        # Равновесная позиция
        eq_x = i * config.DEFAULT_BLOCK_SPACING_X
        eq_y = j * config.DEFAULT_BLOCK_SPACING_Y
        
        # Смещение
        disp_x[i, j] = float(row['position_x']) - eq_x
        disp_y[i, j] = float(row['position_y']) - eq_y
    
    # Векторное поле
    X, Y = np.meshgrid(range(config.NUM_BLOCKS_X), range(config.NUM_BLOCKS_Y), indexing='ij')
    
    plt.figure(figsize=(10, 8))
    plt.quiver(X, Y, disp_x, disp_y, scale=1.0, scale_units='inches')
    plt.title(f'Displacement Vector Field - Time: {time:.2f}s')
    plt.xlabel('X Block Index')
    plt.ylabel('Y Block Index')
    plt.grid(True)
    plt.show()