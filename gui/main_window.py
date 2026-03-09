from __future__ import annotations

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

from core import COMPONENT_TERMINALS, load_project
from core.field_solver import simulate_fdtd_wave, simulate_full_wave_maxwell_2d, solve_quasi_static_field

from .canvas import CircuitScene, CircuitView, ComponentItem, WireItem
from .components_visual import build_qicon, default_params, default_visual_state, template_for
from .field_dialog import FieldPreviewDialog

HIDDEN_USER_PARAMS = {"chemistry"}


PARAMETER_LABELS = {
    "nominal_voltage_v": "Номинальное напряжение, В",
    "capacity_mah": "Емкость, мАч",
    "chemistry": "Химия",
    "internal_resistance_ohm": "Внутреннее сопротивление, Ом",
    "amplitude_v": "Амплитуда, В",
    "frequency_hz": "Частота, Гц",
    "phase_rad": "Фаза, рад",
    "phase_noise_rad": "Фазовый шум, рад",
    "frequency_error": "Ошибка частоты",
    "harmonic_2_ratio": "2-я гармоника",
    "harmonic_3_ratio": "3-я гармоника",
    "resistance_ohm": "Сопротивление, Ом",
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
    "proximity_gain": "Коэф. близости",
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
    "max_forward_current_a": "Макс. прямой ток, А",
    "luminous_efficiency": "Светоотдача",
    "threshold_v": "Порог, В",
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
    "on_resistance_ohm": "Сопротивление вкл., Ом",
    "off_resistance_ohm": "Сопротивление выкл., Ом",
}

TERMINAL_LABELS = {
    "positive": "Плюс",
    "negative": "Минус",
    "drain": "Сток",
    "gate": "Затвор",
    "source": "Исток",
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
        self.current_selected: ComponentItem | WireItem | None = None
        self.name_input: QLineEdit | None = None
        self.rotation_input: QLineEdit | None = None
        self.property_inputs: dict[str, QLineEdit] = {}
        self.library_buttons: list[QPushButton] = []
        self.last_circuit = None
        self.last_result = None
        self.last_field_snapshot = None
        self.last_fdtd_sequence = None
        self.last_maxwell_sequence = None

        self.scene = CircuitScene(self)
        self.scene.selection_changed.connect(self._on_selection_changed)
        self.scene.status_changed.connect(self.statusBar().showMessage)
        self.view = CircuitView(self.scene, self)

        self.duration_input = QLineEdit("0.03")
        self.dt_input = QLineEdit("0.0001")
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
            "Ammeter",
            "Voltmeter",
            "Capacitor",
            "Inductor",
            "Diode",
            "LED",
            "Fuse",
            "Bulb",
            "Switch",
            "AC Generator",
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

        wire_button = QPushButton("Соединить")
        wire_button.clicked.connect(self.scene.set_connect_mode)
        delete_button = QPushButton("Удалить выделенное")
        delete_button.clicked.connect(self.scene.delete_selected)
        route_button = QPushButton("Трассировка")
        route_button.clicked.connect(self.scene.set_route_mode)
        clear_button = QPushButton("Очистить")
        clear_button.clicked.connect(self.scene.clear_circuit)
        stop_button = QPushButton("Стоп анимации")
        stop_button.clicked.connect(self.scene.stop_animation)
        save_button = QPushButton("Сохранить JSON")
        save_button.clicked.connect(self._save_project)
        load_button = QPushButton("Загрузить JSON")
        load_button.clicked.connect(self._load_project)
        start_button = QPushButton("Старт")
        start_button.clicked.connect(self._run_simulation)
        field_button = QPushButton("Карта поля")
        field_button.clicked.connect(self._show_field_map)
        fdtd_button = QPushButton("FDTD волна")
        fdtd_button.clicked.connect(self._show_fdtd_wave)
        maxwell_button = QPushButton("Maxwell 2D")
        maxwell_button.clicked.connect(self._show_maxwell_wave)

        layout.addWidget(wire_button, 2, 0)
        layout.addWidget(delete_button, 2, 1)
        layout.addWidget(route_button, 3, 0, 1, 2)
        layout.addWidget(clear_button, 4, 0)
        layout.addWidget(stop_button, 4, 1)
        layout.addWidget(save_button, 5, 0)
        layout.addWidget(load_button, 5, 1)
        layout.addWidget(start_button, 6, 0)
        layout.addWidget(field_button, 6, 1)
        layout.addWidget(fdtd_button, 7, 0, 1, 2)
        layout.addWidget(maxwell_button, 8, 0, 1, 2)
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

    def _on_selection_changed(self, selected: ComponentItem | WireItem | None) -> None:
        self.current_selected = selected
        if selected is None:
            self._clear_properties("Выбери элемент, чтобы менять его параметры.")
            return
        if isinstance(selected, WireItem):
            self._show_wire_properties(selected)
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
            self.statusBar().showMessage(f"Проект загружен: {path}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Ошибка загрузки", str(exc))

    def _run_simulation(self) -> None:
        try:
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
            self._write_log(result)
            self.statusBar().showMessage("Симуляция завершена. Анимация запущена.")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Ошибка симуляции", str(exc))

    def _show_field_map(self) -> None:
        try:
            duration, dt = self._parse_simulation_settings()
            project = self.scene.build_project("Схема на холсте", duration, dt)
            self.last_circuit = project.to_circuit()
            self.last_result = self.last_circuit.simulate(duration, dt)
            self.scene.play_result(self.last_result)
            self._write_log(self.last_result)
            self.last_field_snapshot = solve_quasi_static_field(self.last_circuit, self.last_result)
            dialog = FieldPreviewDialog(self.last_field_snapshot, self)
            dialog.exec()
            self.statusBar().showMessage("Карта поля рассчитана.")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Ошибка расчета поля", str(exc))

    def _show_fdtd_wave(self) -> None:
        try:
            duration, dt = self._parse_simulation_settings()
            project = self.scene.build_project("Схема на холсте", duration, dt)
            self.last_circuit = project.to_circuit()
            self.last_result = self.last_circuit.simulate(duration, dt)
            self.scene.play_result(self.last_result)
            self._write_log(self.last_result)
            self.last_fdtd_sequence = simulate_fdtd_wave(self.last_circuit, self.last_result)
            dialog = FieldPreviewDialog(self.last_fdtd_sequence, self)
            dialog.exec()
            self.statusBar().showMessage("FDTD-волна рассчитана.")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Ошибка FDTD", str(exc))

    def _show_maxwell_wave(self) -> None:
        try:
            duration, dt = self._parse_simulation_settings()
            project = self.scene.build_project("Схема на холсте", duration, dt)
            self.last_circuit = project.to_circuit()
            self.last_result = self.last_circuit.simulate(duration, dt)
            self.scene.play_result(self.last_result)
            self._write_log(self.last_result)
            self.last_maxwell_sequence = simulate_full_wave_maxwell_2d(self.last_circuit, self.last_result)
            dialog = FieldPreviewDialog(self.last_maxwell_sequence, self)
            dialog.exec()
            self.statusBar().showMessage("Maxwell 2D рассчитан.")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Ошибка Maxwell 2D", str(exc))

    def _write_log(self, result) -> None:
        lines = [f"Схема: {result.metadata['name']}", f"Длительность: {result.metadata['duration_s']:.6f} с", "", "Узлы:"]
        for node, values in result.node_voltages.items():
            lines.append(f"  {node}: {values[-1]:.5f} V")
        lines.append("")
        lines.append("Компоненты:")
        for component_name, observables in result.component_observables.items():
            chunks = []
            for key in ("current_a", "voltage_v", "temperature_c", "surface_temperature_c", "brightness", "glow", "soc", "blown", "current_limit", "reading_a", "reading_v"):
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
