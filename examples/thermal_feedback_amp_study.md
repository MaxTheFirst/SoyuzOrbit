# Усилитель С Лампой В Обратной Связи: С Прогревом И Без

Это уже не пассивный limiter, а именно усилительный каскад:

- `AC Generator` подает богатый по гармоникам входной сигнал;
- `OpAmp` работает как неинвертирующий усилитель;
- `BULB_FB` стоит в цепи отрицательной обратной связи;
- `R_G` задает опорное плечо к земле;
- `R_LOAD` нагружает выход;
- `OUT_MON` снимает итоговую форму сигнала.

Идея кейса такая:

- у холодной лампы сопротивление обратной связи меньше;
- по мере нагрева `BULB_FB.resistance_ohm` растет;
- замкнутый коэффициент усиления `OA1` растет вместе с прогревом;
- поздние участки сигнала становятся заметно сильнее и ближе к ограничению, чем в frozen-варианте.

## Файлы

- `examples/thermal_feedback_amp.json`
- `examples/thermal_feedback_amp_frozen.json`

Во втором проекте используется тот же самый каскад, но у лампы задан JSON-флаг:

```json
"freeze_temperature": true
```

Это новый общий параметр компонента. Его можно задавать прямо в JSON, без отдельного Python-класса.

## Новые JSON Thermal Overrides

Для активных компонентов теперь можно задавать в `params` не только аргументы конструктора, но и post-init thermal overrides:

- `freeze_temperature`
- `heat_capacity_j_per_k`
- `thermal_resistance_k_per_w`
- `contact_thermal_resistance_k_per_w`
- `thermal_case_fraction`
- `thermal_junction_fraction`

Это сделано специально, чтобы можно было собирать честные пары `thermal / frozen` и быстро настраивать тепловую динамику прямо в JSON-проектах.

## Как Запускать

Без графиков:

```bash
./.venv/bin/python run_sim.py examples/thermal_feedback_amp.json
./.venv/bin/python run_sim.py examples/thermal_feedback_amp_frozen.json
```

Если хотите сравнить узлы, состояния и нагрев:

```bash
./.venv/bin/python run_sim.py examples/thermal_feedback_amp.json --plot-nodes --plot-state --plot-power-temperature
./.venv/bin/python run_sim.py examples/thermal_feedback_amp_frozen.json --plot-nodes --plot-state --plot-power-temperature
```

Для headless-режима удобнее так:

```bash
HOME=/tmp/soyuz_home \
XDG_CACHE_HOME=/tmp/soyuz_cache \
MPLCONFIGDIR=/tmp/mplconfig \
MPLBACKEND=Agg \
./.venv/bin/python run_sim.py examples/thermal_feedback_amp.json --plot-nodes --plot-state --plot-power-temperature --save-plot /tmp/thermal-feedback.png
```

## Что Смотреть

- `BULB_FB.temperature_c`
- `BULB_FB.resistance_ohm`
- `OA1.output_current_a`
- `OUT_MON.captured_v`
- напряжение выходного узла на `--plot-nodes`

Главное сравнение:

- в thermal-проекте сопротивление `BULB_FB` должно заметно расти во времени;
- в frozen-проекте сопротивление лампы должно оставаться постоянным;
- из-за этого late-участки выходного сигнала в thermal-версии будут выше и ближе к ограничению, чем в frozen-версии.

## Честная Оговорка

Это не вакуумная лампа и не `tube amplifier` в строгом смысле.

Здесь используется:

- `OpAmp` как усилительный элемент;
- `Bulb` как термозависимый элемент обратной связи.

То есть это именно **усилитель с учетом прогрева в цепи ООС**, а не triode/pentode-модель.
