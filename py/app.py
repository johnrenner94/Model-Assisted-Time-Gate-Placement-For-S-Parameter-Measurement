import numpy as np
import pyqtgraph as pg

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QFormLayout,
    QGroupBox,
    QLabel,
    QComboBox,
    QCheckBox,
    QDoubleSpinBox,
    QPushButton,
    QScrollArea,
)


DIRECTIONS = {
    "Forward": ("S11", "S21"),
    "Reverse": ("S22", "S12"),
}


COLOR_REFERENCE = "#4C9AFF"
COLOR_CALCULATED = "#FFB020"
COLOR_GATE = "#2ECC71"
COLOR_RESPONSE = "#DDDDDD"
COLOR_ORIGINAL = "#888888"
COLOR_GATED = "#2ECC71"
COLOR_WINDOW = "#AAAAAA"


class TimeGatingApp(QWidget):

    def __init__(
        self,
        analysis,
        model,
        report_start_ghz,
        report_stop_ghz,
    ):
        super().__init__()

        self.analysis = analysis
        self.model = model

        self.default_report_start_ghz = report_start_ghz
        self.default_report_stop_ghz = report_stop_ghz

        self.report_start_ghz = report_start_ghz
        self.report_stop_ghz = report_stop_ghz

        self.measured_start_ghz = float(
            self.analysis.frequency_ghz[0]
        )

        self.measured_stop_ghz = float(
            self.analysis.frequency_ghz[-1]
        )

        self._updating_controls = False

        self.setWindowTitle("VNA Time Gating")

        self.resize(1650, 950)

        self._build_pens()
        self._build_ui()
        self._connect_signals()

        self.refresh_all()

    # ==================================================================
    # Pens
    # ==================================================================

    def _build_pens(self):

        self.reference_pen = pg.mkPen(
            COLOR_REFERENCE,
            width=2,
            style=Qt.PenStyle.DashDotLine,
        )

        self.calculated_pen = pg.mkPen(
            COLOR_CALCULATED,
            width=2,
            style=Qt.PenStyle.DotLine,
        )

        self.gate_pen = pg.mkPen(
            COLOR_GATE,
            width=2,
            style=Qt.PenStyle.DashLine,
        )

        self.response_pen = pg.mkPen(
            COLOR_RESPONSE,
            width=1.5,
        )

        self.original_pen = pg.mkPen(
            COLOR_ORIGINAL,
            width=1.5,
        )

        self.gated_pen = pg.mkPen(
            COLOR_GATED,
            width=2,
        )

        self.window_pen = pg.mkPen(
            COLOR_WINDOW,
            width=1.5,
            style=Qt.PenStyle.DotLine,
        )

    # ==================================================================
    # UI
    # ==================================================================

    def _build_ui(self):

        main_layout = QHBoxLayout(self)

        # ==============================================================
        # Plot area
        # ==============================================================

        plot_widget = pg.GraphicsLayoutWidget()

        main_layout.addWidget(
            plot_widget,
            stretch=1,
        )

        # --------------------------------------------------------------
        # Reflection time response
        # --------------------------------------------------------------

        self.reflection_plot = plot_widget.addPlot(
            row=0,
            col=0,
            title="Reflection Time Response",
        )

        self.reflection_plot.setLabel(
            "bottom",
            "Time",
            units="ns",
        )

        self.reflection_plot.setLabel(
            "left",
            "|Response|",
        )

        self.reflection_plot.showGrid(
            x=True,
            y=True,
            alpha=0.2,
        )

        self.reflection_curve = (
            self.reflection_plot.plot(
                pen=self.response_pen,
            )
        )

        self.reflection_gate_shape_curve = (
            self.reflection_plot.plot(
                pen=self.window_pen,
            )
        )

        # --------------------------------------------------------------
        # Transmission time response
        # --------------------------------------------------------------

        self.transmission_time_plot = plot_widget.addPlot(
            row=0,
            col=1,
            title="Transmission Time Response",
        )

        self.transmission_time_plot.setLabel(
            "bottom",
            "Time",
            units="ns",
        )

        self.transmission_time_plot.setLabel(
            "left",
            "|Response|",
        )

        self.transmission_time_plot.showGrid(
            x=True,
            y=True,
            alpha=0.2,
        )

        self.transmission_time_curve = (
            self.transmission_time_plot.plot(
                pen=self.response_pen,
            )
        )

        self.transmission_gate_shape_curve = (
            self.transmission_time_plot.plot(
                pen=self.window_pen,
            )
        )

        # --------------------------------------------------------------
        # VSWR
        # --------------------------------------------------------------

        self.vswr_plot = plot_widget.addPlot(
            row=1,
            col=0,
            title="Reflection VSWR",
        )

        self.vswr_plot.setLabel(
            "bottom",
            "Frequency",
            units="GHz",
        )

        self.vswr_plot.setLabel(
            "left",
            "VSWR",
        )

        self.vswr_plot.showGrid(
            x=True,
            y=True,
            alpha=0.2,
        )

        self.original_vswr_curve = (
            self.vswr_plot.plot(
                pen=self.original_pen,
                name="Original",
            )
        )

        self.gated_vswr_curve = (
            self.vswr_plot.plot(
                pen=self.gated_pen,
                name="Gated",
            )
        )

        self.vswr_plot.addLegend()

        # --------------------------------------------------------------
        # Transmission magnitude
        # --------------------------------------------------------------

        self.transmission_plot = plot_widget.addPlot(
            row=1,
            col=1,
            title="Transmission",
        )

        self.transmission_plot.setLabel(
            "bottom",
            "Frequency",
            units="GHz",
        )

        self.transmission_plot.setLabel(
            "left",
            "Magnitude",
            units="dB",
        )

        self.transmission_plot.showGrid(
            x=True,
            y=True,
            alpha=0.2,
        )

        self.original_transmission_curve = (
            self.transmission_plot.plot(
                pen=self.original_pen,
                name="Original",
            )
        )

        self.gated_transmission_curve = (
            self.transmission_plot.plot(
                pen=self.gated_pen,
                name="Gated",
            )
        )

        self.transmission_plot.addLegend()

        # ==============================================================
        # Reflection markers
        # ==============================================================

        self.near_rp_line = self._make_fixed_line(
            self.reflection_plot,
            self.reference_pen,
            COLOR_REFERENCE,
            position=0.96,
        )

        self.far_rp_line = self._make_fixed_line(
            self.reflection_plot,
            self.reference_pen,
            COLOR_REFERENCE,
            position=0.96,
        )

        self.dut_start_line = self._make_fixed_line(
            self.reflection_plot,
            self.calculated_pen,
            COLOR_CALCULATED,
            position=0.63,
        )

        self.dut_stop_line = self._make_fixed_line(
            self.reflection_plot,
            self.calculated_pen,
            COLOR_CALCULATED,
            position=0.63,
        )

        self.gate_start_line = self._make_movable_line(
            self.reflection_plot,
            self.gate_pen,
            COLOR_GATE,
            position=0.29,
        )

        self.gate_stop_line = self._make_movable_line(
            self.reflection_plot,
            self.gate_pen,
            COLOR_GATE,
            position=0.29,
        )

        # ==============================================================
        # Transmission markers
        # ==============================================================

        self.tx_gate_start_line = self._make_movable_line(
            self.transmission_time_plot,
            self.gate_pen,
            COLOR_GATE,
            position=0.90,
        )

        self.tx_gate_stop_line = self._make_movable_line(
            self.transmission_time_plot,
            self.gate_pen,
            COLOR_GATE,
            position=0.70,
        )

        # ==============================================================
        # Scrollable side panel
        # ==============================================================

        side_panel = QWidget()

        side_layout = QVBoxLayout(side_panel)

        side_layout.setContentsMargins(
            8,
            8,
            8,
            8,
        )

        side_panel.setMinimumWidth(460)
        side_panel.setMaximumWidth(560)

        side_scroll = QScrollArea()

        side_scroll.setWidgetResizable(True)

        side_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        side_scroll.setWidget(side_panel)

        side_scroll.setMinimumWidth(480)
        side_scroll.setMaximumWidth(580)

        main_layout.addWidget(side_scroll)

        # --------------------------------------------------------------
        # Measurement inputs
        # --------------------------------------------------------------

        measurement_group = QGroupBox(
            "Measurement Inputs"
        )

        measurement_form = QFormLayout(
            measurement_group
        )

        self.direction_combo = QComboBox()

        self.direction_combo.addItems(
            DIRECTIONS.keys()
        )

        measurement_form.addRow(
            "Direction:",
            self.direction_combo,
        )

        self.adapters_checkbox = QCheckBox()

        self.adapters_checkbox.setChecked(
            self.model.adapters
        )

        measurement_form.addRow(
            "Adapters present:",
            self.adapters_checkbox,
        )

        self.length_spin = QDoubleSpinBox()

        self.length_spin.setRange(
            0.001,
            10000.0,
        )

        self.length_spin.setDecimals(4)

        self.length_spin.setSuffix(" in")

        self.length_spin.setValue(
            self.model.dut.length_in
        )

        self.length_spin.setKeyboardTracking(
            False
        )

        measurement_form.addRow(
            "DUT length:",
            self.length_spin,
        )

        self.vf_spin = QDoubleSpinBox()

        self.vf_spin.setRange(
            0.01,
            1.0,
        )

        self.vf_spin.setDecimals(5)

        self.vf_spin.setSingleStep(
            0.001
        )

        self.vf_spin.setValue(
            self.model.dut.velocity_factor
        )

        self.vf_spin.setKeyboardTracking(
            False
        )

        measurement_form.addRow(
            "Velocity factor:",
            self.vf_spin,
        )

        self.window_combo = QComboBox()

        self.window_combo.addItem(
            "Boxcar",
            "boxcar",
        )

        self.window_combo.addItem(
            "Kaiser (β = 6)",
            "kaiser",
        )

        self.window_combo.setCurrentIndex(0)

        measurement_form.addRow(
            "Gate window:",
            self.window_combo,
        )

        side_layout.addWidget(
            measurement_group
        )

        # --------------------------------------------------------------
        # Frequency range
        # --------------------------------------------------------------

        frequency_group = QGroupBox(
            "Frequency Range"
        )

        frequency_form = QFormLayout(
            frequency_group
        )

        self.measured_range_label = QLabel(
            (
                f"{self.measured_start_ghz:.4f} – "
                f"{self.measured_stop_ghz:.4f} GHz"
            )
        )

        frequency_form.addRow(
            "Measured:",
            self.measured_range_label,
        )

        self.report_min_spin = (
            self._make_frequency_spinbox()
        )

        self.report_max_spin = (
            self._make_frequency_spinbox()
        )

        self.report_min_spin.setValue(
            self.report_start_ghz
        )

        self.report_max_spin.setValue(
            self.report_stop_ghz
        )

        frequency_form.addRow(
            "Report min:",
            self.report_min_spin,
        )

        frequency_form.addRow(
            "Report max:",
            self.report_max_spin,
        )

        self.lower_guard_label = QLabel()
        self.upper_guard_label = QLabel()

        frequency_form.addRow(
            "Lower guard:",
            self.lower_guard_label,
        )

        frequency_form.addRow(
            "Upper guard:",
            self.upper_guard_label,
        )

        self.full_range_button = QPushButton(
            "Use Full Measured Range"
        )

        self.reset_report_button = QPushButton(
            "Reset Report Range"
        )

        frequency_form.addRow(
            self.full_range_button
        )

        frequency_form.addRow(
            self.reset_report_button
        )

        side_layout.addWidget(
            frequency_group
        )

        # --------------------------------------------------------------
        # Reflection gate
        # --------------------------------------------------------------

        reflection_gate_group = QGroupBox(
            "Reflection Gate"
        )

        reflection_gate_form = QFormLayout(
            reflection_gate_group
        )

        self.gate_start_spin = (
            self._make_time_spinbox()
        )

        self.gate_stop_spin = (
            self._make_time_spinbox()
        )

        reflection_gate_form.addRow(
            "Start:",
            self.gate_start_spin,
        )

        reflection_gate_form.addRow(
            "Stop:",
            self.gate_stop_spin,
        )

        side_layout.addWidget(
            reflection_gate_group
        )

        # --------------------------------------------------------------
        # Transmission gate
        # --------------------------------------------------------------

        transmission_gate_group = QGroupBox(
            "Transmission Gate"
        )

        transmission_gate_form = QFormLayout(
            transmission_gate_group
        )

        self.tx_gate_start_spin = (
            self._make_time_spinbox()
        )

        self.tx_gate_stop_spin = (
            self._make_time_spinbox()
        )

        transmission_gate_form.addRow(
            "Start:",
            self.tx_gate_start_spin,
        )

        transmission_gate_form.addRow(
            "Stop:",
            self.tx_gate_stop_spin,
        )

        side_layout.addWidget(
            transmission_gate_group
        )

        # --------------------------------------------------------------
        # Reset gate
        # --------------------------------------------------------------

        self.reset_button = QPushButton(
            "Reset to Default"
        )

        side_layout.addWidget(
            self.reset_button
        )

        # --------------------------------------------------------------
        # DUT / gate readout
        # --------------------------------------------------------------

        readout_group = QGroupBox(
            "DUT / Gate Readout"
        )

        readout_form = QFormLayout(
            readout_group
        )

        self.expected_delay_label = QLabel()
        self.rp_delay_label = QLabel()
        self.rp_length_label = QLabel()
        self.calculated_start_label = QLabel()
        self.calculated_stop_label = QLabel()
        self.selected_delay_label = QLabel()
        self.selected_length_label = QLabel()
        self.length_difference_label = QLabel()

        readout_form.addRow(
            "Expected DUT delay:",
            self.expected_delay_label,
        )

        readout_form.addRow(
            "Measured RP-RP delay:",
            self.rp_delay_label,
        )

        readout_form.addRow(
            "RP-RP equiv. length:",
            self.rp_length_label,
        )

        readout_form.addRow(
            "Calculated DUT start:",
            self.calculated_start_label,
        )

        readout_form.addRow(
            "Calculated DUT stop:",
            self.calculated_stop_label,
        )

        readout_form.addRow(
            "Selected DUT delay:",
            self.selected_delay_label,
        )

        readout_form.addRow(
            "Selected equiv. length:",
            self.selected_length_label,
        )

        readout_form.addRow(
            "Difference from known:",
            self.length_difference_label,
        )

        side_layout.addWidget(
            readout_group
        )

        # --------------------------------------------------------------
        # Measurement data
        # --------------------------------------------------------------

        data_group = QGroupBox(
            "Measurement Data"
        )

        data_form = QFormLayout(
            data_group
        )

        self.file_label = QLabel(
            str(self.analysis.file)
        )

        self.file_label.setWordWrap(True)

        self.df_label = QLabel(
            f"{self.analysis.frequency_step_hz / 1e6:.3f} MHz"
        )

        self.point_count_label = QLabel(
            str(len(self.analysis.frequency_hz))
        )

        self.time_window_label = QLabel(
            f"{self.analysis.time_window_ns:.4f} ns"
        )

        self.time_resolution_label = QLabel(
            f"{self.analysis.time_resolution_ns:.4f} ns"
        )

        self.s21_delay_label = QLabel(
            f"{self.analysis.s21_delay_ns:.4f} ns"
        )

        self.s12_delay_label = QLabel(
            f"{self.analysis.s12_delay_ns:.4f} ns"
        )

        self.time_axis_label = QLabel(
            (
                f"{self.analysis.time_axis_start_ns:.4f} "
                f"to "
                f"{self.analysis.time_axis_stop_ns:.4f} ns"
            )
        )

        self.time_axis_label.setWordWrap(True)

        data_form.addRow(
            "File:",
            self.file_label,
        )

        data_form.addRow(
            "Points:",
            self.point_count_label,
        )

        data_form.addRow(
            "Frequency step:",
            self.df_label,
        )

        data_form.addRow(
            "Nominal time window:",
            self.time_window_label,
        )

        data_form.addRow(
            "Time resolution:",
            self.time_resolution_label,
        )

        data_form.addRow(
            "Displayed time axis:",
            self.time_axis_label,
        )

        data_form.addRow(
            "S21 peak:",
            self.s21_delay_label,
        )

        data_form.addRow(
            "S12 peak:",
            self.s12_delay_label,
        )

        side_layout.addWidget(
            data_group
        )

        side_layout.addStretch()

    # ==================================================================
    # Widget helpers
    # ==================================================================

    def _make_time_spinbox(self):

        spin = QDoubleSpinBox()

        spin.setRange(
            -1000.0,
            1000.0,
        )

        spin.setDecimals(4)

        spin.setSingleStep(
            0.01
        )

        spin.setSuffix(
            " ns"
        )

        spin.setKeyboardTracking(
            False
        )

        return spin

    def _make_frequency_spinbox(self):

        spin = QDoubleSpinBox()

        spin.setRange(
            self.measured_start_ghz,
            self.measured_stop_ghz,
        )

        spin.setDecimals(4)

        spin.setSingleStep(
            self.analysis.frequency_step_hz / 1e9
        )

        spin.setSuffix(
            " GHz"
        )

        spin.setKeyboardTracking(
            False
        )

        return spin

    def _make_fixed_line(
        self,
        plot,
        pen,
        color,
        position,
    ):

        line = pg.InfiniteLine(
            angle=90,
            movable=False,
            pen=pen,
        )

        plot.addItem(line)

        label = pg.InfLineLabel(
            line,
            text="",
            position=position,
            color=color,
            movable=False,
        )

        line.custom_label = label

        return line

    def _make_movable_line(
        self,
        plot,
        pen,
        color,
        position,
    ):

        line = pg.InfiniteLine(
            angle=90,
            movable=True,
            pen=pen,
            hoverPen=pg.mkPen(
                color,
                width=4,
            ),
        )

        plot.addItem(line)

        label = pg.InfLineLabel(
            line,
            text="",
            position=position,
            color=color,
            movable=False,
        )

        line.custom_label = label

        return line

    # ==================================================================
    # Signals
    # ==================================================================

    def _connect_signals(self):

        self.direction_combo.currentTextChanged.connect(
            self._on_direction_changed
        )

        self.adapters_checkbox.toggled.connect(
            self._on_adapters_changed
        )

        self.length_spin.valueChanged.connect(
            self._on_length_changed
        )

        self.vf_spin.valueChanged.connect(
            self._on_vf_changed
        )

        self.window_combo.currentIndexChanged.connect(
            self._on_window_changed
        )

        self.report_min_spin.valueChanged.connect(
            self._on_report_range_changed
        )

        self.report_max_spin.valueChanged.connect(
            self._on_report_range_changed
        )

        self.full_range_button.clicked.connect(
            self._on_full_frequency_range
        )

        self.reset_report_button.clicked.connect(
            self._on_reset_report_range
        )

        self.reset_button.clicked.connect(
            self._on_reset
        )

        self.gate_start_spin.valueChanged.connect(
            self._on_reflection_spin_changed
        )

        self.gate_stop_spin.valueChanged.connect(
            self._on_reflection_spin_changed
        )

        self.tx_gate_start_spin.valueChanged.connect(
            self._on_transmission_spin_changed
        )

        self.tx_gate_stop_spin.valueChanged.connect(
            self._on_transmission_spin_changed
        )

        self.gate_start_line.sigPositionChanged.connect(
            self._on_reflection_dragged
        )

        self.gate_stop_line.sigPositionChanged.connect(
            self._on_reflection_dragged
        )

        self.gate_start_line.sigPositionChangeFinished.connect(
            self._on_reflection_drag_finished
        )

        self.gate_stop_line.sigPositionChangeFinished.connect(
            self._on_reflection_drag_finished
        )

        self.tx_gate_start_line.sigPositionChanged.connect(
            self._on_transmission_dragged
        )

        self.tx_gate_stop_line.sigPositionChanged.connect(
            self._on_transmission_dragged
        )

        self.tx_gate_start_line.sigPositionChangeFinished.connect(
            self._on_transmission_drag_finished
        )

        self.tx_gate_stop_line.sigPositionChangeFinished.connect(
            self._on_transmission_drag_finished
        )

    # ==================================================================
    # Input callbacks
    # ==================================================================

    def _on_direction_changed(self):

        if self._updating_controls:
            return

        self.refresh_all()

    def _on_adapters_changed(
        self,
        checked,
    ):

        if self._updating_controls:
            return

        self.model.set_adapters(
            checked
        )

        self.refresh_geometry()

    def _on_length_changed(
        self,
        value,
    ):

        if self._updating_controls:
            return

        self.model.set_dut_length(
            value
        )

        self.refresh_geometry()

    def _on_vf_changed(
        self,
        value,
    ):

        if self._updating_controls:
            return

        self.model.set_velocity_factor(
            value
        )

        self.refresh_geometry()

    def _on_window_changed(self):

        if self._updating_controls:
            return

        self.refresh_gate_shapes()
        self.refresh_frequency_plots()

    def _on_report_range_changed(self):

        if self._updating_controls:
            return

        start = (
            self.report_min_spin.value()
        )

        stop = (
            self.report_max_spin.value()
        )

        if stop <= start:
            return

        self.report_start_ghz = start
        self.report_stop_ghz = stop

        self.refresh_frequency_range_readout()
        self.refresh_frequency_plots()

    def _on_full_frequency_range(self):

        self.report_start_ghz = (
            self.measured_start_ghz
        )

        self.report_stop_ghz = (
            self.measured_stop_ghz
        )

        self._update_frequency_spinboxes()

        self.refresh_frequency_range_readout()
        self.refresh_frequency_plots()

    def _on_reset_report_range(self):

        start = max(
            self.measured_start_ghz,
            self.default_report_start_ghz,
        )

        stop = min(
            self.measured_stop_ghz,
            self.default_report_stop_ghz,
        )

        self.report_start_ghz = start
        self.report_stop_ghz = stop

        self._update_frequency_spinboxes()

        self.refresh_frequency_range_readout()
        self.refresh_frequency_plots()

    def _on_reset(self):

        self.model.reset_to_default()

        self.refresh_all()

    # ==================================================================
    # Reflection gate callbacks
    # ==================================================================

    def _on_reflection_spin_changed(self):

        if self._updating_controls:
            return

        direction = (
            self.direction_combo.currentText()
        )

        start = (
            self.gate_start_spin.value()
        )

        stop = (
            self.gate_stop_spin.value()
        )

        if not self._valid_gate(
            start,
            stop,
        ):
            return

        self.model.set_gate(
            direction,
            start,
            stop,
        )

        self.refresh_all()

    def _on_reflection_dragged(self):

        if self._updating_controls:
            return

        direction = (
            self.direction_combo.currentText()
        )

        start = float(
            self.gate_start_line.value()
        )

        stop = float(
            self.gate_stop_line.value()
        )

        if not self._valid_gate(
            start,
            stop,
        ):
            return

        self.model.set_gate(
            direction,
            start,
            stop,
        )

        self.refresh_gate_readout()
        self.refresh_gate_shapes()

    def _on_reflection_drag_finished(self):

        self.refresh_frequency_plots()

    # ==================================================================
    # Transmission gate callbacks
    # ==================================================================

    def _on_transmission_spin_changed(self):

        if self._updating_controls:
            return

        start = (
            self.tx_gate_start_spin.value()
        )

        stop = (
            self.tx_gate_stop_spin.value()
        )

        if not self._valid_gate(
            start,
            stop,
        ):
            return

        self.model.transmission_gate.start = start
        self.model.transmission_gate.stop = stop

        self.refresh_all()

    def _on_transmission_dragged(self):

        if self._updating_controls:
            return

        start = float(
            self.tx_gate_start_line.value()
        )

        stop = float(
            self.tx_gate_stop_line.value()
        )

        if not self._valid_gate(
            start,
            stop,
        ):
            return

        self.model.transmission_gate.start = start
        self.model.transmission_gate.stop = stop

        self.refresh_gate_readout()
        self.refresh_gate_shapes()

    def _on_transmission_drag_finished(self):

        self.refresh_frequency_plots()

    # ==================================================================
    # Validation
    # ==================================================================

    def _valid_gate(
        self,
        start,
        stop,
    ):

        return (
            stop - start
            >= self.analysis.time_resolution_ns
        )

    # ==================================================================
    # Refresh
    # ==================================================================

    def refresh_time_plots(self):

        direction = (
            self.direction_combo.currentText()
        )

        reflection_name, transmission_name = (
            DIRECTIONS[direction]
        )

        time_ns, response = (
            self.analysis.time(
                reflection_name
            )
        )

        self.reflection_curve.setData(
            time_ns,
            response,
        )

        self.reflection_plot.setTitle(
            f"{reflection_name} Reflection Time Response"
        )

        time_ns_tx, response_tx = (
            self.analysis.time(
                transmission_name
            )
        )

        self.transmission_time_curve.setData(
            time_ns_tx,
            response_tx,
        )

        self.transmission_time_plot.setTitle(
            f"{transmission_name} Transmission Time Response"
        )

        self.refresh_gate_shapes()

    def refresh_gate_shapes(self):

        direction = (
            self.direction_combo.currentText()
        )

        reflection_name, transmission_name = (
            DIRECTIONS[direction]
        )

        gate_window = (
            self.window_combo.currentData()
        )

        # --------------------------------------------------------------
        # Reflection
        # --------------------------------------------------------------

        reflection_gate = (
            self.model.gate_for(
                direction
            )
        )

        gate_time, gate_shape = (
            self.analysis.gate_shape(
                reflection_gate.start,
                reflection_gate.stop,
                gate_window,
            )
        )

        _, reflection_response = (
            self.analysis.time(
                reflection_name
            )
        )

        reflection_scale = (
            np.max(reflection_response)
            if len(reflection_response)
            else 1.0
        )

        self.reflection_gate_shape_curve.setData(
            gate_time,
            gate_shape * reflection_scale,
        )

        # --------------------------------------------------------------
        # Transmission
        # --------------------------------------------------------------

        tx_gate = (
            self.model.transmission_gate
        )

        tx_gate_time, tx_gate_shape = (
            self.analysis.gate_shape(
                tx_gate.start,
                tx_gate.stop,
                gate_window,
            )
        )

        _, transmission_response = (
            self.analysis.time(
                transmission_name
            )
        )

        transmission_scale = (
            np.max(transmission_response)
            if len(transmission_response)
            else 1.0
        )

        self.transmission_gate_shape_curve.setData(
            tx_gate_time,
            tx_gate_shape * transmission_scale,
        )

    def refresh_geometry(self):

        direction = (
            self.direction_combo.currentText()
        )

        reference_start, reference_stop = (
            self.model.reference_planes
        )

        calculated_gate = (
            self.model.calculated_gate_for(
                direction
            )
        )

        actual_gate = (
            self.model.gate_for(
                direction
            )
        )

        tx_gate = (
            self.model.transmission_gate
        )

        self._updating_controls = True

        try:

            self.near_rp_line.setValue(
                reference_start
            )

            self.far_rp_line.setValue(
                reference_stop
            )

            self._set_line_label(
                self.near_rp_line,
                "Near RP",
                reference_start,
            )

            self._set_line_label(
                self.far_rp_line,
                "Far RP",
                reference_stop,
            )

            self.dut_start_line.setValue(
                calculated_gate.start
            )

            self.dut_stop_line.setValue(
                calculated_gate.stop
            )

            self._set_line_label(
                self.dut_start_line,
                "DUT Start",
                calculated_gate.start,
            )

            self._set_line_label(
                self.dut_stop_line,
                "DUT Stop",
                calculated_gate.stop,
            )

            self.gate_start_line.setValue(
                actual_gate.start
            )

            self.gate_stop_line.setValue(
                actual_gate.stop
            )

            self._set_line_label(
                self.gate_start_line,
                "Gate Start",
                actual_gate.start,
            )

            self._set_line_label(
                self.gate_stop_line,
                "Gate Stop",
                actual_gate.stop,
            )

            self.gate_start_spin.setValue(
                actual_gate.start
            )

            self.gate_stop_spin.setValue(
                actual_gate.stop
            )

            self.tx_gate_start_line.setValue(
                tx_gate.start
            )

            self.tx_gate_stop_line.setValue(
                tx_gate.stop
            )

            self._set_line_label(
                self.tx_gate_start_line,
                "TX Gate Start",
                tx_gate.start,
            )

            self._set_line_label(
                self.tx_gate_stop_line,
                "TX Gate Stop",
                tx_gate.stop,
            )

            self.tx_gate_start_spin.setValue(
                tx_gate.start
            )

            self.tx_gate_stop_spin.setValue(
                tx_gate.stop
            )

        finally:

            self._updating_controls = False

        self.refresh_gate_readout()
        self.refresh_gate_shapes()

    def refresh_gate_readout(self):

        direction = (
            self.direction_combo.currentText()
        )

        calculated_gate = (
            self.model.calculated_gate_for(
                direction
            )
        )

        actual_gate = (
            self.model.gate_for(
                direction
            )
        )

        self.expected_delay_label.setText(
            f"{self.model.expected_delay_ns:.4f} ns"
        )

        self.rp_delay_label.setText(
            f"{self.model.rp_delay_ns:.4f} ns"
        )

        self.rp_length_label.setText(
            f"{self.model.rp_equivalent_length_in:.4f} in"
        )

        self.calculated_start_label.setText(
            f"{calculated_gate.start:.4f} ns"
        )

        self.calculated_stop_label.setText(
            f"{calculated_gate.stop:.4f} ns"
        )

        self.selected_delay_label.setText(
            f"{self.model.selected_delay_ns:.4f} ns"
        )

        self.selected_length_label.setText(
            f"{self.model.selected_length_in:.4f} in"
        )

        difference = (
            self.model.length_difference_in
        )

        self.length_difference_label.setText(
            f"{difference:+.4f} in"
        )

        self._updating_controls = True

        try:

            self.gate_start_spin.setValue(
                actual_gate.start
            )

            self.gate_stop_spin.setValue(
                actual_gate.stop
            )

            self.tx_gate_start_spin.setValue(
                self.model.transmission_gate.start
            )

            self.tx_gate_stop_spin.setValue(
                self.model.transmission_gate.stop
            )

        finally:

            self._updating_controls = False

        self._set_line_label(
            self.gate_start_line,
            "Gate Start",
            actual_gate.start,
        )

        self._set_line_label(
            self.gate_stop_line,
            "Gate Stop",
            actual_gate.stop,
        )

        self._set_line_label(
            self.tx_gate_start_line,
            "TX Gate Start",
            self.model.transmission_gate.start,
        )

        self._set_line_label(
            self.tx_gate_stop_line,
            "TX Gate Stop",
            self.model.transmission_gate.stop,
        )

    def refresh_frequency_range_readout(self):

        lower_guard = (
            self.report_start_ghz
            - self.measured_start_ghz
        )

        upper_guard = (
            self.measured_stop_ghz
            - self.report_stop_ghz
        )

        self.lower_guard_label.setText(
            f"{lower_guard:.4f} GHz"
        )

        self.upper_guard_label.setText(
            f"{upper_guard:.4f} GHz"
        )

    def refresh_frequency_plots(self):

        direction = (
            self.direction_combo.currentText()
        )

        reflection_name, transmission_name = (
            DIRECTIONS[direction]
        )

        reflection_gate = (
            self.model.gate_for(
                direction
            )
        )

        transmission_gate = (
            self.model.transmission_gate
        )

        gate_window = (
            self.window_combo.currentData()
        )

        # --------------------------------------------------------------
        # Reflection / VSWR
        # --------------------------------------------------------------

        original_vswr = (
            self.analysis.original_vswr(
                reflection_name
            )
        )

        gated_vswr = (
            self.analysis.gated_vswr(
                reflection_name,
                reflection_gate.start,
                reflection_gate.stop,
                gate_window=gate_window,
            )
        )

        self.original_vswr_curve.setData(
            self.analysis.frequency_ghz,
            original_vswr,
        )

        self.gated_vswr_curve.setData(
            self.analysis.frequency_ghz,
            gated_vswr,
        )

        self.vswr_plot.setTitle(
            (
                f"{reflection_name} VSWR "
                f"— {self.window_combo.currentText()} Gate"
            )
        )

        # --------------------------------------------------------------
        # Transmission
        # --------------------------------------------------------------

        original_db = (
            self.analysis.original_db(
                transmission_name
            )
        )

        gated_db = (
            self.analysis.gated_db(
                transmission_name,
                transmission_gate.start,
                transmission_gate.stop,
                gate_window=gate_window,
            )
        )

        self.original_transmission_curve.setData(
            self.analysis.frequency_ghz,
            original_db,
        )

        self.gated_transmission_curve.setData(
            self.analysis.frequency_ghz,
            gated_db,
        )

        self.transmission_plot.setTitle(
            (
                f"{transmission_name} Transmission "
                f"— {self.window_combo.currentText()} Gate"
            )
        )

        # --------------------------------------------------------------
        # Display/report range only.
        #
        # The underlying time-gating calculation still uses the full
        # measured frequency sweep.
        # --------------------------------------------------------------

        self.vswr_plot.setXRange(
            self.report_start_ghz,
            self.report_stop_ghz,
            padding=0,
        )

        self.transmission_plot.setXRange(
            self.report_start_ghz,
            self.report_stop_ghz,
            padding=0,
        )

        self.refresh_frequency_range_readout()

    def refresh_all(self):

        self.refresh_time_plots()
        self.refresh_geometry()
        self.refresh_frequency_range_readout()
        self.refresh_frequency_plots()

    # ==================================================================
    # Frequency controls
    # ==================================================================

    def _update_frequency_spinboxes(self):

        self._updating_controls = True

        try:

            self.report_min_spin.setValue(
                self.report_start_ghz
            )

            self.report_max_spin.setValue(
                self.report_stop_ghz
            )

        finally:

            self._updating_controls = False

    # ==================================================================
    # Label helper
    # ==================================================================

    @staticmethod
    def _set_line_label(
        line,
        descriptor,
        value,
    ):

        line.custom_label.setText(
            f"{descriptor}\n{value:.4f} ns"
        )