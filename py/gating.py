from dataclasses import dataclass


C = 299_792_458
INCH = 0.0254


# ============================================================
# BASIC OBJECTS
# ============================================================

@dataclass
class Gate:
    start: float
    stop: float

    @property
    def width(self):
        return self.stop - self.start

    @property
    def center(self):
        return (self.start + self.stop) / 2


@dataclass
class DUT:
    length_in: float
    velocity_factor: float

    @property
    def delay_ns(self):
        """
        Expected one-way electrical delay through the DUT
        based on physical length and velocity factor.
        """

        length_m = self.length_in * INCH

        return (
            length_m
            / (self.velocity_factor * C)
            * 1e9
        )


# ============================================================
# CONVERSIONS
# ============================================================

def delay_to_length_in(delay_ns, velocity_factor):
    """
    Convert one-way electrical delay to equivalent physical
    length using the supplied velocity factor.
    """

    return (
        delay_ns
        * 1e-9
        * velocity_factor
        * C
        / INCH
    )


# ============================================================
# GATE MODEL
# ============================================================

class GateModel:

    def __init__(
        self,
        dut,
        rp_delay_ns,
        adapters=False,
    ):

        self.dut = dut
        self.rp_delay_ns = rp_delay_ns
        self.adapters = adapters

        # Geometry-based calculated DUT boundaries.
        self.calculated_gate = None

        # Actual operator-selected reflection gate.
        #
        # Stored internally in Forward / S11 coordinates.
        self.gate = None

        # Actual operator-selected transmission gate.
        self.transmission_gate = None

        self.reset_to_default()


    # ========================================================
    # REFERENCE PLANES
    # ========================================================

    @property
    def reflection_span_ns(self):
        """
        Reflection-domain separation between the two
        calibration reference planes.

        Transmission delay is one-way.
        Reflection delay is round-trip.
        """

        return 2 * self.rp_delay_ns


    @property
    def reference_planes(self):
        """
        Reflection-domain coordinates of the calibration
        reference planes.
        """

        return (
            0.0,
            self.reflection_span_ns,
        )


    # ========================================================
    # CALCULATED DUT POSITION
    # ========================================================

    def calculate_default_gate(self):
        """
        Calculate expected DUT boundaries from known geometry.

        This calculation deliberately does not inspect the
        measured reflection peaks.
        """

        dut_reflection_width = (
            2 * self.dut.delay_ns
        )


        # ----------------------------------------------------
        # NO ADAPTERS
        #
        # DUT begins at the near calibration reference plane.
        #
        # Entered DUT length and VF predict where the far DUT
        # boundary should occur.
        # ----------------------------------------------------

        if not self.adapters:

            return Gate(
                0.0,
                dut_reflection_width,
            )


        # ----------------------------------------------------
        # ADAPTERS PRESENT
        #
        # Total measured one-way delay:
        #
        #     adapter A + DUT + adapter B
        #
        # DUT delay comes from entered physical length and VF.
        #
        # Without individual adapter delays, the remaining
        # delay is initially split equally between both ends.
        # ----------------------------------------------------

        extra_delay = (
            self.rp_delay_ns
            - self.dut.delay_ns
        )

        adapter_delay = (
            extra_delay / 2
        )

        start = (
            2 * adapter_delay
        )

        stop = (
            start
            + dut_reflection_width
        )

        return Gate(
            start,
            stop,
        )


    # ========================================================
    # AUTOMATIC RECALCULATION
    # ========================================================

    def recalculate(self):
        """
        Recalculate all geometry-derived DUT information.

        This does NOT move operator-selected gates.
        """

        self.calculated_gate = (
            self.calculate_default_gate()
        )


    # ========================================================
    # RESET TO DEFAULT
    # ========================================================

    def reset_to_default(self):
        """
        Restore operator-adjustable gates to their default
        positions using the CURRENT inputs.

        Reflection gate:
            Calculated DUT boundaries.

        Transmission gate:
            Window centered around measured transmission delay.
        """

        self.recalculate()


        # Reflection gate defaults to calculated DUT region.
        self.gate = Gate(
            self.calculated_gate.start,
            self.calculated_gate.stop,
        )


        # Transmission gate defaults around measured
        # one-way transmission delay.
        self.transmission_gate = Gate(
            self.rp_delay_ns - 0.20,
            self.rp_delay_ns + 0.20,
        )


    # ========================================================
    # PHYSICAL INPUT CHANGES
    # ========================================================

    def set_velocity_factor(self, value):
        """
        Recalculate geometry when VF changes.

        Manual gate selection remains untouched.
        """

        self.dut.velocity_factor = value

        self.recalculate()


    def set_dut_length(self, value):
        """
        Recalculate geometry when DUT length changes.

        Manual gate selection remains untouched.
        """

        self.dut.length_in = value

        self.recalculate()


    def set_adapters(self, present):
        """
        Recalculate geometry when adapter configuration
        changes.

        Manual gate selection remains untouched.
        """

        self.adapters = present

        self.recalculate()


    # ========================================================
    # FORWARD / REVERSE REFLECTION MAPPING
    # ========================================================

    def _mirror(self, gate):
        """
        Mirror a reflection-domain interval between S11 and
        S22 coordinates.

        If total one-way reference-plane delay is T:

            t_reverse = 2T - t_forward
        """

        span = self.reflection_span_ns

        return Gate(
            span - gate.stop,
            span - gate.start,
        )


    def gate_for(self, direction):
        """
        Return actual reflection gate in selected direction.
        """

        if direction == "Forward":
            return self.gate

        return self._mirror(
            self.gate
        )


    def calculated_gate_for(self, direction):
        """
        Return calculated DUT boundaries in selected
        direction.
        """

        if direction == "Forward":
            return self.calculated_gate

        return self._mirror(
            self.calculated_gate
        )


    # ========================================================
    # ACTUAL REFLECTION GATE
    # ========================================================

    def set_gate(
        self,
        direction,
        start,
        stop,
    ):
        """
        Set the operator-selected physical reflection gate.

        Internally the gate is always stored in Forward/S11
        coordinates.

        Editing the gate while viewing Reverse/S22 therefore
        updates the same physical gate.
        """

        new_gate = Gate(
            start,
            stop,
        )

        if direction == "Forward":

            self.gate = new_gate

        else:

            self.gate = self._mirror(
                new_gate
            )


    # ========================================================
    # SELECTED GATE MEASUREMENTS
    # ========================================================

    @property
    def selected_delay_ns(self):
        """
        One-way delay implied by selected reflection gate.
        """

        return (
            self.gate.width / 2
        )


    @property
    def selected_length_in(self):
        """
        Equivalent physical length implied by selected gate
        using current DUT velocity factor.
        """

        return delay_to_length_in(
            self.selected_delay_ns,
            self.dut.velocity_factor,
        )


    @property
    def length_difference_in(self):
        """
        Difference between gate-implied equivalent length and
        entered known DUT physical length.
        """

        return (
            self.selected_length_in
            - self.dut.length_in
        )


    # ========================================================
    # EXPECTED / MEASURED VALUES
    # ========================================================

    @property
    def expected_delay_ns(self):
        """
        Expected DUT one-way delay from physical length + VF.
        """

        return self.dut.delay_ns


    @property
    def rp_equivalent_length_in(self):
        """
        Equivalent physical length corresponding to measured
        RP-to-RP transmission delay using DUT VF.

        This is an equivalent length, not necessarily literal
        physical fixture length.
        """

        return delay_to_length_in(
            self.rp_delay_ns,
            self.dut.velocity_factor,
        )