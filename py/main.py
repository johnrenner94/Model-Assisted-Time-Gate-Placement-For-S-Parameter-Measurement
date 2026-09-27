import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from rf_analysis import VNAAnalysis
from gating import DUT, GateModel
from app import TimeGatingApp


FILE = Path("data/2port.s2p")

VELOCITY_FACTOR = 0.765
DUT_LENGTH_IN = 8.0
ADAPTERS_PRESENT = False

REPORT_START_GHZ = 2.0
REPORT_STOP_GHZ = 26.5


def main():

    qt_app = QApplication(sys.argv)

    analysis = VNAAnalysis(FILE)

    dut = DUT(
        length_in=DUT_LENGTH_IN,
        velocity_factor=VELOCITY_FACTOR,
    )

    model = GateModel(
        dut=dut,
        rp_delay_ns=analysis.average_transmission_delay_ns,
        adapters=ADAPTERS_PRESENT,
    )

    window = TimeGatingApp(
        analysis=analysis,
        model=model,
        report_start_ghz=REPORT_START_GHZ,
        report_stop_ghz=REPORT_STOP_GHZ,
    )

    window.show()

    sys.exit(qt_app.exec())


if __name__ == "__main__":
    main()