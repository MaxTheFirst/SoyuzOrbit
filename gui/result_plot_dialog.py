from __future__ import annotations

import math

from PyQt6.QtCore import QSignalBlocker
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from core.result_plots import (
    PLOT_PANEL_LABELS,
    available_plot_component_names,
    available_plot_panel_ids,
    display_plot_name,
    render_result_figure,
)


class ResultPlotDialog(QDialog):
    def __init__(self, result, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.result = result
        self.available_panel_ids = available_plot_panel_ids(result)
        self.panel_checks: dict[str, QCheckBox] = {}
        self.component_checks: dict[str, QCheckBox] = {}
        self.preview_base_dpi = 110.0
        self.preview_render_scale = 2.0

        self.setWindowTitle("Графики симуляции")
        self.resize(1220, 900)

        self.figure = Figure(dpi=self.preview_base_dpi * self.preview_render_scale)
        self.figure_canvas = FigureCanvasAgg(self.figure)
        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        self.preview_label = QLabel()
        self.preview_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.preview_label.setPixmap(QPixmap())

        controls_box = QWidget()
        controls_layout = QGridLayout(controls_box)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setHorizontalSpacing(12)
        controls_layout.setVerticalSpacing(6)

        for index, panel_id in enumerate(self.available_panel_ids):
            checkbox = QCheckBox(PLOT_PANEL_LABELS.get(panel_id, panel_id))
            checkbox.setChecked(True)
            checkbox.toggled.connect(self._refresh_plot)
            controls_layout.addWidget(checkbox, index // 3, index % 3)
            self.panel_checks[panel_id] = checkbox

        component_box = QWidget()
        component_layout = QGridLayout(component_box)
        component_layout.setContentsMargins(0, 0, 0, 0)
        component_layout.setHorizontalSpacing(12)
        component_layout.setVerticalSpacing(6)

        for index, component_name in enumerate(available_plot_component_names(result)):
            checkbox = QCheckBox(display_plot_name(component_name))
            checkbox.setChecked(True)
            checkbox.toggled.connect(self._refresh_plot)
            component_layout.addWidget(checkbox, index // 2, index % 2)
            self.component_checks[component_name] = checkbox

        component_scroll = QScrollArea()
        component_scroll.setWidget(component_box)
        component_scroll.setWidgetResizable(True)
        component_scroll.setMaximumHeight(190)

        select_all_button = QPushButton("Все панели")
        select_all_button.clicked.connect(self._select_all)
        clear_button = QPushButton("Снять выбор")
        clear_button.clicked.connect(self._clear_selection)
        select_all_components_button = QPushButton("Все компоненты")
        select_all_components_button.clicked.connect(self._select_all_components)
        clear_components_button = QPushButton("Снять компоненты")
        clear_components_button.clicked.connect(self._clear_components)
        save_button = QPushButton("Сохранить PNG")
        save_button.clicked.connect(self._save_png)
        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(self.accept)

        button_row = QHBoxLayout()
        button_row.addWidget(select_all_button)
        button_row.addWidget(clear_button)
        button_row.addWidget(select_all_components_button)
        button_row.addWidget(clear_components_button)
        button_row.addWidget(save_button)
        button_row.addStretch(1)
        button_row.addWidget(close_button)

        preview_scroll = QScrollArea()
        preview_scroll.setWidget(self.preview_label)
        preview_scroll.setWidgetResizable(False)
        self.preview_scroll = preview_scroll

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Панели"))
        layout.addWidget(controls_box)
        layout.addWidget(QLabel("Компоненты"))
        layout.addWidget(component_scroll)
        layout.addLayout(button_row)
        layout.addWidget(self.info_label)
        layout.addWidget(preview_scroll, stretch=1)

        self._refresh_plot()

    def _selected_panels(self) -> list[str]:
        return [panel_id for panel_id, checkbox in self.panel_checks.items() if checkbox.isChecked()]

    def _selected_components(self) -> set[str] | None:
        if not self.component_checks:
            return None
        selected = {component_name for component_name, checkbox in self.component_checks.items() if checkbox.isChecked()}
        if len(selected) == len(self.component_checks):
            return None
        return selected

    def _select_all(self) -> None:
        blockers = [QSignalBlocker(checkbox) for checkbox in self.panel_checks.values()]
        for checkbox in self.panel_checks.values():
            checkbox.setChecked(True)
        del blockers
        self._refresh_plot()

    def _clear_selection(self) -> None:
        blockers = [QSignalBlocker(checkbox) for checkbox in self.panel_checks.values()]
        for checkbox in self.panel_checks.values():
            checkbox.setChecked(False)
        del blockers
        self._refresh_plot()

    def _select_all_components(self) -> None:
        blockers = [QSignalBlocker(checkbox) for checkbox in self.component_checks.values()]
        for checkbox in self.component_checks.values():
            checkbox.setChecked(True)
        del blockers
        self._refresh_plot()

    def _clear_components(self) -> None:
        blockers = [QSignalBlocker(checkbox) for checkbox in self.component_checks.values()]
        for checkbox in self.component_checks.values():
            checkbox.setChecked(False)
        del blockers
        self._refresh_plot()

    def _update_preview(self) -> None:
        self.figure_canvas.draw()
        width_px, height_px = self.figure_canvas.get_width_height()
        buffer = self.figure_canvas.buffer_rgba()
        image = QImage(buffer, width_px, height_px, QImage.Format.Format_RGBA8888).copy()
        pixmap = QPixmap.fromImage(image)
        pixmap.setDevicePixelRatio(self.preview_render_scale)
        self.preview_label.setPixmap(pixmap)
        self.preview_label.setFixedSize(pixmap.deviceIndependentSize().toSize())

    def _save_png(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить графики", "plots.png", "PNG файлы (*.png)")
        if not path:
            return
        self.figure.savefig(path, dpi=max(self.figure.dpi, 220.0))

    def _refresh_plot(self) -> None:
        selected_panels = self._selected_panels()
        selected_components = self._selected_components()
        viewport_width_px = self.preview_scroll.viewport().width() - 24
        if viewport_width_px < 400:
            viewport_width_px = self.width() - 80
        viewport_width_px = max(viewport_width_px, 900)
        self.figure.set_dpi(self.preview_base_dpi * self.preview_render_scale)
        figure_width_in = viewport_width_px / self.preview_base_dpi
        rendered_panels = render_result_figure(
            self.figure,
            self.result,
            selected_panels,
            visible_components=selected_components,
            figure_width_in=figure_width_in,
        )
        width_px = int(math.ceil(self.figure.get_figwidth() * self.figure.dpi))
        height_px = int(math.ceil(self.figure.get_figheight() * self.figure.dpi))
        if width_px > 0 and height_px > 0:
            self._update_preview()
            self.preview_scroll.horizontalScrollBar().setValue(0)
            self.preview_scroll.verticalScrollBar().setValue(0)

        if not self.available_panel_ids:
            self.info_label.setText("В результате симуляции нет данных для графиков.")
            return
        if not rendered_panels:
            if selected_components == set():
                self.info_label.setText("Выберите хотя бы один компонент.")
                return
            self.info_label.setText("Выберите хотя бы одну панель графиков.")
            return
        labels = ", ".join(PLOT_PANEL_LABELS.get(panel_id, panel_id) for panel_id in rendered_panels)
        if selected_components is None:
            component_note = "все компоненты"
        elif not selected_components:
            component_note = "компоненты не выбраны"
        else:
            component_note = ", ".join(display_plot_name(name) for name in sorted(selected_components))
        self.info_label.setText(f"Показаны панели: {labels} | Компоненты: {component_note}")

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._refresh_plot()
