"""Profile-related API routes."""

from collections.abc import Callable
from pathlib import Path
import time
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, status

from src.application.container import ApplicationContainer
from src.application.real_offline_alignment import (
    REAL_ALIGNMENT_PROFILES,
    REAL_PROFILE,
    RealOfflineAlignmentError,
    run_alignment_audit,
)
from src.application.runtime_config import RuntimeConfig
from src.application.temp_serial_ports import list_serial_ports
from src.webapp.deps import get_application_container, get_camera_probe_runner, get_runtime_config
from src.webapp.schemas import (
    CameraProbeRequest,
    CameraProbeResponse,
    PrecheckResponse,
    ProfileResponse,
    RealOfflineAlignmentAuditResponse,
    TempCurrentResponse,
    TempSerialPortSelectRequest,
    TempSerialPortSelectResponse,
    TempSerialPortsResponse,
    TempTargetRequest,
    TempTargetResponse,
)
from src.workflow.precheck import build_system_precheck

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/profile", response_model=ProfileResponse)
def get_profile(runtime_config: RuntimeConfig = Depends(get_runtime_config)) -> dict[str, object]:
    return runtime_config.as_public_dict()


@router.get("/precheck", response_model=PrecheckResponse)
def get_precheck(runtime_config: RuntimeConfig = Depends(get_runtime_config)) -> dict[str, object]:
    return build_system_precheck(
        profile_name=runtime_config.profile,
        storage=runtime_config.storage,
        replay=runtime_config.replay,
        adapters=runtime_config.adapters,
        camera=runtime_config.camera,
        project_root=Path(__file__).resolve().parents[3],
        run_config=runtime_config.live.run,
        vision_config=runtime_config.live.vision,
    )


@router.get("/real-offline-alignment", response_model=RealOfflineAlignmentAuditResponse)
def get_real_offline_alignment_audit(runtime_config: RuntimeConfig = Depends(get_runtime_config)) -> dict[str, Any]:
    real_profile = runtime_config.profile if runtime_config.profile in REAL_ALIGNMENT_PROFILES else REAL_PROFILE
    try:
        return run_alignment_audit(real_profile=real_profile)
    except RealOfflineAlignmentError as exc:
        return {"status": "fail", "detail": str(exc), "hardware_access": "not_attempted"}


@router.post("/camera/probe", response_model=CameraProbeResponse)
def post_camera_probe(
    probe_request: CameraProbeRequest | None = Body(default=None),
    runtime_config: RuntimeConfig = Depends(get_runtime_config),
    runner: Callable[[RuntimeConfig, dict[str, Any] | None], dict[str, Any]] = Depends(get_camera_probe_runner),
) -> dict[str, Any]:
    override = None if probe_request is None else probe_request.model_dump(exclude_none=True)
    return runner(runtime_config, override)


@router.get("/temp/current", response_model=TempCurrentResponse)
def get_current_temperature(
    container: ApplicationContainer = Depends(get_application_container),
) -> dict[str, object]:
    backend = str(container.runtime_config.live.temp.backend or container.runtime_config.adapters.get("temp", "") or "")
    try:
        reading = container.with_temp_controller(lambda controller: controller.read())
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Current temperature unavailable: {exc}") from exc
    return {
        "backend": backend or "missing",
        "temperature_celsius": float(reading.celsius),
        "timestamp_ms": int(reading.timestamp_ms),
        "source": str(reading.source),
    }


@router.get("/temp/serial-ports", response_model=TempSerialPortsResponse)
def get_temp_serial_ports(
    container: ApplicationContainer = Depends(get_application_container),
) -> dict[str, object]:
    backend = _temp_backend(container)
    try:
        ports = list_serial_ports()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Serial ports unavailable: {exc}") from exc
    selected_port = str(container.runtime_config.live.temp.serial.port or "")
    return {
        "backend": backend or "missing",
        "configured_port": selected_port,
        "selected_port": selected_port,
        "ports": [
            {
                "device": port.device,
                "name": port.name,
                "description": port.description,
                "hwid": port.hwid,
            }
            for port in ports
        ],
    }


@router.post("/temp/serial-port", response_model=TempSerialPortSelectResponse)
def post_temp_serial_port(
    payload: TempSerialPortSelectRequest,
    container: ApplicationContainer = Depends(get_application_container),
) -> dict[str, object]:
    backend = _temp_backend(container)
    if backend != "lu92xx_modbus_rtu":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Temperature serial-port selection requires lu92xx_modbus_rtu backend, got {backend or 'missing'}",
        )
    selected_port = payload.port.strip()
    try:
        visible_ports = list_serial_ports()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Serial ports unavailable: {exc}") from exc
    visible_devices = {port.device for port in visible_ports}
    if selected_port not in visible_devices:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Serial port is not currently visible: {selected_port}")
    try:
        reading = container.select_temp_serial_port(selected_port)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Temperature serial port selection unavailable: {exc}",
        ) from exc
    return {
        "backend": backend,
        "selected_port": selected_port,
        "temperature_celsius": float(reading.celsius),
        "timestamp_ms": int(reading.timestamp_ms),
        "source": str(reading.source),
    }


@router.post("/temp/target", response_model=TempTargetResponse)
def post_target_temperature(
    payload: TempTargetRequest,
    container: ApplicationContainer = Depends(get_application_container),
) -> dict[str, object]:
    backend = str(container.runtime_config.live.temp.backend or container.runtime_config.adapters.get("temp", "") or "")
    try:
        result = container.with_temp_controller(
            lambda controller: _write_and_confirm_target_temperature(controller, payload.target_temperature_celsius)
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Target temperature update unavailable: {exc}") from exc
    return {
        "backend": backend or "missing",
        "target_temperature_celsius": float(payload.target_temperature_celsius),
        "confirmed_target_temperature_celsius": float(result["confirmed_target_temperature_celsius"]),
        "timestamp_ms": int(time.time() * 1000),
        "source": str(result["source"]),
    }


def _temp_backend(container: ApplicationContainer) -> str:
    return str(container.runtime_config.live.temp.backend or container.runtime_config.adapters.get("temp", "") or "")


def _write_and_confirm_target_temperature(controller: object, target_temperature_celsius: float) -> dict[str, object]:
    controller.set_target_temperature(target_temperature_celsius)
    return {
        "confirmed_target_temperature_celsius": float(controller.read_target_temperature()),
        "source": type(controller).__name__,
    }
