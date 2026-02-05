import matplotlib.pyplot as plt
import numpy as np

from simulation.particles import ParticleStatus


class Visualizer:
    def __init__(self, grid, particle_system):
        self.grid = grid
        self.ps = particle_system
        # Делаем короткую ссылку на конфиг сетки для удобства
        self.g_cfg = grid.cfg

    def plot_field_and_trajectories(self):
        # 1. АВТОМАТИЧЕСКИЙ РАСЧЕТ РАЗМЕРА ОКНА
        # Мы хотим, чтобы высота картинки была, скажем, 8 дюймов,
        # а ширина подстраивалась под пропорции симуляции.

        real_width = self.g_cfg.width_mm
        real_height = self.g_cfg.height_mm
        aspect_ratio = real_width / real_height

        base_height = 8.0
        calculated_width = base_height * aspect_ratio

        # Создаем фигуру с правильными пропорциями
        fig, ax = plt.subplots(figsize=(calculated_width, base_height))

        # 2. НАСТРОЙКА ОБЛАСТИ (EXTENT)
        # Это говорит matplotlib, какие реальные координаты у углов картинки
        extent = 0, real_width, 0, real_height

        # 3. ТЕПЛОВАЯ КАРТА ПОТЕНЦИАЛА
        im = ax.imshow(
            self.grid.potential,
            origin='lower',
            extent=extent,
            cmap='magma',
            alpha=0.9,
            interpolation='bilinear'  # Сглаживание пикселей
        )
        # Цветовая шкала
        cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label('Потенциал (В)')

        # 4. ОТРИСОВКА ЭЛЕКТРОДОВ (МАСКИ)
        # Накладываем маску там, где есть электроды
        structure_mask = np.where(self.grid.fixed_mask, 1, np.nan)
        # ax.imshow(
        #     structure_mask,
        #     origin='lower',
        #     extent=extent,
        #     cmap='gray',
        #     vmin=0, vmax=1,
        #     alpha=0.6,
        #     interpolation='nearest'  # Для твердых тел лучше без сглаживания
        # )

        # 5. ЛИНИИ ПОЛЯ (STREAMPLOT)
        # Генерируем сетку координат строго по конфигу
        x = np.linspace(0, real_width, self.g_cfg.nx)
        y = np.linspace(0, real_height, self.g_cfg.ny)
        X, Y = np.meshgrid(x, y)

        # Рисуем линии. Density можно вынести в конфиг UI, но пока оставим адаптивным
        # Если сетка очень плотная, streamplot может тормозить, density=1.5 - хороший баланс
        try:
            ax.streamplot(
                X, Y,
                self.grid.ex, self.grid.ey,
                color='cyan',
                linewidth=0.8,
                density=2,
                arrowstyle='->',
                arrowsize=1.2
            )
        except Exception as e:
            print(f"Ошибка при отрисовке линий поля: {e}")

        # 6. ТРАЕКТОРИИ ЧАСТИЦ
        for p in self.ps.particles:
            traj = np.array(p.trajectory)
            if len(traj) > 1:
                # Рисуем хвост
                ax.plot(traj[:, 0], traj[:, 1], 'w-', linewidth=1.2, alpha=0.8)
                # Рисуем голову (текущее положение)
                if p.status == ParticleStatus.IN_FLIGHT:
                    # Еще летит - белая точка
                    ax.plot(traj[-1, 0], traj[-1, 1], 'wo', markersize=3)
                elif p.status == ParticleStatus.HIT_ANODE:
                    # Попала в цель - зеленая точка
                    ax.plot(traj[-1, 0], traj[-1, 1], 'go', markersize=5, markeredgecolor='black')
                else:
                    # Врезалась в стену/катод/вылетела - красный крестик
                    ax.plot(traj[-1, 0], traj[-1, 1], 'rx', markersize=5)

        # 7. ФИНАЛЬНЫЕ НАСТРОЙКИ ОСЕЙ
        ax.set_title(f"Симуляция: {real_width}x{real_height} мм")
        ax.set_xlabel("X (мм)")
        ax.set_ylabel("Y (мм)")

        # ЖЕСТКИЕ ГРАНИЦЫ
        ax.set_xlim(0, real_width)
        ax.set_ylim(0, real_height)

        # ВАЖНО: Aspect ratio = equal.
        # Это гарантирует, что 1 мм на экране всегда квадратный.
        ax.set_aspect('equal')

        plt.tight_layout()
        plt.show()