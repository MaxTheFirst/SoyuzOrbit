# Мини-проекты по волновой оптике

В этой папке лежат отдельные учебные проекты. Каждый проект находится в своей папке и содержит:

- запускаемый Python-скрипт;
- подробный `readme.md`;
- объяснение для человека без подготовки по физике.

## Список

```text
01_telescope_resolution  - дифракционный предел телескопа
02_eye_model             - простая модель глаза
03_kepler_telescope      - двухлинзовый телескоп Кеплера
04_chromatic_aberration  - цветной фокус линзы из BK7
05_optimal_aperture      - компромисс между дифракцией и аберрациями
06_fourier_imaging       - потеря мелких деталей через частотную апертуру
07_fiber_coupling        - ввод света в одномодовое оптоволокно
```

## Общий запуск

Из корня репозитория:

```bash
./.venv/bin/python projects/01_telescope_resolution/telescope_resolution.py
./.venv/bin/python projects/02_eye_model/eye_model.py
./.venv/bin/python projects/03_kepler_telescope/kepler_telescope.py
./.venv/bin/python projects/04_chromatic_aberration/chromatic_aberration.py
./.venv/bin/python projects/05_optimal_aperture/optimal_aperture.py
./.venv/bin/python projects/06_fourier_imaging/fourier_imaging.py
./.venv/bin/python projects/07_fiber_coupling/fiber_coupling.py
```

Если зависимости запускаются через `uv`, команда такая:

```bash
uv run python projects/01_telescope_resolution/telescope_resolution.py
```

И дальше заменить путь на нужный проект.
