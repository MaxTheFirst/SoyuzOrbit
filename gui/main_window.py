from __future__ import annotations

from pathlib import Path
from typing import Any

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core import (
    COMPONENT_TERMINALS,
    SUPPORTED_AUDIO_EXPORT_EXTENSIONS,
    audio_buffer_from_simulation_result,
    is_supported_audio_export_path,
    load_project,
    save_audio_file,
)
from core.field_solver import simulate_fdtd_wave, simulate_full_wave_maxwell_2d, solve_quasi_static_field

from .canvas import CircuitScene, CircuitView, ComponentItem, FieldPortItem, MaterialRegionItem, WireItem
from .components_visual import build_qicon, default_params, default_visual_state, template_for
from .field_dialog import FieldPreviewDialog
from .result_plot_dialog import ResultPlotDialog

HIDDEN_USER_PARAMS = {"chemistry"}


PARAMETER_LABELS = {
    "nominal_voltage_v": "Номинальное напряжение, В",
    "capacity_mah": "Емкость, мАч",
    "chemistry": "Химия",
    "internal_resistance_ohm": "Внутреннее сопротивление, Ом",
    "amplitude_v": "Амплитуда, В",
    "peak_voltage_v": "Пик аудиоисточника, В",
    "high_voltage_v": "Высокий уровень, В",
    "low_voltage_v": "Низкий уровень, В",
    "file_path": "Путь к аудиофайлу",
    "channel": "Канал аудио",
    "normalize": "Нормализовать",
    "loop": "Повторять по кругу",
    "hold_last_value": "Держать последний уровень",
    "target_sample_rate_hz": "Частота чтения, Гц",
    "start_time_s": "Старт воспроизведения, с",
    "dc_offset_v": "Постоянное смещение, В",
    "output_gain": "Коэф. усиления выхода",
    "dc_block": "Убирать DC-смещение",
    "frequency_hz": "Частота, Гц",
    "phase_rad": "Фаза, рад",
    "rotation_deg": "Поворот, °",
    "period_s": "Период, с",
    "pulse_width_s": "Длительность импульса, с",
    "duty_cycle": "Скважность",
    "rise_time_s": "Время фронта, с",
    "fall_time_s": "Время спада, с",
    "phase_noise_rad": "Фазовый шум, рад",
    "frequency_error": "Ошибка частоты",
    "harmonic_2_ratio": "2-я гармоника",
    "harmonic_3_ratio": "3-я гармоника",
    "resistance_ohm": "Сопротивление, Ом",
    "resistance_at_25c_ohm": "Сопротивление при 25°C, Ом",
    "beta_k": "Beta, K",
    "series_resistance_ohm": "Последоват. сопротивление, Ом",
    "tolerance": "Допуск",
    "tolerance_bias": "Смещение допуска",
    "temperature_coefficient": "ТКС",
    "capacitance_f": "Емкость, Ф",
    "esr_ohm": "ESR, Ом",
    "esl_h": "ESL, Гн",
    "leak_resistance_ohm": "Сопротивление утечки, Ом",
    "max_voltage_v": "Макс. напряжение, В",
    "inductance_h": "Индуктивность, Гн",
    "dc_resistance_ohm": "Сопротивление провода, Ом",
    "saturation_current_a": "Ток насыщения, А",
    "relative_permeability": "Отн. проницаемость",
    "interwinding_capacitance_f": "Межвитковая емкость, Ф",
    "length_m": "Длина, м",
    "width_px": "Ширина, px",
    "height_px": "Высота, px",
    "area_mm2": "Сечение, мм²",
    "material": "Материал",
    "auto_length_from_path": "Длина из маршрута",
    "meters_per_pixel": "Метров на пиксель",
    "segment_length_target_m": "Цель длины сегмента, м",
    "max_segments": "Макс. число сегментов",
    "coupling_gain": "ЭМ-связь",
    "permittivity_scale": "Коэф. диэлектрика",
    "mutual_inductance_gain": "Коэф. взаимной индукции",
    "thermal_coupling_gain": "Тепловая связь",
    "contact_resistance_ohm": "Контактное сопротивление, Ом",
    "dielectric_conductance_s_per_m": "Проводимость диэлектрика, С/м",
    "sigma_s_per_m": "Проводимость, С/м",
    "mu_r": "Отн. магнитная проницаемость",
    "proximity_gain": "Коэф. близости",
    "source_kind": "Тип источника",
    "waveform": "Форма сигнала",
    "impedance_ohm": "Импеданс порта, Ом",
    "amplitude_a": "Амплитуда, А",
    "emission_coefficient": "Коэф. эмиссии",
    "barrier_capacitance_f": "Барьерная емкость, Ф",
    "forward_drop_v": "Прямое падение, В",
    "breakdown_voltage_v": "Напряжение пробоя, В",
    "avalanche_softness_v": "Мягкость пробоя, В",
    "transit_time_s": "Transit time, с",
    "reverse_recovery_tau_s": "Reverse recovery, с",
    "junction_area_um2": "Площадь перехода, мкм²",
    "doping_p_cm3": "Легирование P, см^-3",
    "doping_n_cm3": "Легирование N, см^-3",
    "intrinsic_carrier_density_cm3": "Ni, см^-3",
    "carrier_lifetime_s": "Время жизни носителей, с",
    "relative_permittivity": "Отн. диэлектрич. проницаемость",
    "shunt_resistance_ohm": "Шунт, Ом",
    "color": "Цвет",
    "dark_resistance_ohm": "Темновое сопротивление, Ом",
    "light_resistance_ohm": "Световое сопротивление, Ом",
    "illumination_lux": "Освещенность, лк",
    "lux_reference": "Опорная освещенность, лк",
    "gamma": "Показатель гамма",
    "max_forward_current_a": "Макс. прямой ток, А",
    "luminous_efficiency": "Светоотдача",
    "threshold_v": "Порог, В",
    "clamp_voltage_v": "Напряжение ограничения, В",
    "dynamic_resistance_ohm": "Динамическое сопротивление, Ом",
    "leakage_current_a": "Ток утечки, А",
    "nonlinear_exponent": "Нелинейный показатель",
    "rds_on_ohm": "Rds(on), Ом",
    "cgs_f": "Cgs, Ф",
    "cgd_f": "Cgd, Ф",
    "cds_f": "Cds, Ф",
    "max_current_a": "Макс. ток, А",
    "transconductance_a_v2": "Крутизна, А/В²",
    "channel_length_modulation": "Модуляция канала",
    "gate_capacitance_f": "Емкость затвора, Ф",
    "gate_leakage_ohm": "Утечка затвора, Ом",
    "subthreshold_current_a": "Подпороговый ток, А",
    "subthreshold_swing_factor": "Подпороговый фактор",
    "trap_relaxation_s": "Релаксация ловушек, с",
    "channel_width_um": "Ширина канала, мкм",
    "channel_length_um": "Длина канала, мкм",
    "oxide_thickness_nm": "Толщина оксида, нм",
    "mobility_cm2_v_s": "Подвижность, см²/В·с",
    "overlap_length_um": "Overlap, мкм",
    "relative_permittivity_ox": "Проницаемость оксида",
    "body_doping_cm3": "Легирование подложки, см^-3",
    "open_loop_gain": "Усиление без ООС",
    "input_resistance_ohm": "Входное сопротивление, Ом",
    "output_resistance_ohm": "Выходное сопротивление, Ом",
    "slew_rate_v_s": "Slew Rate, В/с",
    "dominant_pole_hz": "Главный полюс, Гц",
    "output_current_limit_a": "Лимит выходного тока, А",
    "input_bias_current_a": "Ток смещения входа, А",
    "common_mode_rejection": "CMRR",
    "power_supply_rejection": "PSRR",
    "input_offset_v": "Смещение нуля, В",
    "supply_min_v": "Нижнее питание, В",
    "supply_max_v": "Верхнее питание, В",
    "quiescent_current_a": "Ток покоя, А",
    "current_rating_a": "Номинальный ток, А",
    "cold_resistance_ohm": "Холодное сопротивление, Ом",
    "melting_temperature_c": "Температура плавления, °C",
    "i2t_trip": "Порог I²t",
    "rated_voltage_v": "Номинальное напряжение, В",
    "rated_power_w": "Номинальная мощность, Вт",
    "cold_ratio": "Коэф. холодной нити",
    "filament_operating_temp_c": "Рабочая температура нити, °C",
    "max_display_current_a": "Предел индикации, А",
    "max_display_voltage_v": "Предел индикации, В",
    "input_capacitance_f": "Входная емкость, Ф",
    "lead_inductance_h": "Индуктивность выводов, Гн",
    "closed": "Замкнут",
    "position_b": "Положение B",
    "on_resistance_ohm": "Сопротивление вкл., Ом",
    "off_resistance_ohm": "Сопротивление выкл., Ом",
}

TERMINAL_LABELS = {
    "positive": "Плюс",
    "negative": "Минус",
    "drain": "Сток",
    "gate": "Затвор",
    "source": "Исток",
    "common": "Общий",
    "throw_a": "Контакт A",
    "throw_b": "Контакт B",
    "plus": "Неинвертирующий",
    "minus": "Инвертирующий",
    "out": "Выход",
    "ground": "Земля",
    "node": "Узел",
}

OBSERVABLE_LABELS = {
    "current_a": "ток, А",
    "voltage_v": "напряжение, В",
    "temperature_c": "температура, °C",
    "surface_temperature_c": "температура корпуса, °C",
    "brightness": "яркость",
    "glow": "накал",
    "soc": "заряд",
    "blown": "перегорел",
    "current_limit": "ограничение тока",
    "reading_a": "показание, А",
    "reading_v": "показание, В",
    "captured_v": "аудиовыход, В",
}


def _display_result_name(name: str) -> str:
    if name.startswith("__wire__"):
        return f"Провод {name.split('__wire__', 1)[1]}"
    return name


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Симулятор электрических цепей")
        self.resize(1520, 940)
        self.current_selected: ComponentItem | WireItem | MaterialRegionItem | FieldPortItem | None = None
        self.name_input: QLineEdit | None = None
        self.rotation_input: QLineEdit | None = None
        self.property_inputs: dict[str, QLineEdit] = {}
        self.library_buttons: list[QPushButton] = []
        self.animation_toggle_button: QPushButton | None = None
        self.animation_reset_button: QPushButton | None = None
        self.animation_info_label: QLabel | None = None
        self.last_circuit = None
        self.last_result = None
        self.last_field_snapshot = None
        self.last_fdtd_sequence = None
        self.last_maxwell_sequence = None

        self.scene = CircuitScene(self)
        self.scene.selection_changed.connect(self._on_selection_changed)
        self.scene.status_changed.connect(self.statusBar().showMessage)
        self.scene.animation_state_changed.connect(self._sync_animation_button)
        self.scene.animation_frame_changed.connect(self._update_animation_info)
        self.view = CircuitView(self.scene, self)

        self.duration_input = QLineEdit("0.03")
        self.dt_input = QLineEdit("0.0001")
        self.animation_speed_input = QLineEdit("1.0")
        self.animation_speed_input.setToolTip("x1 = реальное время, x2 = в 2 раза быстрее, x0.001 = в 1000 раз медленнее.")
        self.animation_speed_input.editingFinished.connect(self._on_animation_speed_edited)
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setPlainText("Результатов симуляции пока нет.")
        self.properties_group = QGroupBox("Свойства")
        self.properties_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        self.properties_form = QFormLayout()
        self.properties_group.setLayout(self.properties_form)
        self.sidebar_scroll = QScrollArea()
        self.sidebar_scroll.setWidgetResizable(True)
        self.sidebar_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.sidebar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.properties_scroll = QScrollArea()
        self.properties_scroll.setWidgetResizable(True)
        self.properties_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.properties_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.properties_scroll.setMinimumHeight(250)
        self.properties_panel = QWidget()
        self.properties_panel_layout = QVBoxLayout(self.properties_panel)
        self.properties_panel_layout.setContentsMargins(0, 0, 0, 0)
        self.properties_panel_layout.setSpacing(0)
        self.properties_panel_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)
        self.properties_panel_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.properties_panel_layout.addWidget(self.properties_group)
        self.properties_scroll.setWidget(self.properties_panel)

        self._build_ui()
        self._build_status_bar()
        self._clear_properties("Выбери элемент, чтобы менять его параметры.")
        self.statusBar().showMessage("Готово. Delete удаляет объект или провод. Esc отменяет добавление, соединение и трассировку.")

    def _build_ui(self) -> None:
        container = QWidget()
        self.setCentralWidget(container)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        layout.addWidget(self.view, stretch=1)
        sidebar = self._build_sidebar()
        self.sidebar_scroll.setWidget(sidebar)
        self.sidebar_scroll.setFixedWidth(396)
        layout.addWidget(self.sidebar_scroll)

    def _build_status_bar(self) -> None:
        self.animation_info_label = QLabel("Кадр: -- / -- | t = ---.--- с")
        self.statusBar().addPermanentWidget(self.animation_info_label)
        self._update_animation_info(-1, 0, 0.0)

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setMinimumWidth(360)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(10)
        library_box = self._build_library_box()
        library_box.setMinimumHeight(280)
        simulation_box = self._build_simulation_box()
        simulation_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        log_box = self._build_log_box()
        log_box.setMinimumHeight(150)
        sidebar_layout.addWidget(library_box)
        sidebar_layout.addWidget(simulation_box)
        sidebar_layout.addWidget(self.properties_scroll, stretch=1)
        sidebar_layout.addWidget(log_box, stretch=0)
        return sidebar

    def _build_library_box(self) -> QWidget:
        box = QGroupBox("Элементы")
        outer_layout = QVBoxLayout(box)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content_layout = QGridLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setHorizontalSpacing(6)
        content_layout.setVerticalSpacing(6)
        component_order = [
            "Ground",
            "Junction",
            "Battery",
            "Resistor",
            "Thermistor",
            "Photoresistor",
            "Ammeter",
            "Voltmeter",
            "Capacitor",
            "Inductor",
            "Diode",
            "LED",
            "Varistor",
            "Fuse",
            "Bulb",
            "Switch",
            "SPDT Switch",
            "AC Generator",
            "Pulse Generator",
            "Audio File Source",
            "Audio Sink",
            "MOSFET",
            "OpAmp",
        ]
        for index, kind in enumerate(component_order):
            state = default_visual_state(kind)
            template = template_for(kind)
            button = QPushButton(template.display_name)
            button.setIcon(build_qicon(kind, state))
            button.setIconSize(QSize(*template.size))
            button.setMinimumHeight(max(template.size[1] + 10, 64))
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            button.clicked.connect(lambda checked=False, value=kind: self.scene.set_place_mode(value))
            content_layout.addWidget(button, index, 0)
            self.library_buttons.append(button)
        scroll.setWidget(content)
        outer_layout.addWidget(scroll)
        return box

    def _build_simulation_box(self) -> QWidget:
        box = QGroupBox("Симуляция")
        layout = QGridLayout(box)
        layout.addWidget(QLabel("Длительность, с"), 0, 0)
        layout.addWidget(self.duration_input, 0, 1)
        layout.addWidget(QLabel("Шаг dt, с"), 1, 0)
        layout.addWidget(self.dt_input, 1, 1)
        layout.addWidget(QLabel("Скорость x"), 2, 0)
        layout.addWidget(self.animation_speed_input, 2, 1)

        wire_button = QPushButton("Соединить")
        wire_button.clicked.connect(self.scene.set_connect_mode)
        delete_button = QPushButton("Удалить выделенное")
        delete_button.clicked.connect(self.scene.delete_selected)
        route_button = QPushButton("Трассировка")
        route_button.clicked.connect(self.scene.set_route_mode)
        material_button = QPushButton("Среда")
        material_button.clicked.connect(self.scene.set_place_material_mode)
        port_button = QPushButton("Порт поля")
        port_button.clicked.connect(self.scene.set_place_port_mode)
        clear_button = QPushButton("Очистить")
        clear_button.clicked.connect(self.scene.clear_circuit)
        self.animation_toggle_button = QPushButton("Пауза")
        self.animation_toggle_button.clicked.connect(self._toggle_animation)
        self.animation_reset_button = QPushButton("Сброс анимации")
        self.animation_reset_button.clicked.connect(self._reset_animation)
        save_button = QPushButton("Сохранить JSON")
        save_button.clicked.connect(self._save_project)
        load_button = QPushButton("Загрузить JSON")
        load_button.clicked.connect(self._load_project)
        start_button = QPushButton("Старт")
        start_button.clicked.connect(self._run_simulation)
        plots_button = QPushButton("Графики")
        plots_button.clicked.connect(self._show_result_plots)
        export_audio_button = QPushButton("Экспорт аудио")
        export_audio_button.clicked.connect(self._export_audio)
        field_button = QPushButton("Карта поля")
        field_button.clicked.connect(self._show_field_map)
        fdtd_button = QPushButton("FDTD волна")
        fdtd_button.clicked.connect(self._show_fdtd_wave)
        maxwell_button = QPushButton("Maxwell TMz")
        maxwell_button.clicked.connect(self._show_maxwell_tmz_wave)
        maxwell_tez_button = QPushButton("Maxwell TEz")
        maxwell_tez_button.clicked.connect(self._show_maxwell_tez_wave)

        layout.addWidget(wire_button, 3, 0)
        layout.addWidget(delete_button, 3, 1)
        layout.addWidget(route_button, 4, 0, 1, 2)
        layout.addWidget(material_button, 5, 0)
        layout.addWidget(port_button, 5, 1)
        layout.addWidget(clear_button, 6, 0)
        layout.addWidget(self.animation_toggle_button, 6, 1)
        layout.addWidget(self.animation_reset_button, 7, 0, 1, 2)
        layout.addWidget(save_button, 8, 0)
        layout.addWidget(load_button, 8, 1)
        layout.addWidget(start_button, 9, 0)
        layout.addWidget(plots_button, 9, 1)
        layout.addWidget(export_audio_button, 10, 0, 1, 2)
        layout.addWidget(field_button, 11, 0, 1, 2)
        layout.addWidget(fdtd_button, 12, 0, 1, 2)
        layout.addWidget(maxwell_button, 13, 0)
        layout.addWidget(maxwell_tez_button, 13, 1)
        return box

    def _build_log_box(self) -> QWidget:
        box = QGroupBox("Последний запуск")
        layout = QVBoxLayout(box)
        layout.addWidget(self.log_output)
        return box

    def _clear_properties(self, hint: str) -> None:
        self.name_input = None
        self.rotation_input = None
        self.property_inputs.clear()
        while self.properties_form.rowCount():
            self.properties_form.removeRow(0)
        hint_label = QLabel(hint)
        hint_label.setWordWrap(True)
        self.properties_form.addRow(hint_label)
        self.properties_group.adjustSize()
        self.properties_panel.adjustSize()

    def _on_selection_changed(self, selected: ComponentItem | WireItem | MaterialRegionItem | FieldPortItem | None) -> None:
        self.current_selected = selected
        if selected is None:
            self._clear_properties("Выбери элемент, чтобы менять его параметры.")
            return
        if isinstance(selected, WireItem):
            self._show_wire_properties(selected)
            return
        if isinstance(selected, MaterialRegionItem):
            self._show_field_object_properties(selected, "Область материала")
            return
        if isinstance(selected, FieldPortItem):
            self._show_field_object_properties(selected, "Полевой порт")
            return
        component = selected
        self.rotation_input = None
        self.property_inputs.clear()
        while self.properties_form.rowCount():
            self.properties_form.removeRow(0)
        template = template_for(component.kind)
        header = QLabel(f"{component.name} ({template.display_name})")
        header.setStyleSheet("font-weight: 600;")
        self.properties_form.addRow(header)
        self.name_input = QLineEdit(component.name)
        self.properties_form.addRow(QLabel("Имя"), self.name_input)
        self.rotation_input = QLineEdit(f"{float(component.rotation()):g}")
        self.properties_form.addRow(QLabel("Поворот, °"), self.rotation_input)
        translated_terminals = ", ".join(TERMINAL_LABELS.get(label, label) for label in COMPONENT_TERMINALS[component.kind])
        self.properties_form.addRow(QLabel("Выводы"), QLabel(translated_terminals))
        for key, value in component.params.items():
            if key in HIDDEN_USER_PARAMS:
                continue
            line = QLineEdit(str(value))
            self.property_inputs[key] = line
            self.properties_form.addRow(QLabel(PARAMETER_LABELS.get(key, key)), line)
        if not self.property_inputs:
            self.properties_form.addRow(QLabel("Редактируемых параметров нет."))
        apply_button = QPushButton("Применить")
        apply_button.clicked.connect(self._apply_properties)
        self.properties_form.addRow(apply_button)
        self.properties_group.adjustSize()
        self.properties_panel.adjustSize()

    def _show_field_object_properties(self, item: MaterialRegionItem | FieldPortItem, title: str) -> None:
        self.rotation_input = None
        self.property_inputs.clear()
        while self.properties_form.rowCount():
            self.properties_form.removeRow(0)
        header = QLabel(f"{item.name} ({title})")
        header.setStyleSheet("font-weight: 600;")
        self.properties_form.addRow(header)
        self.name_input = QLineEdit(item.name)
        self.properties_form.addRow(QLabel("Имя"), self.name_input)
        for key, value in item.params.items():
            line = QLineEdit(str(value))
            self.property_inputs[key] = line
            self.properties_form.addRow(QLabel(PARAMETER_LABELS.get(key, key)), line)
        apply_button = QPushButton("Применить")
        apply_button.clicked.connect(self._apply_properties)
        self.properties_form.addRow(apply_button)
        self.properties_group.adjustSize()
        self.properties_panel.adjustSize()

    def _show_wire_properties(self, wire: WireItem) -> None:
        self.name_input = None
        self.property_inputs.clear()
        while self.properties_form.rowCount():
            self.properties_form.removeRow(0)
        header = QLabel(f"Провод {wire.wire_id}")
        header.setStyleSheet("font-weight: 600;")
        self.properties_form.addRow(header)
        a = wire.a_terminal.component_item
        b = wire.b_terminal.component_item
        a_label = COMPONENT_TERMINALS[a.kind][wire.a_terminal.terminal_index]
        b_label = COMPONENT_TERMINALS[b.kind][wire.b_terminal.terminal_index]
        endpoints = f"{a.name}.{TERMINAL_LABELS.get(a_label, a_label)} <-> {b.name}.{TERMINAL_LABELS.get(b_label, b_label)}"
        self.properties_form.addRow(QLabel("Соединение"), QLabel(endpoints))
        self.properties_form.addRow(QLabel("Геометрическая длина, px"), QLabel(f"{wire.path_length_px():.1f}"))
        self.properties_form.addRow(QLabel("Эффективная длина, м"), QLabel(f"{wire.effective_length_m():.4f}"))
        self.properties_form.addRow(QLabel("Оценка R, Ом"), QLabel(f"{wire.estimated_resistance_ohm():.6f}"))
        hint_label = QLabel("Трассировка: клик по проводу или холсту добавляет точку, перетаскивание двигает ее, двойной клик по точке удаляет.")
        hint_label.setWordWrap(True)
        self.properties_form.addRow(QLabel("Подсказка"), hint_label)
        for key, value in wire.params.items():
            line = QLineEdit(str(value))
            self.property_inputs[key] = line
            self.properties_form.addRow(QLabel(PARAMETER_LABELS.get(key, key)), line)
        reset_route_button = QPushButton("Сбросить маршрут")
        reset_route_button.clicked.connect(self._reset_selected_wire_route)
        self.properties_form.addRow(reset_route_button)
        apply_button = QPushButton("Применить")
        apply_button.clicked.connect(self._apply_properties)
        self.properties_form.addRow(apply_button)
        self.properties_group.adjustSize()
        self.properties_panel.adjustSize()

    def _coerce_value(self, raw: str, template_value: Any) -> Any:
        if isinstance(template_value, bool):
            return raw.strip().lower() in {"1", "true", "yes", "on", "closed", "да", "вкл", "замкнут", "истина"}
        if isinstance(template_value, int) and not isinstance(template_value, bool):
            return int(float(raw))
        if isinstance(template_value, float):
            return float(raw)
        return raw

    def _apply_properties(self) -> None:
        if self.current_selected is None:
            return
        try:
            if isinstance(self.current_selected, WireItem):
                base = default_params("Wire")
                updated = {}
                for key, widget in self.property_inputs.items():
                    updated[key] = self._coerce_value(widget.text(), base.get(key, self.current_selected.params.get(key, "")))
                self.current_selected.apply_params(updated)
                self.statusBar().showMessage(f"Параметры провода {self.current_selected.wire_id} обновлены.")
                self._show_wire_properties(self.current_selected)
                return
            if isinstance(self.current_selected, MaterialRegionItem):
                if self.name_input is not None:
                    self.scene.rename_material(self.current_selected, self.name_input.text())
                base = {
                    "width_px": 220.0,
                    "height_px": 140.0,
                    "epsilon_r": 4.2,
                    "sigma_s_per_m": 0.0,
                    "mu_r": 1.0,
                }
                updated = {}
                for key, widget in self.property_inputs.items():
                    updated[key] = self._coerce_value(widget.text(), base.get(key, self.current_selected.params.get(key, "")))
                self.current_selected.apply_params(updated)
                self.statusBar().showMessage(f"Параметры области обновлены: {self.current_selected.name}.")
                self._show_field_object_properties(self.current_selected, "Область материала")
                return
            if isinstance(self.current_selected, FieldPortItem):
                if self.name_input is not None:
                    self.scene.rename_port(self.current_selected, self.name_input.text())
                base = {
                    "width_px": 90.0,
                    "height_px": 18.0,
                    "rotation_deg": 0.0,
                    "source_kind": "voltage",
                    "waveform": "sine",
                    "amplitude_v": 5.0,
                    "amplitude_a": 0.2,
                    "frequency_hz": 1.0e6,
                    "phase_rad": 0.0,
                    "impedance_ohm": 50.0,
                }
                updated = {}
                for key, widget in self.property_inputs.items():
                    updated[key] = self._coerce_value(widget.text(), base.get(key, self.current_selected.params.get(key, "")))
                self.current_selected.apply_params(updated)
                self.statusBar().showMessage(f"Параметры порта обновлены: {self.current_selected.name}.")
                self._show_field_object_properties(self.current_selected, "Полевой порт")
                return
            if self.name_input is not None:
                self.scene.rename_component(self.current_selected, self.name_input.text())
            if self.rotation_input is not None:
                self.current_selected.apply_rotation(float(self.rotation_input.text()))
            base = default_params(self.current_selected.kind)
            updated = {}
            for key, widget in self.property_inputs.items():
                updated[key] = self._coerce_value(widget.text(), base.get(key, self.current_selected.params.get(key, "")))
            self.current_selected.apply_params(updated)
            self.statusBar().showMessage(f"Параметры обновлены: {self.current_selected.name}.")
            self._on_selection_changed(self.current_selected)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Ошибка изменения свойств", str(exc))

    def _reset_selected_wire_route(self) -> None:
        if not isinstance(self.current_selected, WireItem):
            return
        self.current_selected.clear_route_points()
        self.statusBar().showMessage(f"Маршрут провода {self.current_selected.wire_id} сброшен.")
        self._show_wire_properties(self.current_selected)

    def _parse_simulation_settings(self) -> tuple[float, float]:
        duration = float(self.duration_input.text())
        dt = float(self.dt_input.text())
        if duration <= 0.0 or dt <= 0.0:
            raise ValueError("Длительность и шаг dt должны быть положительными.")
        return duration, dt

    def _parse_animation_speed(self) -> float:
        speed = float(self.animation_speed_input.text().strip().replace(",", "."))
        if speed <= 0.0:
            raise ValueError("Скорость анимации должна быть положительной.")
        return speed

    def _apply_animation_speed(self) -> float:
        speed = self._parse_animation_speed()
        self.scene.set_animation_speed(speed)
        self.animation_speed_input.setText(f"{speed:g}")
        return speed

    def _on_animation_speed_edited(self) -> None:
        try:
            speed = self._apply_animation_speed()
        except Exception as exc:  # noqa: BLE001
            self.animation_speed_input.setText(f"{self.scene.animation_speed:g}")
            QMessageBox.warning(self, "Ошибка скорости анимации", str(exc))
            return
        self.statusBar().showMessage(f"Скорость анимации: x{speed:g}")

    def _sync_animation_button(self) -> None:
        if self.animation_toggle_button is None:
            return
        if self.scene.animation_result is None or len(self.scene.animation_result.time_s) <= 1:
            self.animation_toggle_button.setText("Пауза")
            return
        self.animation_toggle_button.setText("Пауза" if self.scene.animation_timer.isActive() else "Продолжить")

    def _toggle_animation(self) -> None:
        try:
            speed = self._apply_animation_speed()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Ошибка скорости анимации", str(exc))
            return
        active = self.scene.toggle_animation()
        self._sync_animation_button()
        if self.scene.animation_result is None:
            self.statusBar().showMessage("Анимация еще не рассчитана.")
            return
        self.statusBar().showMessage(f"Анимация идет на скорости x{speed:g}." if active else "Анимация поставлена на паузу.")

    def _reset_animation(self) -> None:
        reset = self.scene.reset_animation()
        self._sync_animation_button()
        if not reset:
            self.statusBar().showMessage("Анимации для сброса пока нет.")
            return
        self.statusBar().showMessage("Анимация остановлена и возвращена к первому кадру.")

    def _update_animation_info(self, frame_index: int, total_frames: int, time_s: float) -> None:
        if self.animation_info_label is None:
            return
        if total_frames <= 0 or frame_index < 0:
            self.animation_info_label.setText("Кадр: -- / -- | t = ---.--- с")
            return
        self.animation_info_label.setText(f"Кадр: {frame_index + 1} / {total_frames} | t = {time_s:.3f} с")

    def _save_project(self) -> None:
        try:
            duration, dt = self._parse_simulation_settings()
            project = self.scene.build_project("Схема на холсте", duration, dt)
            path, _ = QFileDialog.getSaveFileName(self, "Сохранить проект", "schema.json", "JSON файлы (*.json)")
            if not path:
                return
            project.save(path)
            self.statusBar().showMessage(f"Проект сохранен: {path}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Ошибка сохранения", str(exc))

    def _load_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Загрузить проект", "", "JSON файлы (*.json)")
        if not path:
            return
        try:
            project = load_project(path)
            self.duration_input.setText(f"{project.settings.duration_s:g}")
            self.dt_input.setText(f"{project.settings.dt_s:g}")
            self.scene.load_project(project)
            self._sync_animation_button()
            self.statusBar().showMessage(f"Проект загружен: {path}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Ошибка загрузки", str(exc))

    def _run_simulation(self) -> None:
        try:
            self._simulate_scene()
            self.statusBar().showMessage("Симуляция завершена. Анимация запущена и будет повторяться по кругу.")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Ошибка симуляции", str(exc))

    def _simulate_scene(self):
        self._apply_animation_speed()
        duration, dt = self._parse_simulation_settings()
        project = self.scene.build_project("Схема на холсте", duration, dt)
        circuit = project.to_circuit()
        result = circuit.simulate(duration, dt)
        self.last_circuit = circuit
        self.last_result = result
        self.last_field_snapshot = None
        self.last_fdtd_sequence = None
        self.last_maxwell_sequence = None
        self.scene.play_result(result)
        self._sync_animation_button()
        self._write_log(result)
        return circuit, result

    def _show_result_plots(self) -> None:
        try:
            _, result = self._simulate_scene()
            dialog = ResultPlotDialog(result, self)
            dialog.exec()
            self.statusBar().showMessage("Графики рассчитаны.")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Ошибка графиков", str(exc))

    def _show_field_map(self) -> None:
        try:
            circuit, result = self._simulate_scene()
            self.last_field_snapshot = solve_quasi_static_field(circuit, result)
            dialog = FieldPreviewDialog(self.last_field_snapshot, self)
            dialog.exec()
            self.statusBar().showMessage("Карта поля рассчитана.")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Ошибка расчета поля", str(exc))

    def _show_fdtd_wave(self) -> None:
        try:
            circuit, result = self._simulate_scene()
            self.last_fdtd_sequence = simulate_fdtd_wave(circuit, result)
            dialog = FieldPreviewDialog(self.last_fdtd_sequence, self)
            dialog.exec()
            self.statusBar().showMessage("FDTD-волна рассчитана.")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Ошибка FDTD", str(exc))

    def _show_maxwell_tmz_wave(self) -> None:
        try:
            circuit, result = self._simulate_scene()
            self.last_maxwell_sequence = simulate_full_wave_maxwell_2d(circuit, result, mode="tmz")
            dialog = FieldPreviewDialog(self.last_maxwell_sequence, self)
            dialog.exec()
            self.statusBar().showMessage("Maxwell TMz рассчитан.")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Ошибка Maxwell TMz", str(exc))

    def _show_maxwell_tez_wave(self) -> None:
        try:
            circuit, result = self._simulate_scene()
            self.last_maxwell_sequence = simulate_full_wave_maxwell_2d(circuit, result, mode="tez")
            dialog = FieldPreviewDialog(self.last_maxwell_sequence, self)
            dialog.exec()
            self.statusBar().showMessage("Maxwell TEz рассчитан.")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Ошибка Maxwell TEz", str(exc))

    def _audio_sink_names(self, result) -> list[str]:
        sinks: list[str] = []
        for component_name, observables in result.component_observables.items():
            if "captured_v" in observables:
                sinks.append(component_name)
        return sinks

    def _selected_audio_sink_name(self, sink_names: list[str]) -> str | None:
        if len(sink_names) == 1:
            return sink_names[0]
        if isinstance(self.current_selected, ComponentItem) and self.current_selected.kind == "Audio Sink":
            if self.current_selected.name in sink_names:
                return self.current_selected.name
        return None

    def _default_audio_export_path(self, sink_name: str) -> str:
        base_name = f"{sink_name}_processed.wav" if sink_name else "processed_audio.wav"
        return str(Path.cwd() / base_name)

    def _audio_export_filter(self) -> str:
        patterns = " ".join(f"*{extension}" for extension in sorted(SUPPORTED_AUDIO_EXPORT_EXTENSIONS))
        return f"Аудио ({patterns})"

    def _export_audio(self) -> None:
        try:
            _, result = self._simulate_scene()
            sink_names = self._audio_sink_names(result)
            if not sink_names:
                raise ValueError("На схеме нет ни одного Audio Sink с наблюдаемым captured_v.")
            sink_name = self._selected_audio_sink_name(sink_names)
            if sink_name is None:
                raise ValueError(
                    "На схеме несколько Audio Sink. Выдели нужный Audio Sink и повтори экспорт."
                )
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Экспорт аудио",
                self._default_audio_export_path(sink_name),
                self._audio_export_filter(),
            )
            if not path:
                return
            target_path = Path(path)
            if not target_path.suffix:
                target_path = target_path.with_suffix(".wav")
            if not is_supported_audio_export_path(target_path):
                supported = ", ".join(sorted(SUPPORTED_AUDIO_EXPORT_EXTENSIONS))
                raise ValueError(f"Неподдерживаемый формат аудио. Доступно: {supported}")
            buffer = audio_buffer_from_simulation_result(result, sink_name, observable_key="captured_v", normalize=False)
            save_audio_file(target_path, buffer, normalize=False)
            self.statusBar().showMessage(f"Аудио экспортировано: {target_path}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Ошибка экспорта аудио", str(exc))

    def _write_log(self, result) -> None:
        lines = [f"Схема: {result.metadata['name']}", f"Длительность: {result.metadata['duration_s']:.6f} с", "", "Узлы:"]
        for node, values in result.node_voltages.items():
            lines.append(f"  {node}: {values[-1]:.5f} V")
        lines.append("")
        lines.append("Компоненты:")
        for component_name, observables in result.component_observables.items():
            chunks = []
            for key in (
                "current_a",
                "voltage_v",
                "temperature_c",
                "surface_temperature_c",
                "brightness",
                "glow",
                "soc",
                "blown",
                "current_limit",
                "reading_a",
                "reading_v",
                "captured_v",
            ):
                if key in observables:
                    chunks.append(f"{OBSERVABLE_LABELS.get(key, key)}={observables[key][-1]:.5g}")
            lines.append(f"  {_display_result_name(component_name)}: " + ", ".join(chunks))
        self.log_output.setPlainText("\n".join(lines))


_def_app_style = """
QMainWindow, QWidget {
    background: #efe7db;
    color: #1f2933;
}
QGroupBox {
    border: 1px solid #cfbfa8;
    border-radius: 10px;
    margin-top: 10px;
    font-weight: 600;
    padding-top: 10px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
}
QPushButton {
    background: #fffaf2;
    border: 1px solid #cfbfa8;
    border-radius: 8px;
    padding: 6px 10px;
}
QPushButton:hover {
    background: #f6ead7;
}
QLineEdit, QTextEdit {
    background: #fffaf2;
    border: 1px solid #cfbfa8;
    border-radius: 8px;
    padding: 6px;
}
QScrollArea {
    border: none;
}
"""


def launch() -> None:
    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(_def_app_style)
    window = MainWindow()
    window.show()
    app.exec()
