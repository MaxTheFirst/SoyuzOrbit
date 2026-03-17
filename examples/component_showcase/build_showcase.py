from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.project import CircuitProject, ComponentRecord, PinRef, ProjectSettings, WireRecord  # noqa: E402


OUTPUT_DIR = Path(__file__).resolve().parent


@dataclass(slots=True)
class ExampleSpec:
    file_name: str
    title: str
    category: str
    project: CircuitProject
    elements: list[str]
    purpose: list[str]
    plots: list[tuple[str, str]]
    analysis: list[str]
    note: str | None = None


def component(component_id: int, kind: str, name: str, x: float, y: float, **params) -> ComponentRecord:
    return ComponentRecord(component_id=component_id, kind=kind, name=name, x=x, y=y, params=dict(params))


def wire(wire_id: int, a_component_id: int, a_terminal_index: int, b_component_id: int, b_terminal_index: int, **params) -> WireRecord:
    return WireRecord(
        wire_id=wire_id,
        a=PinRef(a_component_id, a_terminal_index),
        b=PinRef(b_component_id, b_terminal_index),
        params=dict(params),
    )


def project(name: str, duration_s: float, dt_s: float, components: list[ComponentRecord], wires: list[WireRecord]) -> CircuitProject:
    return CircuitProject(name=name, settings=ProjectSettings(duration_s=duration_s, dt_s=dt_s), components=components, wires=wires)


def build_battery_resistor_measurement() -> ExampleSpec:
    components = [
        component(1, "Ground", "GND1", 160.0, 320.0),
        component(2, "Battery", "BAT1", 160.0, 120.0, nominal_voltage_v=9.0, internal_resistance_ohm=0.4, capacity_mah=1000.0),
        component(3, "Ammeter", "AM1", 400.0, 120.0, shunt_resistance_ohm=0.01),
        component(4, "Resistor", "R1", 640.0, 120.0, resistance_ohm=330.0),
        component(5, "Voltmeter", "VM_R", 640.0, 280.0, input_resistance_ohm=1.0e7),
    ]
    wires = [
        wire(1, 2, 0, 3, 0),
        wire(2, 3, 1, 4, 0),
        wire(3, 4, 1, 1, 0),
        wire(4, 2, 1, 1, 0),
        wire(5, 5, 0, 4, 0),
        wire(6, 5, 1, 1, 0),
    ]
    return ExampleSpec(
        file_name="01_battery_resistor_measurement.json",
        title="Батарея, резистор и измерители",
        category="База и коммутация",
        project=project("Батарея, резистор и измерители", 0.05, 1.0e-4, components, wires),
        elements=["Battery", "Resistor", "Ammeter", "Voltmeter", "Ground"],
        purpose=[
            "Показывает самый базовый DC-контур с источником, нагрузкой и двумя приборами.",
            "Удобен для первичной проверки закона Ома и того, что амперметр ставится последовательно, а вольтметр параллельно.",
        ],
        plots=[
            ("`--plot-nodes`", "Проверить, как делится напряжение между батареей и нагрузкой."),
            ("`--plot-currents`", "Убедиться, что ток один и тот же во всей последовательной ветви."),
            ("`--plot-power-temperature`", "Посмотреть выделяемую мощность на резисторе и слабый нагрев."),
            ("`--plot-iv-xy`", "Увидеть почти прямую линию `I(U)` для резистора."),
        ],
        analysis=[
            "Если увеличить `resistance_ohm`, ток должен уменьшиться почти пропорционально.",
            "Если занизить внутреннее сопротивление батареи, напряжение на нагрузке станет ближе к идеальным 9 В.",
        ],
    )


def build_switch_bulb() -> ExampleSpec:
    components = [
        component(1, "Ground", "GND1", 160.0, 340.0),
        component(2, "Battery", "BAT1", 160.0, 120.0, nominal_voltage_v=12.0, internal_resistance_ohm=0.12, capacity_mah=1800.0),
        component(3, "Switch", "SW1", 400.0, 120.0, closed=True),
        component(4, "Ammeter", "AM1", 620.0, 120.0, shunt_resistance_ohm=0.01),
        component(5, "Bulb", "LAMP1", 860.0, 120.0, rated_voltage_v=12.0, rated_power_w=5.0),
        component(6, "Voltmeter", "VM_LAMP", 860.0, 300.0, input_resistance_ohm=1.0e7),
    ]
    wires = [
        wire(1, 2, 0, 3, 0),
        wire(2, 3, 1, 4, 0),
        wire(3, 4, 1, 5, 0),
        wire(4, 5, 1, 1, 0),
        wire(5, 2, 1, 1, 0),
        wire(6, 6, 0, 5, 0),
        wire(7, 6, 1, 1, 0),
    ]
    return ExampleSpec(
        file_name="02_switch_bulb.json",
        title="Переключатель и лампа",
        category="База и коммутация",
        project=project("Переключатель и лампа", 0.8, 0.001, components, wires),
        elements=["Battery", "Switch", "Bulb", "Ammeter", "Voltmeter", "Ground"],
        purpose=[
            "Показывает, что обычный переключатель просто открывает или закрывает путь току.",
            "Хорошо демонстрирует, что лампа накаливания не выходит мгновенно на стационарный режим: нить сначала холодная, потом нагревается.",
        ],
        plots=[
            ("`--plot-currents`", "Поймать пусковой ток при включении лампы."),
            ("`--plot-power-temperature`", "Посмотреть, как рост температуры меняет мощность и сопротивление нити."),
            ("`--plot-state`", "Отследить `glow` и сравнить его с током и температурой."),
        ],
        analysis=[
            "При открытом переключателе ток должен быть почти нулевым, а `glow` лампы должен падать к нулю.",
            "В замкнутом состоянии лампа сначала берет больше тока, чем после прогрева.",
        ],
        note="В GUI можно дважды щелкнуть по `SW1`, чтобы до запуска сравнить открытое и закрытое состояние.",
    )


def build_spdt_selector_leds() -> ExampleSpec:
    components = [
        component(1, "Ground", "GND1", 170.0, 360.0),
        component(2, "Battery", "BAT1", 170.0, 120.0, nominal_voltage_v=5.0, internal_resistance_ohm=0.15, capacity_mah=1200.0),
        component(3, "SPDT Switch", "SEL1", 420.0, 120.0, position_b=False),
        component(4, "Resistor", "R_A", 700.0, 60.0, resistance_ohm=220.0),
        component(5, "LED", "LED_A", 920.0, 60.0, color="red", max_forward_current_a=0.02),
        component(6, "Resistor", "R_B", 700.0, 210.0, resistance_ohm=220.0),
        component(7, "LED", "LED_B", 920.0, 210.0, color="green", max_forward_current_a=0.02),
    ]
    wires = [
        wire(1, 2, 0, 3, 0),
        wire(2, 3, 1, 4, 0),
        wire(3, 4, 1, 5, 0),
        wire(4, 5, 1, 1, 0),
        wire(5, 3, 2, 6, 0),
        wire(6, 6, 1, 7, 0),
        wire(7, 7, 1, 1, 0),
        wire(8, 2, 1, 1, 0),
    ]
    return ExampleSpec(
        file_name="03_spdt_selector_leds.json",
        title="Перекидной переключатель и выбор ветви",
        category="База и коммутация",
        project=project("Перекидной переключатель и выбор ветви", 0.03, 1.0e-4, components, wires),
        elements=["Battery", "SPDT Switch", "Resistor", "LED", "Ground"],
        purpose=[
            "Показывает, как перекидной переключатель направляет один и тот же источник либо в верхнюю, либо в нижнюю ветвь.",
            "Наглядный пример маршрутизации тока без сложной логики.",
        ],
        plots=[
            ("`--plot-currents`", "Сравнить токи в верхней и нижней ветвях."),
            ("`--plot-state`", "Проверить, что яркость есть только у одной LED за раз."),
            ("`--plot-nodes`", "Посмотреть, как меняется потенциал на выходе переключателя."),
        ],
        analysis=[
            "В положении `A` должна светиться только `LED_A`, а `LED_B` должна оставаться почти выключенной.",
            "После переключения в положение `B` картина должна зеркально поменяться.",
        ],
        note="В GUI дважды щелкните по `SEL1`, чтобы перевести его между положениями `A` и `B`.",
    )


def build_junction_loaded_divider() -> ExampleSpec:
    components = [
        component(1, "Ground", "GND1", 180.0, 360.0),
        component(2, "Battery", "BAT1", 180.0, 120.0, nominal_voltage_v=10.0, internal_resistance_ohm=0.1, capacity_mah=1200.0),
        component(3, "Resistor", "R_TOP", 430.0, 120.0, resistance_ohm=4700.0),
        component(4, "Junction", "J_MID", 650.0, 120.0),
        component(5, "Resistor", "R_BOTTOM", 650.0, 250.0, resistance_ohm=4700.0),
        component(6, "Resistor", "R_LOAD", 900.0, 120.0, resistance_ohm=10000.0),
        component(7, "Voltmeter", "VM_OUT", 900.0, 280.0, input_resistance_ohm=1.0e7),
    ]
    wires = [
        wire(1, 2, 0, 3, 0),
        wire(2, 3, 1, 4, 0),
        wire(3, 4, 0, 5, 0),
        wire(4, 5, 1, 1, 0),
        wire(5, 4, 0, 6, 0),
        wire(6, 6, 1, 1, 0),
        wire(7, 7, 0, 4, 0),
        wire(8, 7, 1, 1, 0),
        wire(9, 2, 1, 1, 0),
    ]
    return ExampleSpec(
        file_name="04_junction_loaded_divider.json",
        title="Узел-разветвитель и нагруженный делитель",
        category="База и коммутация",
        project=project("Узел-разветвитель и нагруженный делитель", 0.05, 1.0e-4, components, wires),
        elements=["Battery", "Resistor", "Junction", "Voltmeter", "Ground"],
        purpose=[
            "Показывает роль `Junction` как общей точки, к которой можно подключать несколько ветвей.",
            "Демонстрирует, что подключение нагрузки меняет напряжение делителя.",
        ],
        plots=[
            ("`--plot-nodes`", "Смотреть напряжение в средней точке делителя."),
            ("`--plot-currents`", "Сравнить ток через верхний резистор и сумму токов в нижних ветвях."),
            ("`--plot-iv-xy`", "Проверить линейность резистивных ветвей."),
        ],
        analysis=[
            "Без `R_LOAD` делитель дал бы почти ровно половину напряжения; с нагрузкой напряжение середины проседает.",
            "Ток через `R_TOP` должен быть больше, чем через `R_BOTTOM`, потому что часть тока уходит в ветвь `R_LOAD`.",
        ],
    )


def build_rc_charge_discharge() -> ExampleSpec:
    components = [
        component(1, "Ground", "GND1", 160.0, 340.0),
        component(
            2,
            "Pulse Generator",
            "PULSE1",
            160.0,
            120.0,
            high_voltage_v=5.0,
            low_voltage_v=0.0,
            period_s=0.2,
            duty_cycle=0.5,
            pulse_width_s=0.1,
            rise_time_s=0.002,
            fall_time_s=0.002,
            internal_resistance_ohm=1.0,
        ),
        component(3, "Resistor", "R1", 390.0, 120.0, resistance_ohm=2200.0),
        component(4, "Capacitor", "C1", 390.0, 260.0, capacitance_f=2.2e-4, max_voltage_v=10.0),
        component(5, "Voltmeter", "VM_CAP", 620.0, 260.0, input_resistance_ohm=1.0e7),
    ]
    wires = [
        wire(1, 2, 0, 3, 0),
        wire(2, 3, 1, 4, 0),
        wire(3, 4, 1, 1, 0),
        wire(4, 2, 1, 1, 0),
        wire(5, 5, 0, 4, 0),
        wire(6, 5, 1, 1, 0),
    ]
    return ExampleSpec(
        file_name="05_rc_charge_discharge.json",
        title="RC-заряд и разряд",
        category="Накопление энергии",
        project=project("RC-заряд и разряд", 0.8, 0.001, components, wires),
        elements=["Pulse Generator", "Resistor", "Capacitor", "Voltmeter", "Ground"],
        purpose=[
            "Показывает, что напряжение на конденсаторе не прыгает мгновенно, а меняется плавно.",
            "Это базовый пример накопления электрического заряда.",
        ],
        plots=[
            ("`--plot-nodes`", "Смотреть, как выход импульса отличается от напряжения на конденсаторе."),
            ("`--plot-energy-storage`", "Отследить `charge_c` и увидеть накопление заряда."),
            ("`--plot-currents`", "Поймать пики тока в моменты фронтов импульса."),
        ],
        analysis=[
            "Чем больше `R1` или `C1`, тем медленнее должен идти заряд и разряд.",
            "Если `dt` сделать слишком крупным, экспонента станет грубой и потеряет форму.",
        ],
    )


def build_rl_pulse_response() -> ExampleSpec:
    components = [
        component(1, "Ground", "GND1", 170.0, 340.0),
        component(
            2,
            "Pulse Generator",
            "PULSE1",
            170.0,
            120.0,
            high_voltage_v=5.0,
            low_voltage_v=0.0,
            period_s=0.02,
            duty_cycle=0.5,
            pulse_width_s=0.01,
            rise_time_s=2.0e-4,
            fall_time_s=2.0e-4,
            internal_resistance_ohm=0.3,
        ),
        component(3, "Inductor", "L1", 430.0, 120.0, inductance_h=0.02, dc_resistance_ohm=0.6),
        component(4, "Resistor", "R1", 680.0, 120.0, resistance_ohm=10.0),
        component(5, "Ammeter", "AM1", 920.0, 120.0, shunt_resistance_ohm=0.01),
    ]
    wires = [
        wire(1, 2, 0, 3, 0),
        wire(2, 3, 1, 4, 0),
        wire(3, 4, 1, 5, 0),
        wire(4, 5, 1, 1, 0),
        wire(5, 2, 1, 1, 0),
    ]
    return ExampleSpec(
        file_name="06_rl_pulse_response.json",
        title="RL-цепь на импульсах",
        category="Накопление энергии",
        project=project("RL-цепь на импульсах", 0.08, 1.0e-4, components, wires),
        elements=["Pulse Generator", "Inductor", "Resistor", "Ammeter", "Ground"],
        purpose=[
            "Показывает, что ток через катушку не может измениться мгновенно.",
            "Это базовый пример накопления магнитной энергии.",
        ],
        plots=[
            ("`--plot-currents`", "Смотреть плавный разгон и спад тока."),
            ("`--plot-energy-storage`", "Отследить `flux_linkage_wb` у катушки."),
            ("`--plot-nodes`", "Посмотреть напряжения на фронтах импульса."),
        ],
        analysis=[
            "Чем больше `inductance_h`, тем медленнее будет нарастать ток.",
            "Форма тока должна быть более сглаженной, чем форма входного импульса.",
        ],
    )


def build_diode_half_wave_rectifier() -> ExampleSpec:
    components = [
        component(1, "Ground", "GND1", 180.0, 340.0),
        component(2, "AC Generator", "AC1", 180.0, 120.0, amplitude_v=8.0, frequency_hz=50.0, internal_resistance_ohm=0.4),
        component(3, "Diode", "D1", 420.0, 120.0),
        component(4, "Resistor", "R_LOAD", 670.0, 120.0, resistance_ohm=220.0),
        component(5, "Voltmeter", "VM_OUT", 670.0, 280.0, input_resistance_ohm=1.0e7),
    ]
    wires = [
        wire(1, 2, 0, 3, 0),
        wire(2, 3, 1, 4, 0),
        wire(3, 4, 1, 1, 0),
        wire(4, 2, 1, 1, 0),
        wire(5, 5, 0, 4, 0),
        wire(6, 5, 1, 1, 0),
    ]
    return ExampleSpec(
        file_name="07_diode_half_wave_rectifier.json",
        title="Диодный полуволновой выпрямитель",
        category="Нелинейные и световые элементы",
        project=project("Диодный полуволновой выпрямитель", 0.12, 2.0e-4, components, wires),
        elements=["AC Generator", "Diode", "Resistor", "Voltmeter", "Ground"],
        purpose=[
            "Показывает, что диод пропускает ток главным образом в одном направлении.",
            "Это простейший способ превратить переменное напряжение в пульсирующее постоянное.",
        ],
        plots=[
            ("`--plot-nodes`", "Сравнить входную синусоиду и выпрямленный выход."),
            ("`--plot-currents`", "Увидеть, что ток через диод идет только на положительной полуволне."),
            ("`--plot-iv-xy`", "Посмотреть нелинейную кривую `I(U)` диода."),
        ],
        analysis=[
            "На отрицательной полуволне ток через `D1` должен почти исчезать.",
            "На положительной полуволне выход должен быть ниже входа на величину прямого падения диода.",
        ],
    )


def build_led_indicator() -> ExampleSpec:
    components = [
        component(1, "Ground", "GND1", 170.0, 320.0),
        component(2, "Battery", "BAT1", 170.0, 120.0, nominal_voltage_v=5.0, internal_resistance_ohm=0.15, capacity_mah=800.0),
        component(3, "Ammeter", "AM1", 410.0, 120.0, shunt_resistance_ohm=0.01),
        component(4, "Resistor", "R1", 650.0, 120.0, resistance_ohm=180.0),
        component(5, "LED", "LED1", 890.0, 120.0, color="red", max_forward_current_a=0.02),
    ]
    wires = [
        wire(1, 2, 0, 3, 0),
        wire(2, 3, 1, 4, 0),
        wire(3, 4, 1, 5, 0),
        wire(4, 5, 1, 1, 0),
        wire(5, 2, 1, 1, 0),
    ]
    return ExampleSpec(
        file_name="08_led_indicator.json",
        title="Светодиодный индикатор",
        category="Нелинейные и световые элементы",
        project=project("Светодиодный индикатор", 0.03, 1.0e-4, components, wires),
        elements=["Battery", "Ammeter", "Resistor", "LED", "Ground"],
        purpose=[
            "Показывает, зачем светодиоду нужен токоограничивающий резистор.",
            "Демонстрирует связь между током через LED и ее яркостью.",
        ],
        plots=[
            ("`--plot-currents`", "Отследить рабочий ток светодиода."),
            ("`--plot-state`", "Смотреть `brightness` и возможную деградацию."),
            ("`--plot-iv-xy`", "Увидеть пороговую нелинейность `I(U)` светодиода."),
        ],
        analysis=[
            "Если сильно уменьшить `R1`, яркость вырастет, но возрастет и риск перегрузки `LED1`.",
            "Если напряжение источника ниже прямого падения LED, ток и яркость станут малыми.",
        ],
    )


def build_thermistor_self_heating_divider() -> ExampleSpec:
    components = [
        component(1, "Ground", "GND1", 180.0, 360.0),
        component(2, "Battery", "BAT1", 180.0, 120.0, nominal_voltage_v=12.0, internal_resistance_ohm=0.1, capacity_mah=1500.0),
        component(3, "Resistor", "R_FIXED", 430.0, 120.0, resistance_ohm=100.0),
        component(4, "Junction", "J_MID", 650.0, 120.0),
        component(5, "Thermistor", "TH1", 650.0, 260.0, resistance_at_25c_ohm=100.0, beta_k=3950.0),
        component(6, "Voltmeter", "VM_OUT", 900.0, 260.0, input_resistance_ohm=1.0e7),
    ]
    wires = [
        wire(1, 2, 0, 3, 0),
        wire(2, 3, 1, 4, 0),
        wire(3, 4, 0, 5, 0),
        wire(4, 5, 1, 1, 0),
        wire(5, 2, 1, 1, 0),
        wire(6, 6, 0, 4, 0),
        wire(7, 6, 1, 1, 0),
    ]
    return ExampleSpec(
        file_name="09_thermistor_self_heating_divider.json",
        title="Термистор с самонагревом",
        category="Нелинейные и световые элементы",
        project=project("Термистор с самонагревом", 1.5, 0.001, components, wires),
        elements=["Battery", "Resistor", "Thermistor", "Junction", "Voltmeter", "Ground"],
        purpose=[
            "Показывает, что сопротивление NTC-термистора зависит от температуры.",
            "Демонстрирует самонагрев: ток греет термистор, а нагрев меняет его сопротивление.",
        ],
        plots=[
            ("`--plot-nodes`", "Следить за изменением выходного напряжения делителя."),
            ("`--plot-power-temperature`", "Посмотреть рост температуры термистора и изменение мощности."),
            ("`--plot-currents`", "Отследить ток, который запускает самонагрев."),
        ],
        analysis=[
            "Для NTC при нагреве сопротивление падает, поэтому выходное напряжение на средней точке тоже меняется.",
            "Если сделать батарею слабее или поднять `R_FIXED`, самонагрев станет заметно меньше.",
        ],
    )


def build_photoresistor_divider(illumination_lux: float, file_name: str, title: str) -> ExampleSpec:
    components = [
        component(1, "Ground", "GND1", 180.0, 360.0),
        component(2, "Battery", "BAT1", 180.0, 120.0, nominal_voltage_v=5.0, internal_resistance_ohm=0.1, capacity_mah=1200.0),
        component(3, "Resistor", "R_FIXED", 430.0, 120.0, resistance_ohm=10000.0),
        component(4, "Junction", "J_MID", 650.0, 120.0),
        component(
            5,
            "Photoresistor",
            "LDR1",
            650.0,
            260.0,
            dark_resistance_ohm=50000.0,
            light_resistance_ohm=800.0,
            illumination_lux=illumination_lux,
            lux_reference=100.0,
            gamma=0.78,
        ),
        component(6, "Voltmeter", "VM_OUT", 900.0, 260.0, input_resistance_ohm=1.0e7),
    ]
    wires = [
        wire(1, 2, 0, 3, 0),
        wire(2, 3, 1, 4, 0),
        wire(3, 4, 0, 5, 0),
        wire(4, 5, 1, 1, 0),
        wire(5, 2, 1, 1, 0),
        wire(6, 6, 0, 4, 0),
        wire(7, 6, 1, 1, 0),
    ]
    return ExampleSpec(
        file_name=file_name,
        title=title,
        category="Нелинейные и световые элементы",
        project=project(title, 0.1, 5.0e-4, components, wires),
        elements=["Battery", "Resistor", "Photoresistor", "Junction", "Voltmeter", "Ground"],
        purpose=[
            "Показывает, что сопротивление фоторезистора зависит от освещенности.",
            "Этот пример лучше всего анализировать в паре с противоположным по освещенности вариантом.",
        ],
        plots=[
            ("`--plot-nodes`", "Сравнить выходное напряжение делителя при разной освещенности."),
            ("`--plot-currents`", "Увидеть, как меняется ток через ветвь с LDR."),
            ("`--plot-power-temperature`", "Проверить, что в этом примере тепловой эффект почти вторичен."),
        ],
        analysis=[
            "В ярком варианте сопротивление `LDR1` меньше, поэтому средняя точка должна сильнее проседать к земле.",
            "В темном варианте ток меньше, а напряжение на выходе делителя должно быть заметно выше.",
        ],
        note="Сам по себе свет в ходе одной симуляции не меняется: для анализа нужно сравнивать два разных файла или вручную менять `illumination_lux`.",
    )


def build_varistor_surge_clamp() -> ExampleSpec:
    components = [
        component(1, "Ground", "GND1", 180.0, 380.0),
        component(
            2,
            "Pulse Generator",
            "PULSE1",
            180.0,
            120.0,
            high_voltage_v=40.0,
            low_voltage_v=0.0,
            period_s=0.02,
            duty_cycle=0.35,
            pulse_width_s=0.007,
            rise_time_s=5.0e-4,
            fall_time_s=5.0e-4,
            internal_resistance_ohm=0.3,
        ),
        component(3, "Resistor", "R_SER", 430.0, 120.0, resistance_ohm=47.0),
        component(4, "Junction", "J_PROT", 650.0, 120.0),
        component(5, "Varistor", "VAR1", 650.0, 270.0, clamp_voltage_v=15.0, dynamic_resistance_ohm=1.2, leakage_current_a=2.0e-6),
        component(6, "Resistor", "R_LOAD", 900.0, 120.0, resistance_ohm=680.0),
        component(7, "Voltmeter", "VM_PROT", 900.0, 300.0, input_resistance_ohm=1.0e7),
    ]
    wires = [
        wire(1, 2, 0, 3, 0),
        wire(2, 3, 1, 4, 0),
        wire(3, 4, 0, 5, 0),
        wire(4, 5, 1, 1, 0),
        wire(5, 4, 0, 6, 0),
        wire(6, 6, 1, 1, 0),
        wire(7, 7, 0, 4, 0),
        wire(8, 7, 1, 1, 0),
        wire(9, 2, 1, 1, 0),
    ]
    return ExampleSpec(
        file_name="12_varistor_surge_clamp.json",
        title="Варистор как ограничитель перенапряжения",
        category="Нелинейные и световые элементы",
        project=project("Варистор как ограничитель перенапряжения", 0.06, 1.0e-4, components, wires),
        elements=["Pulse Generator", "Resistor", "Junction", "Varistor", "Voltmeter", "Ground"],
        purpose=[
            "Показывает, что варистор почти не мешает до порога и резко начинает проводить после него.",
            "Это базовая схема защиты чувствительного узла от импульсного перенапряжения.",
        ],
        plots=[
            ("`--plot-nodes`", "Следить за защищаемым узлом и видеть, как он перестает расти пропорционально входу."),
            ("`--plot-currents`", "Посмотреть, как ток уходит в `VAR1` во время всплеска."),
            ("`--plot-iv-xy`", "Увидеть резкую нелинейность `I(U)` варистора."),
            ("`--plot-power-temperature`", "Оценить, как сильно варистор нагревается на импульсах."),
        ],
        analysis=[
            "Пока напряжение ниже `clamp_voltage_v`, ток варистора должен быть очень малым.",
            "После входа в режим ограничения рост напряжения на защищаемом узле сильно замедляется.",
        ],
    )


def build_fuse_overload_trip() -> ExampleSpec:
    components = [
        component(1, "Ground", "GND1", 170.0, 340.0),
        component(2, "Battery", "BAT1", 170.0, 120.0, nominal_voltage_v=12.0, internal_resistance_ohm=0.05, capacity_mah=2000.0),
        component(3, "Fuse", "F1", 410.0, 120.0, current_rating_a=0.35, i2t_trip=0.03, cold_resistance_ohm=0.05),
        component(4, "Ammeter", "AM1", 650.0, 120.0, shunt_resistance_ohm=0.01),
        component(5, "Resistor", "R_LOAD", 890.0, 120.0, resistance_ohm=3.0),
    ]
    wires = [
        wire(1, 2, 0, 3, 0),
        wire(2, 3, 1, 4, 0),
        wire(3, 4, 1, 5, 0),
        wire(4, 5, 1, 1, 0),
        wire(5, 2, 1, 1, 0),
    ]
    return ExampleSpec(
        file_name="13_fuse_overload_trip.json",
        title="Перегорание предохранителя",
        category="Защита, тепло и деградация",
        project=project("Перегорание предохранителя", 0.2, 1.0e-4, components, wires),
        elements=["Battery", "Fuse", "Ammeter", "Resistor", "Ground"],
        purpose=[
            "Показывает, что предохранитель реагирует не только на мгновенный ток, но и на накопленную перегрузку.",
            "Удобен для объяснения модели `I²t` и перехода от нормального режима к обрыву.",
        ],
        plots=[
            ("`--plot-currents`", "Смотреть, как ток резко падает после перегорания."),
            ("`--plot-power-temperature`", "Отследить нагрев плавкой вставки до отказа."),
            ("`--plot-state`", "Смотреть `stress_i2t` и `blown`."),
        ],
        analysis=[
            "До срабатывания ток должен быть большим, а после срабатывания почти исчезнуть.",
            "Если увеличить `current_rating_a` или `i2t_trip`, предохранитель будет держаться дольше.",
        ],
    )


def build_bulb_warmup() -> ExampleSpec:
    components = [
        component(1, "Ground", "GND1", 170.0, 340.0),
        component(2, "Battery", "BAT1", 170.0, 120.0, nominal_voltage_v=12.0, internal_resistance_ohm=0.08, capacity_mah=1800.0),
        component(3, "Ammeter", "AM1", 410.0, 120.0, shunt_resistance_ohm=0.01),
        component(4, "Bulb", "LAMP1", 650.0, 120.0, rated_voltage_v=12.0, rated_power_w=21.0),
        component(5, "Voltmeter", "VM_LAMP", 650.0, 290.0, input_resistance_ohm=1.0e7),
    ]
    wires = [
        wire(1, 2, 0, 3, 0),
        wire(2, 3, 1, 4, 0),
        wire(3, 4, 1, 1, 0),
        wire(4, 2, 1, 1, 0),
        wire(5, 5, 0, 4, 0),
        wire(6, 5, 1, 1, 0),
    ]
    return ExampleSpec(
        file_name="14_bulb_warmup.json",
        title="Прогрев лампы накаливания",
        category="Защита, тепло и деградация",
        project=project("Прогрев лампы накаливания", 0.6, 0.001, components, wires),
        elements=["Battery", "Ammeter", "Bulb", "Voltmeter", "Ground"],
        purpose=[
            "Показывает, что сопротивление нити лампы зависит от температуры.",
            "Это хороший пример связанной электротепловой модели даже без нелинейных полупроводников.",
        ],
        plots=[
            ("`--plot-currents`", "Увидеть большой стартовый ток и его спад по мере прогрева."),
            ("`--plot-power-temperature`", "Сравнить нагрев и выход на стационарный режим."),
            ("`--plot-state`", "Отследить `glow` как визуальный индикатор накала."),
        ],
        analysis=[
            "На старте нить холодная, поэтому ток должен быть заметно выше, чем через некоторое время.",
            "Если уменьшить напряжение батареи, максимальный `glow` тоже должен уменьшиться.",
        ],
    )


def build_mosfet_led_switch() -> ExampleSpec:
    components = [
        component(1, "Ground", "GND1", 170.0, 380.0),
        component(2, "Battery", "BAT1", 170.0, 120.0, nominal_voltage_v=9.0, internal_resistance_ohm=0.1, capacity_mah=1200.0),
        component(3, "Resistor", "R_LOAD", 420.0, 120.0, resistance_ohm=330.0),
        component(4, "LED", "LED1", 660.0, 120.0, color="blue", max_forward_current_a=0.02),
        component(5, "MOSFET", "M1", 900.0, 120.0, threshold_v=3.0, rds_on_ohm=0.08),
        component(
            6,
            "Pulse Generator",
            "GATE",
            900.0,
            300.0,
            high_voltage_v=8.0,
            low_voltage_v=0.0,
            period_s=0.01,
            duty_cycle=0.5,
            pulse_width_s=0.005,
            rise_time_s=1.0e-4,
            fall_time_s=1.0e-4,
            internal_resistance_ohm=0.2,
        ),
    ]
    wires = [
        wire(1, 2, 0, 3, 0),
        wire(2, 3, 1, 4, 0),
        wire(3, 4, 1, 5, 0),
        wire(4, 5, 2, 1, 0),
        wire(5, 2, 1, 1, 0),
        wire(6, 6, 0, 5, 1),
        wire(7, 6, 1, 1, 0),
    ]
    return ExampleSpec(
        file_name="15_mosfet_led_switch.json",
        title="MOSFET как электронный ключ",
        category="Управление и специальные модели",
        project=project("MOSFET как электронный ключ", 0.04, 5.0e-5, components, wires),
        elements=["Battery", "Resistor", "LED", "MOSFET", "Pulse Generator", "Ground"],
        purpose=[
            "Показывает, как сигнал на затворе управляет током в силовой цепи.",
            "Это базовый пример полупроводникового ключа без механического контакта.",
        ],
        plots=[
            ("`--plot-currents`", "Смотреть ток стока, затвора и нагрузки."),
            ("`--plot-energy-storage`", "Отследить `inversion_charge_c` у MOSFET."),
            ("`--plot-state`", "Смотреть яркость LED как индикатор открытия ключа."),
            ("`--plot-power-temperature`", "Оценить потери на MOSFET."),
        ],
        analysis=[
            "Когда `GATE` выше порога `threshold_v`, LED должна загораться, а ток стока возрастать.",
            "Если поднять `threshold_v`, ключ станет открываться хуже или перестанет открываться при том же импульсе затвора.",
        ],
    )


def build_opamp_voltage_follower() -> ExampleSpec:
    components = [
        component(1, "Ground", "GND1", 170.0, 380.0),
        component(
            2,
            "Pulse Generator",
            "VIN",
            170.0,
            120.0,
            high_voltage_v=2.5,
            low_voltage_v=0.5,
            period_s=0.4,
            duty_cycle=0.5,
            pulse_width_s=0.2,
            rise_time_s=0.05,
            fall_time_s=0.05,
            internal_resistance_ohm=1.0,
        ),
        component(3, "OpAmp", "OA1", 470.0, 150.0, dominant_pole_hz=20.0, output_current_limit_a=0.05),
        component(4, "Resistor", "R_LOAD", 780.0, 150.0, resistance_ohm=1000.0),
        component(5, "Voltmeter", "VM_IN", 470.0, 320.0, input_resistance_ohm=1.0e7),
        component(6, "Voltmeter", "VM_OUT", 780.0, 320.0, input_resistance_ohm=1.0e7),
    ]
    wires = [
        wire(1, 2, 0, 3, 0),
        wire(2, 2, 1, 1, 0),
        wire(3, 3, 2, 3, 1),
        wire(4, 3, 2, 4, 0),
        wire(5, 4, 1, 1, 0),
        wire(6, 5, 0, 3, 0),
        wire(7, 5, 1, 1, 0),
        wire(8, 6, 0, 3, 2),
        wire(9, 6, 1, 1, 0),
    ]
    return ExampleSpec(
        file_name="16_opamp_voltage_follower.json",
        title="Операционный усилитель как повторитель",
        category="Управление и специальные модели",
        project=project("Операционный усилитель как повторитель", 1.0, 0.001, components, wires),
        elements=["Pulse Generator", "OpAmp", "Resistor", "Voltmeter", "Ground"],
        purpose=[
            "Показывает отрицательную обратную связь: выход стремится повторять вход.",
            "Это самый понятный способ показать роль `OpAmp` без сложных формул усиления.",
        ],
        plots=[
            ("`--plot-nodes`", "Сравнить входной сигнал и выход повторителя."),
            ("`--plot-currents`", "Посмотреть выходной ток усилителя на нагрузку."),
            ("`--plot-power-temperature`", "Оценить потери и нагрев `OA1`."),
        ],
        analysis=[
            "Выход `OA1` должен повторять `VIN` с небольшой динамической задержкой.",
            "Если сделать нагрузку слишком тяжелой или снизить `output_current_limit_a`, усилитель начнет ограничиваться.",
        ],
    )


def build_wire_voltage_drop() -> ExampleSpec:
    components = [
        component(1, "Ground", "GND1", 170.0, 360.0),
        component(2, "Battery", "BAT1", 170.0, 120.0, nominal_voltage_v=12.0, internal_resistance_ohm=0.08, capacity_mah=1500.0),
        component(3, "Ammeter", "AM1", 430.0, 120.0, shunt_resistance_ohm=0.01),
        component(4, "Resistor", "R_LOAD", 920.0, 120.0, resistance_ohm=20.0),
        component(5, "Voltmeter", "VM_SRC", 170.0, 280.0, input_resistance_ohm=1.0e7),
        component(6, "Voltmeter", "VM_LOAD", 920.0, 280.0, input_resistance_ohm=1.0e7),
    ]
    wires = [
        wire(1, 2, 0, 3, 0),
        wire(
            2,
            3,
            1,
            4,
            0,
            auto_length_from_path=False,
            length_m=20.0,
            area_mm2=0.05,
            material="aluminum",
            contact_resistance_ohm=0.1,
        ),
        wire(3, 4, 1, 1, 0),
        wire(4, 2, 1, 1, 0),
        wire(5, 5, 0, 2, 0),
        wire(6, 5, 1, 1, 0),
        wire(7, 6, 0, 4, 0),
        wire(8, 6, 1, 1, 0),
    ]
    return ExampleSpec(
        file_name="17_wire_voltage_drop.json",
        title="Падение напряжения на длинном проводе",
        category="Управление и специальные модели",
        project=project("Падение напряжения на длинном проводе", 0.2, 5.0e-4, components, wires),
        elements=["Battery", "Ammeter", "Resistor", "Voltmeter", "Wire", "Ground"],
        purpose=[
            "Показывает, что соединительный провод в этой модели не идеален и сам может вносить сопротивление и нагрев.",
            "Это полезно для объяснения, почему на удаленной нагрузке напряжение ниже, чем у источника.",
        ],
        plots=[
            ("`--plot-nodes`", "Сравнить напряжение у источника и на нагрузке."),
            ("`--plot-currents`", "Убедиться, что ток течет и через провод как через отдельный элемент модели."),
            ("`--plot-power-temperature`", "Отследить потери и нагрев длинного провода."),
            ("`--plot-iv-xy`", "Посмотреть почти линейную характеристику провода."),
        ],
        analysis=[
            "Если уменьшить `area_mm2` или увеличить `length_m`, напряжение на `VM_LOAD` должно стать ниже.",
            "Сильно тонкий длинный провод начинает вести себя как заметный резистор, а не как идеальное соединение.",
        ],
    )


def build_examples() -> list[ExampleSpec]:
    return [
        build_battery_resistor_measurement(),
        build_switch_bulb(),
        build_spdt_selector_leds(),
        build_junction_loaded_divider(),
        build_rc_charge_discharge(),
        build_rl_pulse_response(),
        build_diode_half_wave_rectifier(),
        build_led_indicator(),
        build_thermistor_self_heating_divider(),
        build_photoresistor_divider(illumination_lux=500.0, file_name="10_photoresistor_bright_divider.json", title="Фоторезистор при ярком свете"),
        build_photoresistor_divider(illumination_lux=5.0, file_name="11_photoresistor_dark_divider.json", title="Фоторезистор в темноте"),
        build_varistor_surge_clamp(),
        build_fuse_overload_trip(),
        build_bulb_warmup(),
        build_mosfet_led_switch(),
        build_opamp_voltage_follower(),
        build_wire_voltage_drop(),
    ]


def render_readme(specs: list[ExampleSpec]) -> str:
    lines = [
        "# Демонстрационные схемы по компонентам",
        "",
        "Каталог содержит простые JSON-проекты, на которых можно быстро проверить работу почти всех элементов библиотеки и показать их на защите или лабораторной демонстрации.",
        "",
        "## Как запускать",
        "",
        "Примеры команд:",
        "",
        "```bash",
        "python3 run_sim.py examples/component_showcase/01_battery_resistor_measurement.json --plot-nodes --plot-currents --plot-iv-xy",
        "python3 run_sim.py examples/component_showcase/05_rc_charge_discharge.json --plot-nodes --plot-energy-storage",
        "python3 run_sim.py examples/component_showcase/15_mosfet_led_switch.json --plot-currents --plot-energy-storage --plot-state",
        "```",
        "",
        "Основные панели графиков, которые здесь чаще всего полезны:",
        "",
        "- `--plot-nodes`: напряжения по узлам и выходам.",
        "- `--plot-currents`: токи по компонентам и ветвям.",
        "- `--plot-power-temperature`: совместный график мощности и температуры.",
        "- `--plot-energy-storage`: заряд конденсаторов, инверсный заряд MOSFET, потокосцепление катушек.",
        "- `--plot-iv-xy`: нелинейные кривые `I(U)` для диодов, LED, варистора и других элементов.",
        "- `--plot-state`: яркость LED, `glow` лампы, `blown` предохранителя и другие флаги состояния.",
        "",
    ]
    categories: list[str] = []
    for spec in specs:
        if spec.category not in categories:
            categories.append(spec.category)
    for category in categories:
        lines.append(f"## {category}")
        lines.append("")
        for spec in specs:
            if spec.category != category:
                continue
            lines.append(f"### [{spec.file_name}]({spec.file_name})")
            lines.append("")
            lines.append(f"**Схема:** {spec.title}")
            lines.append("")
            lines.append(f"**Элементы:** {', '.join(spec.elements)}")
            lines.append("")
            lines.append("**Что показывает:**")
            for item in spec.purpose:
                lines.append(f"- {item}")
            lines.append("")
            lines.append("**Какие графики смотреть:**")
            for flag, explanation in spec.plots:
                lines.append(f"- {flag}: {explanation}")
            lines.append("")
            lines.append("**Что анализировать:**")
            for item in spec.analysis:
                lines.append(f"- {item}")
            if spec.note:
                lines.append("")
                lines.append(f"**Примечание:** {spec.note}")
            lines.append("")
        lines.append("")
    lines.extend(
        [
            "## Покрытие элементов",
            "",
            "Эти схемы суммарно покрывают:",
            "",
            "- Источники: `Battery`, `AC Generator`, `Pulse Generator`.",
            "- Пассивные элементы: `Resistor`, `Capacitor`, `Inductor`.",
            "- Нелинейные и световые элементы: `Diode`, `LED`, `Varistor`, `Thermistor`, `Photoresistor`, `Bulb`.",
            "- Управляющие элементы: `Switch`, `SPDT Switch`, `MOSFET`, `OpAmp`.",
            "- Измерители и инфраструктуру: `Ammeter`, `Voltmeter`, `Ground`, `Junction`, физические `Wire`.",
            "",
            "Если нужно быстро показать базовые возможности проекта, обычно достаточно четырех файлов:",
            "",
            "- `01_battery_resistor_measurement.json`",
            "- `05_rc_charge_discharge.json`",
            "- `07_diode_half_wave_rectifier.json`",
            "- `15_mosfet_led_switch.json`",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    specs = build_examples()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for spec in specs:
        spec.project.save(OUTPUT_DIR / spec.file_name)
    (OUTPUT_DIR / "README.md").write_text(render_readme(specs), encoding="utf-8")
    print(f"Generated {len(specs)} showcase examples in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
