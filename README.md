# SoyuzOrbit

`SoyuzOrbit` в текущем виде не связан с орбитальной механикой. По факту это настольный симулятор электрических цепей и приближенных электромагнитных полей, написанный на Python, с редактором схем на `PyQt6`, собственным переходным решателем, библиотекой физических компонентов и форматом проекта на JSON.

Проект поддерживает два основных сценария:

1. Сборка схемы в GUI, сохранение/загрузка проекта в JSON и запуск расчета.
2. Описание схемы напрямую в Python через API `core` и запуск из CLI.

Дополнительно проект умеет:

- считать переходные процессы по напряжениям, токам, температурам и внутренним состояниям компонентов;
- моделировать физические провода как распределенные элементы с паразитиками;
- оценивать тепловую связь между соседними компонентами;
- добавлять приближенную электромагнитную связь между близкими параллельными проводниками;
- строить квазистатическую карту потенциала, электрического и магнитного поля;
- строить упрощенную FDTD-анимацию и 2D-анимации Maxwell в режимах `TMz` и `TEz`.

## 1. Что именно находится в репозитории

| Путь | Назначение |
| --- | --- |
| `main.py` | Точка входа GUI. Просто вызывает `gui.main_window.launch()`. |
| `run_sim.py` | CLI для запуска Python-примеров или JSON-проектов, печати итогов, построения графиков и экспорта карт/анимаций полей. |
| `requirements.txt` | Внешние зависимости проекта. |
| `core/component.py` | Базовые классы `Component` и `TwoTerminalComponent`. |
| `core/components.py` | Библиотека физических моделей компонентов и фабрика `create_component()`. |
| `core/engine.py` | Класс `Circuit`, численный решатель, тепловые и ЭМ-связи, временная интеграция. |
| `core/project.py` | Формат проекта, датаклассы JSON-схемы, преобразование проекта в `Circuit`. |
| `core/field_solver.py` | Квазистатический полевой решатель, FDTD и 2D Maxwell. |
| `core/physics.py` | Константы, свойства материалов, термические и полупроводниковые вспомогательные функции. |
| `gui/main_window.py` | Основное окно приложения, панель элементов, запуск расчета, сохранение/загрузка JSON. |
| `gui/canvas.py` | Холст схемы, графические элементы, провода, маршрутизация, сериализация GUI в `CircuitProject`. |
| `gui/components_visual.py` | Процедурная генерация иконок и пиксмапов компонентов через Pillow. |
| `gui/field_dialog.py` | Диалог предпросмотра карт поля и полевых анимаций. |
| `examples/*.py` | Примеры построения схемы напрямую в Python. |
| `examples/*.json` | Примеры проектов в JSON. |
| `examples/component_showcase/*.json` | Новый каталог простых демонстрационных схем почти по всем компонентам библиотеки. |
| `examples/component_showcase/README.md` | Объясняет, что показывает каждая схема, какие графики открывать и что по ним анализировать. |
| `examples/adders/*` | Учебные схемы сумматоров и скрипты для подачи двоичных входов через CLI. |

## 2. Стек Python и зависимости

### Внешние зависимости

`requirements.txt` содержит ровно пять библиотек:

- `numpy` — все массивы состояния, временные ряды, сетки полей, векторизованные расчеты;
- `scipy` — fallback-решение нелинейной системы через `scipy.optimize.root`, если собственная Ньютоновская итерация не сошлась;
- `pillow` — процедурная графика компонентов, экспорт PNG/GIF карт и анимаций поля;
- `matplotlib` — графики в CLI (`--plot-*`, `--save-plot`);
- `PyQt6` — GUI редактора схем.

### Что используется из стандартной библиотеки

Основные модули стандартной библиотеки:

- `dataclasses` — все структуры проекта (`ComponentRecord`, `WireRecord`, `ProjectSettings`, `SimulationResult` и т.д.);
- `math` — физические формулы, геометрия, экспоненты, тригонометрия;
- `json` — сериализация/десериализация проекта;
- `pathlib` — работа с файлами проекта и экспортом;
- `importlib.util` — загрузка Python-примеров по пути;
- `collections.defaultdict` — группировка истории по компонентам и построение связей.

### Важное организационное замечание

Проект не оформлен как пакет с `setup.py`/`pyproject.toml`. Это рабочий репозиторий, который запускается из корня.

В репозитории присутствует `.venv`, собранное локально, но код не зависит от конкретной среды: достаточно любого современного Python 3.x, совместимого с перечисленными библиотеками. В рабочем каталоге разработчика виртуальное окружение собрано на Python 3.13, но `requirements.txt` версию Python явно не фиксирует.

## 3. Быстрый запуск

### Установка зависимостей

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

### Запуск GUI

```bash
python main.py
```

GUI открывает редактор схем, где можно:

- поставить компонент на холст;
- соединить два вывода проводом;
- добавить маршрутные точки на провод;
- сохранить схему в JSON;
- загрузить JSON-проект;
- запустить переходный расчет;
- открыть окно с графиками результата симуляции;
- показать карту поля, FDTD, Maxwell TMz или Maxwell TEz.

### Запуск CLI по Python-примеру

```bash
python run_sim.py examples/test_dc_basic.py --plot-nodes --plot-currents --plot-voltages
```

### Запуск CLI по JSON-проекту

```bash
python run_sim.py examples/led_project.json --plot-all
```

### Запуск каталога простых демонстрационных схем

```bash
python run_sim.py examples/component_showcase/01_battery_resistor_measurement.json --plot-nodes --plot-currents --plot-iv-xy
python run_sim.py examples/component_showcase/05_rc_charge_discharge.json --plot-nodes --plot-energy-storage
python run_sim.py examples/component_showcase/15_mosfet_led_switch.json --plot-currents --plot-energy-storage --plot-state
```

Каталог `examples/component_showcase/` полезен как основной набор учебных и презентационных схем:

- там есть простые рабочие примеры почти для всех ключевых элементов;
- для каждой схемы в отдельном `README.md` перечислены рекомендуемые графики;
- примеры удобно открывать и в GUI, и через CLI.

### Сохранение всех графиков в файл

```bash
python run_sim.py examples/led_project.json --plot-all --save-plot led-project-plots.png
```

### Экспорт карты поля по JSON-проекту

```bash
python run_sim.py examples/maxwell_material_port_demo.json --save-field field.png
```

### Экспорт анимации поля

```bash
python run_sim.py examples/maxwell_material_port_demo.json --save-maxwell maxwell.gif --maxwell-mode tmz --field-layer electric
```

## 4. Точки входа и режимы работы

### GUI (`main.py`)

GUI — это основной интерактивный режим. Пользователь работает с объектами `ComponentItem`, `WireItem`, `MaterialRegionItem`, `FieldPortItem` на `QGraphicsScene`.

Поддерживаются действия:

- добавление компонентов из библиотеки;
- удаление выделенного (`Delete`/`Backspace`);
- отмена текущего режима (`Esc`);
- соединение выводов (`Соединить`);
- ручная трассировка провода (`Трассировка`);
- добавление области материала (`Среда`);
- добавление полевого порта (`Порт поля`);
- сохранение/загрузка JSON;
- запуск симуляции (`Старт`);
- пауза/продолжение анимации результатов;
- сброс анимации к первому кадру;
- просмотр квазистатической карты поля;
- просмотр FDTD;
- просмотр Maxwell `TMz`;
- просмотр Maxwell `TEz`.

Особенности GUI:

- графика компонентов рисуется процедурно через Pillow, бинарные PNG-ресурсы не требуются;
- провод визуально меняет цвет в зависимости от температуры;
- LED визуально светится в зависимости от `brightness`;
- предохранитель и лампа накаливания визуально отражают перегрузку/накал;
- амперметр и вольтметр отображают текущие показания поверх иконки;
- двойной клик по `Switch` переключает состояние `closed`.
- двойной клик по `SPDT Switch` меняет положение между `A` и `B`;
- в строке состояния показываются текущий кадр анимации и время;
- кнопка `Сброс анимации` останавливает проигрывание и возвращает сцену к первому кадру.

### CLI (`run_sim.py`)

CLI умеет принимать:

- путь к Python-файлу, который экспортирует `build_circuit()`;
- имя импортируемого Python-модуля;
- путь к JSON-проекту.

Поддерживаемые аргументы:

| Аргумент | Назначение |
| --- | --- |
| `example` | Python-файл, модуль или JSON-проект. |
| `--duration` | Переопределить длительность расчета в секундах. |
| `--dt` | Переопределить шаг интегрирования. |
| `--plot-currents` | Построить графики токов компонентов. |
| `--plot-voltages` | Построить графики напряжений компонентов, ЭДС и показаний вольтметров. |
| `--plot-temp` | Построить графики температур. |
| `--plot-surface-temp` | Построить графики температур корпуса компонентов. |
| `--plot-nodes` | Построить графики напряжений всех узлов. |
| `--plot-power` | Построить графики мощности компонентов. |
| `--plot-power-temperature` | Построить совмещенные графики мощности и температуры. |
| `--plot-energy-storage` | Построить графики накопления заряда и магнитного потока. |
| `--plot-charge` | Построить графики зарядовых наблюдаемых величин. |
| `--plot-iv-xy` | Построить XY-графики `I(U)` для элементов, у которых есть напряжение и ток. |
| `--plot-state` | Построить графики состояний: яркость, накал, SOC, флаги перегрузки и т.п. |
| `--plot-all` | Построить все доступные панели графиков. |
| `--save-plot` | Сохранить график в файл вместо открытия окна. |
| `--save-field` | Экспортировать квазистатическую карту поля. |
| `--save-fdtd` | Экспортировать GIF упрощенной FDTD-волны. |
| `--save-maxwell` | Экспортировать GIF полного 2D Maxwell-решения. |
| `--maxwell-mode {tmz,tez}` | Выбрать режим Maxwell. |
| `--field-layer {potential,electric,magnetic}` | Выбрать слой для экспорта поля/анимации. |

Поведение CLI:

- для Python-модуля длительность и `dt` берутся из `DURATION_S` и `DT_S`, если пользователь не передал overrides;
- для JSON-проекта длительность и `dt` берутся из `project.settings`;
- после расчета CLI печатает итоговые напряжения узлов и итоговые наблюдаемые величины компонентов;
- при построении графиков используются массивы из `SimulationResult`;
- если передан `--save-plot`, нужно выбрать хотя бы одну панель `--plot-*` или использовать `--plot-all`.

## 5. Главные сущности модели

### `Circuit`

`Circuit` в `core/engine.py` — это контейнер симулируемой электрической сети.

Он хранит:

- имя схемы;
- список `components`;
- множество имен узлов `nodes`.

Методы и поведение:

- `add(component)` — добавить компонент в схему;
- `node_order()` — отсортированный список всех узлов, кроме земли;
- `simulate(duration_s, dt_s, max_iters=40, tol=1e-6)` — основной запуск расчета;
- внутренне использует нелинейный решатель, тепловые и ЭМ-связи, адаптивные ретраи и историю по компонентам.

### `Component`

`Component` — базовый класс произвольного элемента с любым числом выводов. Он задает:

- `name`;
- `nodes`;
- `ambient_c`;
- `temperature_c` и `surface_temperature_c`;
- термические параметры (`heat_capacity_j_per_k`, `surface_heat_capacity_j_per_k`, `thermal_resistance_k_per_w`, `junction_thermal_resistance_k_per_w`, `contact_thermal_resistance_k_per_w`);
- последние напряжения, токи и мощность;
- геометрию на холсте (`layout_position_px`, `layout_points_px`, `geometry_scale_m_per_px`);
- коэффициенты `thermal_coupling_gain`, `electromagnetic_gain`, `permittivity_scale`, `mutual_inductance_gain`.

Ключевые методы:

- `start_timestep(time_s, dt_s)` — подготовка к очередному шагу;
- `currents(terminal_voltages, time_s, dt_s)` — вернуть токи на выводах и локальный Якобиан;
- `commit(terminal_voltages, time_s, dt_s)` — зафиксировать состояние после успешного шага;
- `observe()` — вернуть наблюдаемые величины для истории;
- `integrate_temperature(power_w, dt_s)` — обновить тепловое состояние.

### `TwoTerminalComponent`

`TwoTerminalComponent` — частный случай `Component` для двухвыводных ветвей.

Он добавляет:

- `last_voltage_v`, `last_current_a`;
- историю `history_voltage_v_1`, `history_voltage_v_2`, `history_current_a_1`, `history_current_a_2`;
- абстрактный метод `branch_current(voltage_v, time_s, dt_s)`, который возвращает ток ветви и дифференциальную проводимость;
- стандартный пересчет токов по двум выводам и Якобиана вида `[[g, -g], [-g, g]]`.

## 6. Как проект превращается в электрическую сеть

### 6.1 Общая идея

GUI и JSON не описывают MNA-узлы напрямую. Вместо этого проект содержит компоненты, провода, области материала и порты поля. Преобразование в `Circuit` выполняет `CircuitProject.to_circuit()`.

### 6.2 Правила назначения узлов

Алгоритм строгий:

1. Каждый вывод каждого компонента сначала получает собственный узел `n1`, `n2`, `n3`, ...
2. Если компонент типа `Ground`, его единственный вывод принудительно становится узлом `"0"`.
3. Если явного `Ground` в проекте нет, первый неземляной вывод автоматически привязывается к `"0"`.
4. Компоненты типов `Ground` и `Junction` не инстанцируются как электрические элементы. Они участвуют только в топологии.

Следствие:

- JSON-проект может не содержать `Ground`, но тогда земля назначится автоматически первому выводу;
- `Junction` используется как топологическая точка, через которую удобно объединять много проводов.

### 6.3 Как обрабатываются провода

Провод в проекте — это не идеальный короткий замыкатель. Каждый `WireRecord` превращается в один или несколько экземпляров `PhysiWire`.

Алгоритм:

1. Определяются точки маршрута: `a_position -> route_points -> b_position`.
2. Если `auto_length_from_path=true`, физическая длина вычисляется как `path_length_px * meters_per_pixel`.
3. Провод режется на `segment_count` сегментов по правилу:
   - `segment_count = ceil(total_length_m / segment_length_target_m)`,
   - далее число ограничивается `max_segments`,
   - минимум всегда `1`.
4. Между сегментами вставляются промежуточные узлы `nK`.
5. Каждый сегмент получает собственную длину, собственную геометрию на холсте и параметры паразитики.
6. Все сегменты одного GUI-провода объединяются в группу `__wire__<wire_id>` для истории результатов.

Это одна из важнейших особенностей проекта: соединение на холсте электрически моделируется как физический провод с сопротивлением, индуктивностью, емкостью и тепловыми/ЭМ-паразитиками, а не как идеальный net merge.

### 6.4 Что происходит с геометрией

При сохранении из GUI каждый компонент получает `terminal_positions` — абсолютные координаты выводов на сцене. Это используется для:

- визуального восстановления положения выводов;
- построения квазистатической карты поля;
- оценки электромагнитной связи между ветвями.

Если JSON написан вручную и `terminal_positions` пусты, электрическая часть все равно работает, но полевая и геометрическая часть становится грубее, потому что некоторые объекты будут рассматриваться почти как точки.

## 7. Численная модель схемы

### 7.1 Остаток и Якобиан

На каждом временном шаге `Circuit._residual_and_jacobian()` собирает глобальную нелинейную систему:

- `residual` размера `N`, где `N` — число неземляных узлов;
- `jacobian` размера `N x N`.

Для каждого компонента:

- вычисляются напряжения на его выводах;
- вызывается `component.currents(...)`;
- локальные токи суммируются в остаток по узлам;
- локальный Якобиан вносится в глобальный Якобиан.

В диагональ сразу добавляется `GMIN = 1e-9`, чтобы улучшить устойчивость плохо обусловленных систем.

### 7.2 Решатель нелинейной системы

Основная стратегия:

1. Ньютоновская итерация до `max_iters` раз.
2. Решение линейной системы:
   - сначала `np.linalg.solve`;
   - если матрица вырождена, fallback на `np.linalg.lstsq`.
3. Шаг решения клиппируется в диапазон `[-5, 5]` В по каждой переменной.
4. Применяется демпфирование `solution += 0.65 * step`.
5. Критерии остановки:
   - `||residual||_inf < tol`;
   - или `||step||_inf < tol`.

Если Ньютон не сошелся, используется fallback:

- `scipy.optimize.root(..., method="hybr")`.

Если не сошелся и он, шаг считается неуспешным.

### 7.3 Дискретизация по времени

Число шагов задается так:

- `steps = round(duration_s / dt_s)`;
- время хранится как `np.linspace(0.0, steps * dt_s, steps + 1)`.

Это важно:

- фактическое конечное время равно `steps * dt_s`;
- если `duration_s / dt_s` нецелое, финальная длительность после округления может немного отличаться от запрошенной.

### 7.4 Адаптивное дробление шага

Если конкретный шаг не удалось решить, код делает рекурсивный retry:

- текущий шаг делится пополам;
- сначала решается полу-шаг до середины;
- затем еще один полу-шаг до исходного времени;
- глубина рекурсии ограничена (`max_depth=5`);
- минимальный допустимый шаг `min_dt_s=1e-5`.

Состояние компонентов перед попыткой снапшотится и при ошибке полностью восстанавливается.

### 7.5 Адаптивные полные ретраи

Для схем с потенциально трудными быстрыми фронтами `Circuit.simulate()` умеет перезапускать весь расчет с меньшим шагом:

- сначала `1.0 * dt`;
- затем `0.5 * dt`;
- затем `0.25 * dt`;
- затем `0.125 * dt`.

Такие ретраи включаются только если схема содержит признаки быстрых/жестких компонентов:

- компоненты с `rise_time_s`/`fall_time_s`;
- или классы `PulseGenerator`, `RealACGenerator`, `SchockleyDiode`, `LED_ImageActive`, `Varistor`, `MOSFET_Model`.

Если успешен не первый retry, в `result.metadata` добавляются:

- `requested_dt_s`;
- `adaptive_retry=True`;
- `retry_attempt`.

### 7.6 Группировка истории

История результатов хранится не по каждому физическому сегменту провода, а по `group_name`:

- для обычных компонентов `group_name = component.name`;
- для сегментов одного провода `group_name = "__wire__<wire_id>"`.

Агрегация наблюдаемых величин:

- для `power_w`, `voltage_v`, `resistance_ohm`, `inductance_h`, `length_m`, `propagation_delay_s`, `contact_resistance_ohm` значения сегментов суммируются;
- для `temperature_c` и `surface_temperature_c` берется максимум;
- для `current_a` берется среднее по сегментам;
- иначе по умолчанию берется среднее.

## 8. Тепловая модель

Каждый физический компонент имеет двухузловую тепловую модель:

- температура кристалла/внутренней массы `temperature_c`;
- температура корпуса/поверхности `surface_temperature_c`.

Тепловой шаг:

1. электрическая модель вычисляет выделяемую мощность;
2. `integrate_temperature()` переносит тепло от внутреннего узла к поверхности;
3. поверхность охлаждается в среду через `thermal_resistance_k_per_w`.

В `core.physics.thermal_step()` используется явный шаг:

- охлаждение к среде пропорционально `(temp_c - ambient_c) / thermal_resistance_k_per_w`;
- изменение температуры обратно пропорционально теплоемкости.

Дополнительно схема строит тепловые связи между компонентами:

- если компоненты сидят на общем электрическом узле, это усиливает тепловую связь;
- если у них есть координаты на холсте и расстояние меньше примерно `0.18 м` в пересчете по `geometry_scale_m_per_px`, создается дополнительная связь по близости;
- интенсивность связи масштабируется `thermal_coupling_gain`.

Итог: нагрев одного компонента может частично подогревать соседние.

## 9. Приближенная электромагнитная связь проводников

Для двухвыводных компонентов с геометрией из `layout_points_px` может строиться приближенная взаимная связь.

Условия включения связи:

- есть минимум две геометрические точки;
- `electromagnetic_gain > 0`;
- ветви не принадлежат одной и той же группе;
- расстояние между центрами не больше примерно `0.08 м`;
- ориентация ветвей достаточно параллельна (`orientation >= 0.25`).

Для каждой пары оцениваются:

- взаимная емкость `mutual_capacitance_f`;
- взаимная индуктивность `mutual_inductance_h`.

Обе величины вычисляются эвристически из:

- длины перекрытия;
- расстояния;
- относительной ориентации;
- `electromagnetic_gain`;
- `permittivity_scale`;
- `mutual_inductance_gain`.

Далее связь вносится в электрическую систему как дополнительная дифференциальная ветвь между двумя двухполюсниками.

Важно: это не строгая 3D-электродинамика и не RLGC-линейка с распределенными уравнениями. Это инженерное приближение, полезное для качественного учета взаимной паразитной связи между близкими трассами.

## 10. Физические константы и материалы

В `core/physics.py` определены:

- `EPSILON_0 = 8.8541878128e-12` Ф/м;
- `MU_0 = 1.25663706212e-6` Гн/м;
- `ELEMENTARY_CHARGE = 1.602176634e-19` Кл;
- `BOLTZMANN = 1.380649e-23` Дж/К;
- `ROOM_TEMPERATURE_C = 25.0`;
- `GMIN = 1e-9`.

Материалы проводов:

| Ключ | Название | Удельное сопротивление, Ом·м | ТКС | Плотность, кг/м³ | Теплоемкость, Дж/(кг·К) |
| --- | --- | --- | --- | --- | --- |
| `copper` | Copper | `1.68e-8` | `0.00393` | `8960` | `385` |
| `aluminum` | Aluminum | `2.82e-8` | `0.00429` | `2700` | `897` |
| `nichrome` | Nichrome | `1.10e-6` | `0.0004` | `8400` | `450` |
| `tungsten` | Tungsten | `5.60e-8` | `0.0045` | `19300` | `134` |

Кривые химии батарей:

- `alkaline`;
- `liion`;
- `leadacid`.

Они влияют на:

- зависимость напряжения холостого хода от `state_of_charge`;
- рост внутреннего сопротивления на холоде;
- штраф по разряду.

## 11. Библиотека компонентов

### 11.1 Важное различие: Python API vs GUI/JSON defaults

В проекте есть два уровня параметров:

1. Полный Python-конструктор класса.
2. Подмножество параметров, которые seed-ятся из `COMPONENT_LIBRARY` и поэтому появляются в GUI по умолчанию.

Это принципиально:

- `RealResistor` в Python принимает `tolerance`, `tolerance_bias`, `temperature_coefficient`, тепловые параметры и `ambient_c`;
- но в GUI новый резистор стартует только с `{"resistance_ohm": 220.0}`;
- если вы хотите использовать расширенные параметры через JSON, их можно дописать вручную в `params`, и `create_component()` передаст их в конструктор;
- исключение — служебные routing-поля провода (`auto_length_from_path`, `meters_per_pixel`, `segment_length_target_m`, `max_segments`, `coupling_gain`, `permittivity_scale`, `mutual_inductance_gain`, `thermal_coupling_gain`): они используются на этапе сборки сети и удаляются перед созданием конкретного объекта `PhysiWire`.

### 11.2 Неактивные топологические типы

#### `Ground`

- Выводы: `ground`.
- Электрически не инстанцируется как компонент.
- Любой его вывод становится узлом `"0"`.

#### `Junction`

- Выводы: `node`.
- Электрически не инстанцируется как компонент.
- Используется как топологическая точка для удобного объединения проводов.

### 11.3 Источники

#### `Battery` (`PhysiBattery`)

- Выводы: `positive`, `negative`.
- GUI default params: `nominal_voltage_v=9.0`, `capacity_mah=550.0`, `chemistry="alkaline"`, `internal_resistance_ohm=1.2`.
- Дополнительные Python-параметры: `initial_soc=1.0`, `discharge_enabled=True`, `ambient_c=25.0`.
- Модель:
  - источник Тевенина с напряжением холостого хода `open_circuit_voltage()`;
  - внутреннее сопротивление зависит от SOC, температуры и текущего тока;
  - SOC уменьшается от разрядного тока.
- При `discharge_enabled=false` SOC фиксируется, и батарея не разряжается в ходе симуляции.
- Наблюдаемые величины: `temperature_c`, `surface_temperature_c`, `power_w`, `voltage_v`, `current_a`, `soc`, `open_circuit_voltage_v`, `internal_resistance_ohm`, `discharge_enabled`.
- Нюанс GUI: поле `chemistry` в панели свойств скрыто (`HIDDEN_USER_PARAMS`), но в Python и JSON поддерживается.

#### `AC Generator` (`RealACGenerator`)

- Выводы: `positive`, `negative`.
- GUI default params: `amplitude_v=5.0`, `frequency_hz=1000.0`, `internal_resistance_ohm=0.5`.
- Дополнительные Python-параметры: `phase_rad=0.0`, `phase_noise_rad=0.01`, `frequency_error=0.0`, `harmonic_2_ratio=0.03`, `harmonic_3_ratio=0.01`, `ambient_c=25.0`.
- Модель:
  - синусоидальный источник Тевенина;
  - добавляет фазовый шум;
  - поддерживает ошибку частоты и 2-ю/3-ю гармоники.
- Наблюдаемые величины: `temperature_c`, `surface_temperature_c`, `power_w`, `voltage_v`, `current_a`, `emf_v`, `frequency_hz`.

#### `Pulse Generator` (`PulseGenerator`)

- Выводы: `positive`, `negative`.
- GUI default params: `high_voltage_v=5.0`, `low_voltage_v=0.0`, `period_s=1.0`, `duty_cycle=0.5`, `pulse_width_s=0.2`, `rise_time_s=1e-3`, `fall_time_s=1e-3`, `internal_resistance_ohm=0.8`.
- Полный Python-конструктор допускает `pulse_width_s=None`, тогда ширина импульса считается как `period_s * duty_cycle`.
- Модель:
  - источник Тевенина прямоугольного сигнала;
  - фронт и спад сглаживаются косинусным профилем;
  - источник сам нагревается на своем внутреннем сопротивлении.
- Наблюдаемые величины: `temperature_c`, `surface_temperature_c`, `power_w`, `voltage_v`, `current_a`, `emf_v`, `period_s`, `duty_cycle`, `pulse_width_s`.

### 11.4 Резистивные и сенсорные элементы

#### `Resistor` (`RealResistor`)

- Выводы: `positive`, `negative`.
- GUI default params: `resistance_ohm=220.0`.
- Полные Python-параметры: `resistance_ohm` (обязательный), `tolerance=0.05`, `tolerance_bias=0.0`, `temperature_coefficient=0.0039`, `heat_capacity_j_per_k=7.5`, `thermal_resistance_k_per_w=30.0`, `ambient_c=25.0`.
- Модель:
  - линейный резистор;
  - фактическое сопротивление один раз смещается допуском;
  - затем меняется с температурой по ТКС;
  - выделяемая мощность идет в тепловую модель.
- Наблюдаемые величины: `temperature_c`, `surface_temperature_c`, `power_w`, `voltage_v`, `current_a`, `resistance_ohm`, `tolerance`.

#### `Thermistor` (`Thermistor`)

- Выводы: `positive`, `negative`.
- GUI default params: `resistance_at_25c_ohm=10000.0`, `beta_k=3950.0`.
- Дополнительные Python-параметры: `series_resistance_ohm=0.0`, `ambient_c=25.0`.
- Модель:
  - NTC по Beta-модели;
  - сопротивление зависит от абсолютной температуры;
  - доступен дополнительный последовательный резистор.
- Наблюдаемые величины: `temperature_c`, `surface_temperature_c`, `power_w`, `voltage_v`, `current_a`, `resistance_ohm`, `beta_k`.

#### `Photoresistor` (`Photoresistor`)

- Выводы: `positive`, `negative`.
- GUI default params: `dark_resistance_ohm=2e6`, `light_resistance_ohm=350.0`, `illumination_lux=120.0`, `lux_reference=100.0`, `gamma=0.78`.
- Дополнительные Python-параметры: `ambient_c=25.0`.
- Модель:
  - сопротивление уменьшается с освещенностью;
  - температурный фактор также влияет на сопротивление;
  - модель ориентирована на качественную зависимость, а не на конкретный даташит.
- Наблюдаемые величины: `temperature_c`, `surface_temperature_c`, `power_w`, `voltage_v`, `current_a`, `resistance_ohm`, `illumination_lux`.

#### `Wire` (`PhysiWire`)

- Выводы: `positive`, `negative`.
- Обычно создается не вручную, а автоматически из проводов GUI/JSON.
- GUI default params:
  - `length_m=0.3`,
  - `area_mm2=0.75`,
  - `material="copper"`,
  - `dielectric_conductance_s_per_m=2e-10`,
  - `proximity_gain=0.003`,
  - `auto_length_from_path=true`,
  - `meters_per_pixel=0.002`,
  - `segment_length_target_m=0.06`,
  - `max_segments=12`,
  - `coupling_gain=1.0`,
  - `permittivity_scale=1.0`,
  - `mutual_inductance_gain=1.0`,
  - `thermal_coupling_gain=1.0`,
  - `contact_resistance_ohm=0.0`.
- Полные Python-параметры дополнительно включают:
  - `skin_effect_gain=0.015`,
  - `inductance_per_m_h=7.5e-7`,
  - `shunt_capacitance_f_per_m=6e-11`,
  - `internal_inductance_ratio=0.35`,
  - `diffusion_time_constant_s_per_m=2.5e-7`,
  - `ambient_c=25.0`.
- Модель:
  - сопротивление зависит от материала, длины, сечения и температуры;
  - есть skin-effect, proximity-effect и диффузионная память `skin_memory`;
  - есть последовательная индуктивность, шунтирующая емкость и диэлектрическая проводимость;
  - есть контактное сопротивление;
  - есть оценка задержки распространения `propagation_delay_s`.
- Наблюдаемые величины: `temperature_c`, `surface_temperature_c`, `power_w`, `voltage_v`, `current_a`, `resistance_ohm`, `inductance_h`, `length_m`, `material`, `propagation_delay_s`, `contact_resistance_ohm`.

#### `Switch` (`ToggleSwitch`)

- Выводы: `positive`, `negative`.
- GUI default params: `closed=false`.
- Дополнительные Python-параметры: `on_resistance_ohm=0.01`, `off_resistance_ohm=1e9`, `ambient_c=25.0`.
- Модель: простая коммутация между низким и очень высоким сопротивлением.
- Наблюдаемые величины: `temperature_c`, `surface_temperature_c`, `power_w`, `voltage_v`, `current_a`, `closed`.
- GUI-особенность: двойной клик по элементу переключает `closed`.

### 11.5 Реактивные элементы

#### `Capacitor` (`RealCapacitor`)

- Выводы: `positive`, `negative`.
- GUI default params: `capacitance_f=100e-6`, `max_voltage_v=16.0`.
- Полные Python-параметры: `esr_ohm=0.12`, `esl_h=2e-8`, `leak_resistance_ohm=2e6`, `heat_capacity_j_per_k=6.0`, `thermal_resistance_k_per_w=22.0`, `ambient_c=25.0`.
- Модель:
  - companion model для переходных процессов;
  - ESR, ESL, утечка;
  - пробой выше `max_voltage_v`, который добавляет сильную проводимость;
  - ведется внутреннее напряжение на самом конденсаторе `capacitor_voltage_v`.
- Наблюдаемые величины: `temperature_c`, `surface_temperature_c`, `power_w`, `voltage_v`, `current_a`, `capacitance_f`, `capacitor_voltage_v`, `charge_c`, `breakdown`.

#### `Inductor` (`RealInductor`)

- Выводы: `positive`, `negative`.
- GUI default params: `inductance_h=220e-6`, `dc_resistance_ohm=0.2`.
- Полные Python-параметры: `saturation_current_a=2.0`, `relative_permeability=25.0`, `interwinding_capacitance_f=3e-11`, `heat_capacity_j_per_k=12.0`, `thermal_resistance_k_per_w=20.0`, `ambient_c=25.0`.
- Модель:
  - companion model индуктивности;
  - сопротивление меди зависит от температуры;
  - эффективная индуктивность уменьшается при насыщении через `saturation_curve()`;
  - есть межвитковая емкость.
- Наблюдаемые величины: `temperature_c`, `surface_temperature_c`, `power_w`, `voltage_v`, `current_a`, `inductance_h`, `magnetic_current_a`, `flux_linkage_wb`.

### 11.6 Полупроводники и защита

#### `Diode` (`SchockleyDiode`)

- Выводы: `positive`, `negative`.
- GUI default params:
  - `transit_time_s=1.5e-8`,
  - `reverse_recovery_tau_s=7.5e-8`,
  - `junction_area_um2=60000.0`,
  - `doping_p_cm3=1e17`,
  - `doping_n_cm3=5e16`,
  - `carrier_lifetime_s=2e-6`.
- Полный Python-конструктор дополнительно поддерживает:
  - `saturation_current_a=1e-12`,
  - `emission_coefficient=1.9`,
  - `barrier_capacitance_f=4e-11`,
  - `forward_drop_v=0.72`,
  - `breakdown_voltage_v=70.0`,
  - `avalanche_softness_v=3.0`,
  - `shunt_resistance_ohm=5e7`,
  - `intrinsic_carrier_density_cm3=1e10`,
  - `relative_permittivity=11.7`,
  - `heat_capacity_j_per_k=3.0`,
  - `thermal_resistance_k_per_w=18.0`,
  - `ambient_c=25.0`.
- Модель:
  - экспоненциальный диод Шокли;
  - рекомбинационный ток;
  - барьерная и физическая junction capacitance;
  - transit time и диффузионная емкость;
  - stored charge и reverse recovery;
  - лавинный пробой в обратном направлении;
  - расчет встроенного потенциала, ширины обедненной области и пикового поля.
- Наблюдаемые величины: `temperature_c`, `surface_temperature_c`, `power_w`, `voltage_v`, `current_a`, `junction_capacitance_f`, `forward_drop_v`, `stored_charge_c`, `built_in_potential_v`, `depletion_width_m`, `peak_field_v_m`.

#### `LED` (`LED_ImageActive`)

- Выводы: `positive`, `negative`.
- GUI default params: `color="red"`, `max_forward_current_a=0.02`.
- Дополнительные LED-параметры: `luminous_efficiency=0.25`, `burn_energy_j=0.03`, `ambient_c=25.0`.
- Дополнительно LED наследует все параметры диода через `**kwargs`.
- Модель:
  - базовая ВАХ и емкостные эффекты наследуются от `SchockleyDiode`;
  - рассчитывается яркость `brightness` по току;
  - накапливается энергия повреждения `damage_j`;
  - при сильном перегрузе LED помечается как `failed`.
- Наблюдаемые величины: все наблюдаемые диода плюс `brightness`, `failed`, `flash`, `color`.

#### `Varistor` (`Varistor`)

- Выводы: `positive`, `negative`.
- GUI default params: `clamp_voltage_v=18.0`, `dynamic_resistance_ohm=1.5`, `leakage_current_a=2e-6`, `nonlinear_exponent=6.0`.
- Дополнительный Python-параметр: `ambient_c=25.0`.
- Модель:
  - малый ток утечки ниже порога;
  - нелинейное ограничение при превышении `clamp_voltage_v`;
  - нагрев пропорционален рассеиваемой мощности.
- Наблюдаемые величины: `temperature_c`, `surface_temperature_c`, `power_w`, `voltage_v`, `current_a`, `clamp_voltage_v`, `clamping_active`.

#### `Fuse` (`RealFuse`)

- Выводы: `positive`, `negative`.
- GUI default params: `current_rating_a=1.0`.
- Полные Python-параметры: `cold_resistance_ohm=0.05`, `melting_temperature_c=220.0`, `i2t_trip=1.6`, `ambient_c=25.0`.
- Модель:
  - низкое сопротивление в холодном состоянии;
  - накапливает `stress_i2t`;
  - перегорает либо по температуре, либо по интегралу `I²t`;
  - после срабатывания становится почти разрывом (`1e9 Ом`).
- Наблюдаемые величины: `temperature_c`, `surface_temperature_c`, `power_w`, `voltage_v`, `current_a`, `blown`, `stress_i2t`.

### 11.7 Активные элементы

#### `MOSFET` (`MOSFET_Model`)

- Выводы: `drain`, `gate`, `source`.
- GUI default params:
  - `threshold_v=3.2`,
  - `rds_on_ohm=0.08`,
  - `cgs_f=4.2e-10`,
  - `cgd_f=1.8e-10`,
  - `cds_f=1.4e-10`,
  - `reverse_recovery_tau_s=8e-8`,
  - `trap_relaxation_s=2e-5`,
  - `channel_width_um=2500.0`,
  - `channel_length_um=1.2`,
  - `oxide_thickness_nm=35.0`,
  - `mobility_cm2_v_s=420.0`,
  - `overlap_length_um=0.28`,
  - `body_doping_cm3=2.5e16`,
  - `max_current_a=20.0`.
- Полные Python-параметры дополнительно включают:
  - `transconductance_a_v2=1.2`,
  - `channel_length_modulation=0.02`,
  - `gate_capacitance_f=6e-10`,
  - `cgs_f=None`,
  - `cgd_f=None`,
  - `gate_leakage_ohm=5e9`,
  - `subthreshold_current_a=1e-9`,
  - `subthreshold_swing_factor=1.45`,
  - `body_diode_saturation_current_a=5e-11`,
  - `body_diode_emission=1.8`,
  - `output_conductance_s=2e-5`,
  - `relative_permittivity_ox=3.9`,
  - `ambient_c=25.0`.
- Модель:
  - нелинейный канал с режимами `cutoff`, `subthreshold`, `linear`, `saturation`, включая обратные аналоги;
  - физически мотивированная оксидная емкость через геометрию канала;
  - отдельные `Cgs`, `Cgd`, `Cds`;
  - утечки затвора;
  - body diode и ее reverse recovery;
  - trapping/релаксация `trap_state`;
  - ограничения по `max_current_a`;
  - температурная зависимость `beta`, `Rds(on)` и порога.
- Наблюдаемые величины: `temperature_c`, `surface_temperature_c`, `power_w`, `drain_current_a`, `gate_current_a`, `source_current_a`, `mode`, `cgs_f`, `cgd_f`, `cds_f`, `trap_state`, `oxide_capacitance_f`, `inversion_charge_c`, `oxide_field_v_m`, `channel_field_v_m`.

#### `OpAmp` (`PhysiOpAmp`)

- Выводы: `plus`, `minus`, `out`.
- GUI default params: `open_loop_gain=2e5`, `dominant_pole_hz=12.0`, `output_current_limit_a=0.035`, `input_bias_current_a=8e-8`.
- Полные Python-параметры дополнительно:
  - `input_resistance_ohm=2e6`,
  - `output_resistance_ohm=60.0`,
  - `slew_rate_v_s=6e5`,
  - `common_mode_rejection=9e4`,
  - `power_supply_rejection=1.5e5`,
  - `input_offset_v=0.0`,
  - `supply_min_v=-12.0`,
  - `supply_max_v=12.0`,
  - `quiescent_current_a=0.002`,
  - `ambient_c=25.0`.
- Модель:
  - ограниченное усиление по ошибке входов;
  - dominant pole и slew-rate limit;
  - входные токи смещения;
  - CMRR и PSRR;
  - ограничение выходного тока;
  - внутреннее состояние `internal_drive_v`.
- Наблюдаемые величины: `temperature_c`, `surface_temperature_c`, `power_w`, `output_target_v`, `output_current_a`, `dominant_node_v`, `current_limit`.

### 11.8 Индикация и измерение

#### `Bulb` (`IncandescentBulb`)

- Выводы: `positive`, `negative`.
- GUI default params: `rated_voltage_v=12.0`, `rated_power_w=21.0`.
- Полные Python-параметры: `cold_ratio=10.0`, `filament_operating_temp_c=2400.0`, `ambient_c=25.0`.
- Модель:
  - горячее сопротивление определяется по `V²/P`;
  - холодное сопротивление меньше в `cold_ratio` раз;
  - по температуре растет сопротивление нити;
  - вычисляется показатель свечения `glow`.
- Наблюдаемые величины: `temperature_c`, `surface_temperature_c`, `power_w`, `voltage_v`, `current_a`, `resistance_ohm`, `glow`.

#### `Ammeter` (`Ammeter`)

- Выводы: `positive`, `negative`.
- GUI default params: `shunt_resistance_ohm=0.01`, `max_display_current_a=10.0`.
- Дополнительные Python-параметры: `lead_inductance_h=2.5e-8`, `ambient_c=25.0`.
- Модель:
  - шунт с малым сопротивлением;
  - учтена индуктивность выводов;
  - при превышении лимита ставится флаг `overload`.
- Наблюдаемые величины: `temperature_c`, `surface_temperature_c`, `power_w`, `voltage_v`, `current_a`, `reading_a`, `overload`.

#### `Voltmeter` (`Voltmeter`)

- Выводы: `positive`, `negative`.
- GUI default params: `input_resistance_ohm=1e7`, `max_display_voltage_v=300.0`.
- Дополнительные Python-параметры: `input_capacitance_f=1.8e-11`, `ambient_c=25.0`.
- Модель:
  - большое входное сопротивление;
  - входная емкость;
  - рассчитывается собственный входной ток;
  - при превышении лимита ставится `overload`.
- Наблюдаемые величины: `temperature_c`, `surface_temperature_c`, `power_w`, `voltage_v`, `current_a`, `reading_v`, `input_current_a`, `overload`.

## 12. Результаты симуляции (`SimulationResult`)

`SimulationResult` содержит:

- `time_s: np.ndarray` — временная ось;
- `node_voltages: dict[str, np.ndarray]` — история напряжений по узлам;
- `component_observables: dict[str, dict[str, np.ndarray]]` — история наблюдаемых величин по компонентам/группам;
- `metadata: dict[str, Any]`.

Стандартные поля `metadata`:

- `name`;
- `duration_s`;
- `dt_s`;
- `nodes`;
- `components`;
- `electromagnetic_links`;
- `adaptive_substeps`.

Возможны дополнительные поля:

- `requested_dt_s`;
- `adaptive_retry`;
- `retry_attempt`.

Вспомогательные методы:

- `final_node_voltage(node)`;
- `final_observable(component, key)`.

## 13. Полевые решатели

### 13.1 Общая идея

Все полевые решатели опираются не на абстрактный netlist, а на геометрию компонентов и проводов на холсте. Если схема создана только в Python без геометрии, полевая часть либо будет грубой, либо вообще не сможет построить осмысленную картину.

Исходная геометрия берется из:

- `component.layout_points_px`;
- `component.layout_position_px`;
- `circuit.field_material_regions`;
- `circuit.field_ports`.

### 13.2 Квазистатическое поле (`solve_quasi_static_field`)

Решатель:

- строит прямоугольную сетку по bounding box схемы с `padding_px`;
- материалам назначает карты `epsilon_r`, `sigma_s_per_m`, `mu_r`;
- проводники фиксирует по потенциалам, известным из последнего шага схемотехнического расчета;
- решает взвешенную релаксацию по потенциалу;
- затем получает:
  - `potential_v`,
  - `electric_field_v_m = |grad(phi)|`,
  - `magnetic_flux_density_t`.

Как вычисляется магнитная часть:

- для каждого двухвыводного элемента с геометрией строится токовый сегмент;
- используется приближенная формула, похожая на Biot-Savart для конечного сегмента через его середину и направление;
- итоговая магнитная карта берется по модулю.

Метаданные `FieldSnapshot.metadata`:

- `grid_width`, `grid_height`;
- `scale_m_per_px`;
- `iterations`;
- `materials_count`;
- `ports_count`;
- `reference_frequency_hz`;
- `solver="quasi_static_weighted"`.

### 13.3 Полевые порты

Порты могут быть:

- явно заданы в `field_ports` проекта;
- автоматически синтезированы из источников `Battery`, `RealACGenerator`, `PulseGenerator`, если явных портов нет.

Если нет ни явного полевого порта, ни подходящего источника для автогенерации порта, `simulate_fdtd_wave()` и `simulate_full_wave_maxwell_2d()` завершатся ошибкой: для этих режимов нужен хотя бы один источник возбуждения поля.

Поддерживаемые формы сигнала в `_port_signal()`:

- `sine`;
- `step`;
- `pulse`;
- `gaussian`.

Поддерживаемые режимы возбуждения:

- `source_kind="voltage"`;
- `source_kind="current"`.

### 13.4 Упрощенная FDTD (`simulate_fdtd_wave`)

Это не полный векторный Maxwell, а скалярная волновая модель на потенциале:

- используется карта фазовой скорости `c_map = c0 / sqrt(epsilon_r * mu_r)`;
- строится явная разностная схема по времени;
- учитываются потери через `sigma_s_per_m`;
- границы зануляются;
- порты прикладывают возбуждение на маску порта.

Результат — `FieldWaveSequence` с:

- статической картой `potential_v`;
- последовательностью `electric_frames_v_m`;
- последовательностью `magnetic_frames_t`.

Метаданные:

- `solver="fdtd_scalar_materials"`;
- `time_step_s`;
- `steps`;
- `source_period_steps`;
- `materials_count`;
- `ports_count`;
- `note` — предупреждение для медленных схем.

### 13.5 Полный 2D Maxwell (`simulate_full_wave_maxwell_2d`)

Поддерживаются два режима.

#### `TMz`

Переменные:

- `Ez`;
- `Hx`;
- `Hy`.

Особенности:

- используется CFL-ограниченный шаг;
- края снабжены поглощающим слоем через дополнительную проводимость `sigma_absorb`;
- PEC-области зануляют `Ez`;
- строятся кадры `|Ez|` и `|B|`.

Метаданные: `solver="maxwell_2d_tmz"`.

#### `TEz`

Переменные:

- `Ex`;
- `Ey`;
- `Hz`.

Особенности:

- аналогично используется явная схема и поглощающий слой;
- возбуждение порта прикладывается векторно по направлению `rotation_deg`;
- дополнительно используется сглаживание `_low_pass_field()` и внутреннее затухание, чтобы стабилизировать картину.

Метаданные: `solver="maxwell_2d_tez"`.

### 13.6 PEC и материалы

Если в `material_regions` для области задано `sigma_s_per_m >= 5e5`, в Maxwell-решателях такая область интерпретируется как PEC и добавляется в `pec_mask`.

### 13.7 Ограничения полевой части

Полевой модуль полезен как приближенный инженерный визуализатор, но не как строгий 3D-полевой CAD/EM-солвер. Ограничения:

- 2D, а не 3D;
- геометрия — прямоугольные области материалов и маски портов;
- проводники берутся из схемной геометрии на холсте;
- FDTD-режим упрощен и скалярен;
- Maxwell считает сверхбыстрый ЭМ-отклик, а не «медленную» бытовую динамику длительностью миллисекунды/секунды.

Именно поэтому код иногда добавляет предупреждение вида:

> низкочастотная схема: Maxwell показывает только сверхбыстрый ЭМ-отклик, а не мигание LED.

## 14. Формат проекта JSON

### 14.1 Текущая версия схемы

Текущая константа:

- `SCHEMA_VERSION = 3`.

При этом загрузчик не валидирует жестко номер версии. Если в JSON отсутствуют новые поля, применяются значения по умолчанию. Поэтому старый `examples/led_project.json` со `schema_version=1` до сих пор загружается.

### 14.2 Полный каркас проекта

```json
{
  "schema_version": 3,
  "name": "Имя проекта",
  "settings": {
    "duration_s": 0.03,
    "dt_s": 0.0001
  },
  "components": [],
  "material_regions": [],
  "field_ports": [],
  "wires": []
}
```

### 14.3 `settings`

```json
{
  "duration_s": 0.03,
  "dt_s": 0.0001
}
```

Поля:

- `duration_s` — длительность расчета в секундах, должна быть `> 0`;
- `dt_s` — шаг интегрирования, должен быть `> 0`.

### 14.4 `components`

Каждая запись — `ComponentRecord`:

```json
{
  "component_id": 1,
  "kind": "Resistor",
  "name": "R1",
  "x": 420.0,
  "y": 220.0,
  "rotation_deg": 0.0,
  "params": {
    "resistance_ohm": 330.0
  },
  "terminal_positions": [
    [356.0, 220.0],
    [484.0, 220.0]
  ]
}
```

Поля:

- `component_id` — уникальный целый ID;
- `kind` — тип компонента;
- `name` — уникальное имя;
- `x`, `y` — центр объекта на сцене;
- `rotation_deg` — угол поворота на холсте;
- `params` — словарь параметров компонента;
- `terminal_positions` — список абсолютных координат выводов на сцене.

Поддерживаемые `kind`:

- `Ground`
- `Junction`
- `Battery`
- `AC Generator`
- `Pulse Generator`
- `Resistor`
- `Thermistor`
- `Photoresistor`
- `Capacitor`
- `Inductor`
- `Wire` — используется служебно в библиотеке, но на практике GUI создает провода отдельным массивом `wires`, а не как компонент
- `Diode`
- `LED`
- `Varistor`
- `MOSFET`
- `OpAmp`
- `Fuse`
- `Bulb`
- `Ammeter`
- `Voltmeter`
- `Switch`

### 14.5 `wires`

Каждая запись — `WireRecord`:

```json
{
  "wire_id": 1,
  "a": {
    "component_id": 1,
    "terminal_index": 0
  },
  "b": {
    "component_id": 2,
    "terminal_index": 0
  },
  "params": {
    "area_mm2": 0.75,
    "auto_length_from_path": true
  },
  "route_points": [
    [280.0, 120.0],
    [320.0, 160.0]
  ],
  "path_length_px": 132.5,
  "a_position": [234.0, 120.0],
  "b_position": [356.0, 120.0]
}
```

Поля:

- `wire_id` — уникальный ID провода;
- `a`, `b` — ссылка на выводы через `component_id` и `terminal_index`;
- `params` — параметры будущего `PhysiWire` и сборки маршрута;
- `route_points` — промежуточные точки маршрута;
- `path_length_px` — длина трассы в пикселях;
- `a_position`, `b_position` — фактические координаты концов.

`terminal_index` отсчитывается от порядка выводов:

| Тип | Порядок выводов |
| --- | --- |
| `Battery`, `AC Generator`, `Pulse Generator`, `Resistor`, `Thermistor`, `Photoresistor`, `Capacitor`, `Inductor`, `Diode`, `LED`, `Varistor`, `Fuse`, `Bulb`, `Ammeter`, `Voltmeter`, `Switch` | `positive`, `negative` |
| `MOSFET` | `drain`, `gate`, `source` |
| `OpAmp` | `plus`, `minus`, `out` |
| `Ground` | `ground` |
| `Junction` | `node` |

### 14.6 Параметры провода в `wires[].params`

Поддерживаются два слоя параметров.

#### Параметры построения маршрута и сегментации

- `auto_length_from_path`
- `meters_per_pixel`
- `segment_length_target_m`
- `max_segments`
- `coupling_gain`
- `permittivity_scale`
- `mutual_inductance_gain`
- `thermal_coupling_gain`

Эти ключи важны на стадии `CircuitProject.to_circuit()`, но затем не передаются в конструктор `PhysiWire`.

#### Электрические параметры каждого сегмента

- `length_m`
- `area_mm2`
- `material`
- `skin_effect_gain`
- `inductance_per_m_h`
- `shunt_capacitance_f_per_m`
- `dielectric_conductance_s_per_m`
- `proximity_gain`
- `internal_inductance_ratio`
- `diffusion_time_constant_s_per_m`
- `contact_resistance_ohm`
- `ambient_c`

### 14.7 `material_regions`

Каждая запись — `MaterialRegionRecord`:

```json
{
  "region_id": 1,
  "name": "FR4",
  "x": 430.0,
  "y": 220.0,
  "params": {
    "width_px": 560.0,
    "height_px": 240.0,
    "rotation_deg": 0.0,
    "epsilon_r": 4.3,
    "sigma_s_per_m": 0.0,
    "mu_r": 1.0
  }
}
```

Поддерживаемые `params`:

- `width_px`
- `height_px`
- `rotation_deg`
- `epsilon_r`
- `sigma_s_per_m`
- `mu_r`

Назначение:

- область влияет только на полевые решатели;
- на схемотехнический решатель напрямую она не влияет.

### 14.8 `field_ports`

Каждая запись — `FieldPortRecord`:

```json
{
  "port_id": 1,
  "name": "PORT1",
  "x": 270.0,
  "y": 140.0,
  "params": {
    "width_px": 80.0,
    "height_px": 18.0,
    "rotation_deg": 0.0,
    "source_kind": "voltage",
    "waveform": "sine",
    "amplitude_v": 4.0,
    "amplitude_a": 0.1,
    "frequency_hz": 1500000.0,
    "phase_rad": 0.0,
    "impedance_ohm": 50.0
  }
}
```

Базовые параметры GUI:

- `width_px`
- `height_px`
- `rotation_deg`
- `source_kind`
- `waveform`
- `amplitude_v`
- `amplitude_a`
- `frequency_hz`
- `phase_rad`
- `impedance_ohm`

Дополнительные параметры, которые понимает `_port_signal()` при ручном JSON:

- `period_s`
- `pulse_width_s`
- `rise_time_s`
- `fall_time_s`
- `low_level_v`

### 14.9 Проверки при загрузке проекта

`CircuitProject.validate()` гарантирует:

- уникальность `component_id`;
- уникальность `region_id`;
- уникальность `port_id`;
- валидность `kind` для всех компонентов;
- существование компонентов, на которые ссылаются провода;
- валидность `terminal_index` для проводов;
- положительность `duration_s` и `dt_s`.

## 15. JSON-примеры в `examples/`

### `examples/component_showcase/`

- Это основной новый каталог из 17 простых демонстрационных схем по компонентам.
- Суммарно он покрывает `Battery`, `AC Generator`, `Pulse Generator`, `Resistor`, `Capacitor`, `Inductor`, `Thermistor`, `Photoresistor`, `Diode`, `LED`, `Varistor`, `MOSFET`, `OpAmp`, `Fuse`, `Bulb`, `Ammeter`, `Voltmeter`, `Switch`, `SPDT Switch`, `Ground`, `Junction` и физические `Wire`.
- Внутри лежит отдельный файл `examples/component_showcase/README.md`, где по каждой схеме расписано:
  - что именно она показывает;
  - какие флаги графиков лучше запускать;
  - что по этим графикам анализировать;
  - какие параметры удобно менять для демонстрации.
- Если нужно быстро показать проект на защите, обычно достаточно начать с:
  - `01_battery_resistor_measurement.json`
  - `05_rc_charge_discharge.json`
  - `07_diode_half_wave_rectifier.json`
  - `15_mosfet_led_switch.json`

### `examples/adders/`

- Каталог с учебными сумматорами на простых элементах.
- Сейчас там есть `half_adder_switches.json` и скрипт `half_adder_runner.py`.
- Это удобный мост между одиночными логическими схемами и более осмысленной цифровой функцией “сложение битов”.
- Через `half_adder_runner.py` можно подавать входы `A` и `B` из CLI и сразу получать `SUM` и `CARRY`.

### `examples/led_project.json`

- Минимальный старый JSON-проект со `schema_version=1`.
- Показывает базовую батарею, резистор, LED и землю.
- Полезен как самый короткий пример структуры.

### `examples/photoresistor_demo.json`

- Демонстрирует цепь `Battery -> Photoresistor -> Resistor -> LED`.
- Показывает зависимость светодиода от освещенности `illumination_lux`.

### `examples/thermistor_divider.json`

- Делитель напряжения на фиксированном резисторе и термисторе.
- Отдельно добавлен `Voltmeter`.

### `examples/triple_led_blink.json`

- Три независимые ветви с `Pulse Generator`, резистором и LED.
- У всех генераторов разные периоды.
- Хорош для просмотра анимации состояний в GUI.

### `examples/varistor_surge_clamp.json`

- Импульсный источник перенапряжения, резистор-ограничитель, варистор, вольтметр.
- Демонстрирует нелинейное ограничение напряжения.

### `examples/maxwell_material_port_demo.json`

- Простая DC-цепь с батареей, резистором и LED.
- Добавлена область материала `FR4`.
- Добавлен явный полевой порт.
- Это базовый пример для `Карта поля`, `FDTD`, `Maxwell TMz`, `Maxwell TEz`.

### `examples/beat_charge_sculpture.json`

- JSON-версия пассивной beat-реактивной “световой скульптуры”.
- Открывается напрямую в GUI, без Python-кода.
- Использует два AC-генератора, диодный удвоитель, накопительный bus и три канала индикации с разной инерцией.

## 16. Python-примеры в `examples/`

### `examples/test_dc_basic.py`

- Батарея 9 В, резистор 330 Ом, красный LED.
- Демонстрация минимального Python API.

### `examples/test_ac_filter.py`

- AC-генератор, физический провод, катушка, конденсатор, нагрузка.
- Хороший пример влияния паразитик провода и реактивных элементов.

### `examples/fuse_burn.py`

- Аккумулятор 12 В, предохранитель, лампа накаливания.
- Демонстрирует бросок пускового тока и перегорание предохранителя.

### `examples/beat_charge_sculpture.py`

- Два близких по частоте AC-источника смешиваются через резисторы.
- Далее сигнал проходит через диодный удвоитель и заряжает общий накопительный bus.
- От bus питаются три диодно-емкостных канала с разными порогами и временами удержания.
- Визуально это работает как пассивная “световая скульптура”: быстрый, средний и медленный LED-каналы по-разному реагируют на beat-огибающую.

## 17. Работа через Python API

### 17.1 Минимальный пример

```python
from core import Circuit, PhysiBattery, RealResistor, LED_ImageActive

circuit = Circuit("Простейшая LED-цепь")
circuit.add(PhysiBattery("BAT1", "vcc", "0", nominal_voltage_v=9.0))
circuit.add(RealResistor("R1", "vcc", "n_led", resistance_ohm=330.0))
circuit.add(LED_ImageActive("LED1", "n_led", "0", color="red"))

result = circuit.simulate(duration_s=0.03, dt_s=1.0e-4)
print(result.final_node_voltage("n_led"))
print(result.final_observable("LED1", "brightness"))
```

### 17.2 Что доступно через `core`

Экспортируется:

- `Circuit`, `SimulationResult`;
- все основные классы компонентов;
- `COMPONENT_LIBRARY`, `COMPONENT_TERMINALS`, `create_component`;
- `CircuitProject`, `ProjectSettings`, `ComponentRecord`, `WireRecord`, `MaterialRegionRecord`, `FieldPortRecord`;
- `load_project`, `save_project`;
- `solve_quasi_static_field`, `simulate_fdtd_wave`, `simulate_full_wave_maxwell_2d`, `simulate_full_wave_maxwell_2d_tez`.

### 17.3 Работа с JSON из Python

```python
from core import load_project

project = load_project("examples/maxwell_material_port_demo.json")
circuit = project.to_circuit()
result = circuit.simulate(project.settings.duration_s, project.settings.dt_s)
```

### 17.4 Экспорт поля из Python

```python
from core import solve_quasi_static_field

snapshot = solve_quasi_static_field(circuit, result)
image = snapshot.to_image(layer="electric", scale=4)
image.save("electric_field.png")
```

## 18. Ограничения и реальные границы применимости

Проект полезен как инженерный симулятор-эскиз и исследовательская песочница, но важно понимать его границы.

### Что здесь сделано хорошо

- переходные процессы по пользовательским физическим компонентам;
- объединение схемотехнической, тепловой и приблизительной ЭМ-части;
- удобный JSON-формат проекта;
- GUI, который сразу дает геометрию для полевых расчетов;
- богатая библиотека компонентов для демонстрационных и учебных задач.

### Чего здесь нет

- строгого SPICE-совместимого движка;
- полноценного MNA с дополнительными токовыми неизвестными идеальных источников;
- 3D-решателя полей;
- точного PCB/кабельного EM-моделирования;
- продвинутого менеджмента версий схем;
- отдельного пакета тестов/CI.

### Какие приближения особенно важны

- полупроводники и активные элементы физически мотивированы, но не привязаны к конкретным даташитам;
- проводники имеют эвристическую модель skin/proximity/EM coupling;
- Maxwell/FDTD используют геометрию холста, а не реальную технологическую геометрию;
- у медленных схем полевые решатели показывают быстрый ЭМ-отклик, а не временную динамику уровня секунд.

## 19. Короткое резюме архитектуры

Если свести весь проект к одной цепочке, она выглядит так:

1. GUI или Python формирует проект/схему.
2. `CircuitProject.to_circuit()` создает `Circuit`, где каждый провод становится физическим проводником, а не идеальным short.
3. `Circuit.simulate()` решает переходный процесс по узловым напряжениям, состояниям компонентов, температурам и паразитным связям.
4. Результат сохраняется в `SimulationResult`.
5. GUI анимирует значения по компонентам.
6. Полевые решатели строят карты/анимации на основе геометрии и результата схемотехнического расчета.

Это и есть фактическая структура проекта в текущем состоянии.
