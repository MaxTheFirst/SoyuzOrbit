from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from core.field_solver import FieldVolumeSequence

try:
    from PIL.ImageQt import ImageQt
except Exception:  # noqa: BLE001
    ImageQt = None


LAYER_LABELS = {
    "potential": "Потенциал, В",
    "electric": "|E|, В/м",
    "magnetic": "|B|, Тл",
}

PLANE_LABELS = {
    "xy": "XY",
    "xz": "XZ",
    "yz": "YZ",
}


class VolumeFieldPreviewDialog(QDialog):
    def __init__(self, snapshot: FieldVolumeSequence, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.snapshot = snapshot
        self.setWindowTitle("Maxwell 3D")
        self.resize(1080, 840)
        self.play_timer = QTimer(self)
        self.play_timer.timeout.connect(self._advance_frame)

        self.layer_combo = QComboBox()
        self.layer_combo.addItem("Потенциал", "potential")
        self.layer_combo.addItem("Электрическое поле", "electric")
        self.layer_combo.addItem("Магнитное поле", "magnetic")
        self.layer_combo.setCurrentIndex(1)
        self.layer_combo.currentIndexChanged.connect(self._refresh_preview)

        self.render_combo = QComboBox()
        self.render_combo.addItem("Срез", "slice")
        self.render_combo.addItem("Изоповерхность", "iso")
        self.render_combo.currentIndexChanged.connect(self._on_render_changed)

        self.plane_combo = QComboBox()
        self.plane_combo.addItem("Срез XY", "xy")
        self.plane_combo.addItem("Срез XZ", "xz")
        self.plane_combo.addItem("Срез YZ", "yz")
        self.plane_combo.currentIndexChanged.connect(self._on_plane_changed)

        self.frame_slider = QSlider(Qt.Orientation.Horizontal)
        self.frame_slider.setMinimum(0)
        self.frame_slider.setMaximum(max(self.snapshot.frame_count() - 1, 0))
        self.frame_slider.valueChanged.connect(self._refresh_preview)
        self.frame_label = QLabel()

        self.slice_slider = QSlider(Qt.Orientation.Horizontal)
        self.slice_slider.setMinimum(0)
        self.slice_slider.valueChanged.connect(self._refresh_preview)
        self.slice_label = QLabel()

        self.iso_slider = QSlider(Qt.Orientation.Horizontal)
        self.iso_slider.setMinimum(5)
        self.iso_slider.setMaximum(95)
        self.iso_slider.setValue(58)
        self.iso_slider.valueChanged.connect(self._refresh_preview)
        self.iso_label = QLabel()

        self.play_button = QPushButton("Пуск")
        self.play_button.clicked.connect(self._toggle_play)
        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(self.accept)

        self.info_label = QLabel()
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(760, 560)
        self.image_label.setStyleSheet("background: #10151b; border: 1px solid #2e3c4a; border-radius: 10px;")

        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("Слой"))
        top_row.addWidget(self.layer_combo)
        top_row.addWidget(QLabel("Вид"))
        top_row.addWidget(self.render_combo)
        top_row.addWidget(QLabel("Плоскость"))
        top_row.addWidget(self.plane_combo)
        top_row.addStretch(1)
        top_row.addWidget(close_button)

        frame_row = QHBoxLayout()
        frame_row.addWidget(QLabel("Кадр"))
        frame_row.addWidget(self.frame_slider, stretch=1)
        frame_row.addWidget(self.frame_label)
        frame_row.addWidget(self.play_button)

        slice_row = QHBoxLayout()
        slice_row.addWidget(QLabel("Срез"))
        slice_row.addWidget(self.slice_slider, stretch=1)
        slice_row.addWidget(self.slice_label)

        iso_row = QHBoxLayout()
        iso_row.addWidget(QLabel("Изо-порог"))
        iso_row.addWidget(self.iso_slider, stretch=1)
        iso_row.addWidget(self.iso_label)

        layout = QVBoxLayout(self)
        layout.addLayout(top_row)
        layout.addLayout(frame_row)
        layout.addLayout(slice_row)
        layout.addLayout(iso_row)
        layout.addWidget(self.info_label)
        layout.addWidget(self.image_label, stretch=1)

        self._on_plane_changed()
        self._on_render_changed()

    def _current_plane(self) -> str:
        return str(self.plane_combo.currentData())

    def _current_render_mode(self) -> str:
        return str(self.render_combo.currentData())

    def _on_plane_changed(self) -> None:
        count = self.snapshot.slice_count(self._current_plane())
        self.slice_slider.setMaximum(max(count - 1, 0))
        self.slice_slider.setValue(count // 2)
        self._refresh_preview()

    def _on_render_changed(self) -> None:
        slice_mode = self._current_render_mode() == "slice"
        self.plane_combo.setEnabled(slice_mode)
        self.slice_slider.setEnabled(slice_mode)
        self.iso_slider.setEnabled(not slice_mode)
        self._refresh_preview()

    def _toggle_play(self) -> None:
        if self.play_timer.isActive():
            self.play_timer.stop()
            self.play_button.setText("Пуск")
            return
        self.play_timer.start(65)
        self.play_button.setText("Стоп")

    def _advance_frame(self) -> None:
        next_value = self.frame_slider.value() + 1
        if next_value > self.frame_slider.maximum():
            next_value = 0
        self.frame_slider.setValue(next_value)

    def _refresh_preview(self) -> None:
        layer = str(self.layer_combo.currentData())
        frame_index = int(self.frame_slider.value())
        render_mode = self._current_render_mode()
        plane = self._current_plane()
        slice_index = int(self.slice_slider.value())
        iso_ratio = float(self.iso_slider.value()) / 100.0
        if render_mode == "iso":
            image = self.snapshot.isosurface_to_image(layer=layer, frame_index=frame_index, iso_ratio=iso_ratio, scale=2)
        else:
            image = self.snapshot.slice_to_image(layer=layer, plane=plane, frame_index=frame_index, slice_index=slice_index, scale=3)
        values = self.snapshot.layer_frame(layer, frame_index)
        if ImageQt is None:
            self.info_label.setText("Pillow ImageQt недоступен, предпросмотр не может быть показан.")
            return
        pixmap = QPixmap.fromImage(ImageQt(image))
        scaled = pixmap.scaled(
            self.image_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.image_label.setPixmap(scaled)
        self.frame_label.setText(f"{frame_index + 1}/{self.snapshot.frame_count()}")
        self.slice_label.setText(f"{slice_index + 1}/{self.snapshot.slice_count(plane)}")
        self.iso_label.setText(f"{iso_ratio:.2f}")
        mode_label = "изоповерхность" if render_mode == "iso" else f"плоскость={PLANE_LABELS[plane]}"
        info = f"{LAYER_LABELS[layer]} | {mode_label} | min={float(values.min()):.5g} | max={float(values.max()):.5g}"
        info += f" | сетка={self.snapshot.metadata['grid_width']}x{self.snapshot.metadata['grid_height']}x{self.snapshot.metadata['grid_depth']}"
        info += f" | solver={self.snapshot.metadata['solver']}"
        info += f" | dt={float(self.snapshot.metadata['time_step_s']):.3e} c"
        note = str(self.snapshot.metadata.get("note", "")).strip()
        if note:
            info += f" | {note}"
        self.info_label.setText(info)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._refresh_preview()
