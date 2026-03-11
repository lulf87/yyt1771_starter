"""Precheck scaffold that keeps workflow logic out of adapters."""

from src.core.contracts import CameraPort, PlcPort, TempReader


def run_precheck(camera: CameraPort, temp_reader: TempReader, plc: PlcPort) -> bool:
    return all((camera is not None, temp_reader is not None, plc is not None))
