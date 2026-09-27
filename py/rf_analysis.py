import numpy as np
import skrf as rf

# -------------------------------------------------------------------------
# Signal-processing settings
# -------------------------------------------------------------------------

# This is the frequency-domain window used before transforming the measured
# frequency-domain S-parameters into the time domain.
#
# Keep this consistent between:
#   1. the time response displayed to the user
#   2. scikit-rf's time_gate() calculation
#
# scikit-rf's time_gate() uses "cosine" by default.
FFT_WINDOW = "cosine"

BANDPASS = True
GATE_METHOD = "fft"


class VNAAnalysis:
    """
    RF-analysis backend for a two-port Touchstone file.

    Responsibilities:
        - Load the .s2p file
        - Verify uniform frequency spacing
        - Calculate sampling/time-domain properties
        - Calculate S11/S22/S21/S12 time responses
        - Estimate transmission delay from S21/S12
        - Calculate original and gated VSWR
        - Calculate original and gated transmission magnitude
    """

    def __init__(self, file):
        self.file = file
        self.network = rf.Network(str(file))

        if self.network.number_of_ports != 2:
            raise ValueError("Expected a two-port .s2p file.")

        self.parameters = {
            "S11": self.network.s11,
            "S22": self.network.s22,
            "S21": self.network.s21,
            "S12": self.network.s12,
        }

        self.frequency_hz = self.network.f
        self.frequency_ghz = self.frequency_hz / 1e9

        self._check_frequency_spacing()
        self._calculate_sampling()
        self._calculate_time_responses()
        self._calculate_transmission_delays()

    # ------------------------------------------------------------------
    # Frequency/time sampling
    # ------------------------------------------------------------------

    def _check_frequency_spacing(self):
        steps = np.diff(self.frequency_hz)

        if not np.allclose(steps, steps[0], rtol=1e-6):
            raise ValueError(
                "Frequency points must be uniformly spaced for FFT time gating."
            )

        self.frequency_step_hz = float(steps[0])

    def _calculate_sampling(self):
        self.frequency_span_hz = (
            self.frequency_hz[-1] - self.frequency_hz[0]
        )

        # Approximate unambiguous time record.
        self.time_window_ns = (
            1 / self.frequency_step_hz
        ) * 1e9

        # Approximate time resolution.
        self.time_resolution_ns = (
            1 / self.frequency_span_hz
        ) * 1e9

    # ------------------------------------------------------------------
    # Time-domain responses
    # ------------------------------------------------------------------

    def _calculate_time_responses(self):
        self.time_data = {}

        for name, parameter in self.parameters.items():

            time_s, response = parameter.impulse_response(
                window=FFT_WINDOW,
                bandpass=BANDPASS,
            )

            self.time_data[name] = {
                "time_ns": time_s * 1e9,
                "response": np.abs(response),
            }

    def time(self, name):
        data = self.time_data[name]

        return (
            data["time_ns"],
            data["response"],
        )

    @property
    def time_axis_ns(self):
        """
        Return the time axis used by the displayed impulse response.

        All four S-parameters share the same frequency sampling and therefore
        the same time axis.
        """
        return self.time_data["S11"]["time_ns"]

    @property
    def time_axis_start_ns(self):
        return float(self.time_axis_ns[0])

    @property
    def time_axis_stop_ns(self):
        return float(self.time_axis_ns[-1])

    # ------------------------------------------------------------------
    # Transmission-delay estimate
    # ------------------------------------------------------------------

    def _peak_delay(self, name):
        time_ns, response = self.time(name)

        index = np.argmax(response)

        return float(time_ns[index])

    def _calculate_transmission_delays(self):
        self.s21_delay_ns = self._peak_delay("S21")
        self.s12_delay_ns = self._peak_delay("S12")

        self.average_transmission_delay_ns = (
            self.s21_delay_ns + self.s12_delay_ns
        ) / 2

    def transmission_delay(self, name):
        if name == "S21":
            return self.s21_delay_ns

        if name == "S12":
            return self.s12_delay_ns

        raise ValueError(
            "Transmission delay requires S21 or S12."
        )

    # ------------------------------------------------------------------
    # Frequency-domain quantities
    # ------------------------------------------------------------------

    @staticmethod
    def vswr(parameter):
        """
        Convert a one-port S-parameter to VSWR.
        """

        gamma = np.abs(parameter.s[:, 0, 0])

        # Protect the VSWR calculation from division by zero.
        gamma = np.clip(gamma, 0, 0.999999)

        return (1 + gamma) / (1 - gamma)

    @staticmethod
    def db(parameter):
        """
        Return 20*log10(|S|).

        For S21/S12 this is the normal signed transmission magnitude in dB.
        Passive insertion loss therefore normally appears as a negative value.
        """

        magnitude = np.abs(parameter.s[:, 0, 0])

        magnitude = np.maximum(
            magnitude,
            1e-15,
        )

        return 20 * np.log10(magnitude)

    def original_vswr(self, name):
        return self.vswr(
            self.parameters[name]
        )

    def original_db(self, name):
        return self.db(
            self.parameters[name]
        )

    # ------------------------------------------------------------------
    # Gate-window definitions
    # ------------------------------------------------------------------

    @staticmethod
    def gate_window_definition(gate_window):
        """
        Translate the GUI window name into the value expected by scikit-rf.

        Boxcar:
            Rectangular/hard-edged gate.

        Kaiser:
            Tapered gate using beta = 6, matching scikit-rf's normal default.
        """

        if gate_window == "boxcar":
            return "boxcar"

        if gate_window == "kaiser":
            return ("kaiser", 6)

        raise ValueError(
            f"Unsupported gate window: {gate_window}"
        )

    def gate_shape(
        self,
        start_ns,
        stop_ns,
        gate_window="boxcar",
    ):
        """
        Generate an approximate 0-to-1 representation of the gate weighting
        for display in the GUI.

        This is primarily a visualization aid.

        Boxcar:
            1 inside the selected interval, 0 outside.

        Kaiser:
            Kaiser taper spanning the selected interval.

        The actual RF calculation is still performed by scikit-rf.time_gate().
        """

        time_ns = self.time_axis_ns

        shape = np.zeros_like(
            time_ns,
            dtype=float,
        )

        if stop_ns <= start_ns:
            return time_ns, shape

        mask = (
            (time_ns >= start_ns)
            & (time_ns <= stop_ns)
        )

        indices = np.flatnonzero(mask)

        if len(indices) == 0:
            return time_ns, shape

        if gate_window == "boxcar":
            shape[indices] = 1.0

        elif gate_window == "kaiser":

            if len(indices) == 1:
                shape[indices] = 1.0

            else:
                shape[indices] = np.kaiser(
                    len(indices),
                    beta=6,
                )

        else:
            raise ValueError(
                f"Unsupported gate window: {gate_window}"
            )

        return time_ns, shape

    # ------------------------------------------------------------------
    # Time gating
    # ------------------------------------------------------------------

    def gated_parameter(
        self,
        name,
        start_ns,
        stop_ns,
        gate_window="boxcar",
    ):
        """
        Apply time gating to one S-parameter.

        The gate window is explicit so that the calculation never silently
        depends on scikit-rf's default gate-window choice.
        """

        window = self.gate_window_definition(
            gate_window
        )

        return self.parameters[name].time_gate(
            start=start_ns,
            stop=stop_ns,
            t_unit="ns",
            method=GATE_METHOD,
            window=window,
            fft_window=FFT_WINDOW,
        )

    def gated_vswr(
        self,
        name,
        start_ns,
        stop_ns,
        gate_window="boxcar",
    ):
        gated = self.gated_parameter(
            name,
            start_ns,
            stop_ns,
            gate_window,
        )

        return self.vswr(gated)

    def gated_db(
        self,
        name,
        start_ns,
        stop_ns,
        gate_window="boxcar",
    ):
        gated = self.gated_parameter(
            name,
            start_ns,
            stop_ns,
            gate_window,
        )

        return self.db(gated)