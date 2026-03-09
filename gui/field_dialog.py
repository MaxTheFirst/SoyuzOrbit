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

from core.field_solver import FieldSnapshot, FieldWaveSequence

try:
    from PIL.ImageQt import ImageQt
except Exception:  # noqa: BLE001
    ImageQt = None


LAYER_LABELS = {
    "potential": "Потенциал, В",
    "electric": "|E|, В/м",
    "magnetic": "|B|, Тл",
}


class FieldPreviewDialog(QDialog):
    def __init__(self, snapshot: FieldSnapshot | FieldWaveSequence, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.snapshot = snapshot
        self.is_sequence = isinstance(snapshot, FieldWaveSequence)
        self.setWindowTitle("Карта поля")
        self.resize(980, 760)
        self.play_timer = QTimer(self)
        self.play_timer.timeout.connect(self._advance_frame)

        self.layer_combo = QComboBox()
        self.layer_combo.addItem("Потенциал", "potential")
        self.layer_combo.addItem("Электрическое поле", "electric")
        self.layer_combo.addItem("Магнитное поле", "magnetic")
        self.layer_combo.currentIndexChanged.connect(self._refresh_preview)

        self.frame_slider = QSlider(Qt.Orientation.Horizontal)
        self.frame_slider.setMinimum(0)
        self.frame_slider.setMaximum(max(self._frame_count() - 1, 0))
        self.frame_slider.valueChanged.connect(self._refresh_preview)
        self.frame_label = QLabel()
        self.play_button = QPushButton("Пуск")
        self.play_button.clicked.connect(self._toggle_play)

        self.info_label = QLabel()
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(720, 520)
        self.image_label.setStyleSheet("background: #fffaf2; border: 1px solid #cfbfa8; border-radius: 10px;")

        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(self.accept)

        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("Слой"))
        top_row.addWidget(self.layer_combo)
        top_row.addStretch(1)
        top_row.addWidget(close_button)

        layout = QVBoxLayout(self)
        layout.addLayout(top_row)
        if self.is_sequence:
            sequence_row = QHBoxLayout()
            sequence_row.addWidget(QLabel("Кадр"))
            sequence_row.addWidget(self.frame_slider, stretch=1)
            sequence_row.addWidget(self.frame_label)
            sequence_row.addWidget(self.play_button)
            layout.addLayout(sequence_row)
        layout.addWidget(self.info_label)
        layout.addWidget(self.image_label, stretch=1)

        self._refresh_preview()

    def _frame_count(self) -> int:
        if isinstance(self.snapshot, FieldWaveSequence):
            return self.snapshot.frame_count()
        return 1

    def _current_frame(self) -> int:
        if not self.is_sequence:
            return 0
        return int(self.frame_slider.value())

    def _toggle_play(self) -> None:
        if not self.is_sequence:
            return
        if self.play_timer.isActive():
            self.play_timer.stop()
            self.play_button.setText("Пуск")
            return
        self.play_timer.start(65)
        self.play_button.setText("Стоп")

    def _advance_frame(self) -> None:
        if not self.is_sequence:
            return
        next_value = self.frame_slider.value() + 1
        if next_value > self.frame_slider.maximum():
            next_value = 0
        self.frame_slider.setValue(next_value)

    def _refresh_preview(self) -> None:
        layer = str(self.layer_combo.currentData())
        if self.is_sequence:
            image = self.snapshot.to_image(layer=layer, frame_index=self._current_frame(), scale=3)
            values = self.snapshot.layer_frame(layer, self._current_frame())
            self.frame_label.setText(f"{self._current_frame() + 1}/{self._frame_count()}")
        else:
            image = self.snapshot.to_image(layer=layer, scale=3)
            values = self.snapshot.layer(layer)
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
        info = f"{LAYER_LABELS[layer]} | min={float(values.min()):.5g} | max={float(values.max()):.5g} | "
        info += f"сетка={self.snapshot.metadata['grid_width']}x{self.snapshot.metadata['grid_height']}"
        if self.is_sequence and "time_step_s" in self.snapshot.metadata:
            info += f" | dt={float(self.snapshot.metadata['time_step_s']):.3e} c"
        self.info_label.setText(info)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._refresh_preview()
