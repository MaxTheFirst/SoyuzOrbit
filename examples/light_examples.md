# Легкие демонстрационные схемы

Все примеры ниже собраны только из сравнительно легких компонентов:

- `Battery` / `AC Generator` / `Pulse Generator`
- `Resistor`
- `Capacitor`
- `Inductor`
- `Diode`
- `LED`
- `Ammeter` / `Voltmeter`
- `Ground`

Тяжелые элементы вроде `MOSFET`, `OpAmp`, полевых портов и сложных материаловых сцен здесь не используются.

## Что добавлено

### `rc_charge_discharge.json`

Что показывает:

- классический заряд и разряд конденсатора;
- задержку по сравнению с входным импульсом;
- экспоненциальную форму роста и спада напряжения на `C1`.

Что смотреть:

- `VM_CAP.reading_v`
- `C1.charge_c`

### `half_wave_peak_detector.json`

Что показывает:

- полуволновое выпрямление;
- накопление на конденсаторе;
- сглаживание пульсаций на нагрузке.

Что смотреть:

- `VM_OUT.reading_v`
- `D1.current_a`
- `C1.charge_c`

### `rl_pulse_ramp.json`

Что показывает:

- ток через катушку не может подскочить мгновенно;
- на импульсах виден плавный разгон и спад тока;
- напряжение на резисторе отражает ток через ветвь.

Что смотреть:

- `AM1.reading_a`
- `VM_R.reading_v`
- `L1.flux_linkage_wb`

### `led_afterglow_hold.json`

Что показывает:

- диод заряжает конденсатор импульсом;
- после окончания импульса LED еще светится;
- видно, как RC-цепочка хранит энергию и медленно ее отдает.

Что смотреть:

- `LED1.brightness`
- `VM_CAP.reading_v`
- `C1.charge_c`

## Как запускать

Примеры:

```bash
python3 run_sim.py examples/rc_charge_discharge.json --plot-all
python3 run_sim.py examples/half_wave_peak_detector.json --plot-all
python3 run_sim.py examples/rl_pulse_ramp.json --plot-all
python3 run_sim.py examples/led_afterglow_hold.json --plot-all
```

Если среда без окна:

```bash
MPLBACKEND=Agg MPLCONFIGDIR=/tmp/mpl XDG_CACHE_HOME=/tmp/.cache python3 run_sim.py examples/rc_charge_discharge.json --plot-all --save-plot /tmp/rc_demo.png
```
