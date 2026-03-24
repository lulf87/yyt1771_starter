"""Minimal Hikvision GigE / MVS camera adapter with injectable camera factory."""

from __future__ import annotations

import ctypes
from dataclasses import dataclass
import importlib
import inspect
import os
from pathlib import Path
import re
import shutil
import socket
import struct
import subprocess
import sys
import time
import types
from collections.abc import Callable, Sequence
from typing import Any

from src.core.config_models import DeviceRoiConfig
from src.core.contracts import CameraPort
from src.core.models import FramePacket


HIK_MVS_PYTHON_MODULE = "MvCameraControl_class"
HIK_MVS_PYTHON_PATH_ENV = "HIK_MVS_PYTHON_PATH"
HIK_MVS_LIBRARY_PATH_ENV = "HIK_MVS_LIBRARY_PATH"
MONO8_PIXEL_FORMAT = "mono8"
_HIK_MVS_SOURCE_CACHE: dict[tuple[str, str], Any] = {}
_GVCP_DISCOVERY_COMMAND = 0x0002
_GVCP_DISCOVERY_ACK = 0x0003
_GVCP_KEY = 0x4201
_GVCP_DISCOVERY_PORT = 3956
_GVCP_DISCOVERY_HEADER = struct.Struct("!HHHH")
_IFCONFIG_INET_PATTERN = re.compile(
    r"\s+inet (?P<ip>\d+\.\d+\.\d+\.\d+)\s+netmask \S+(?:\s+broadcast (?P<broadcast>\d+\.\d+\.\d+\.\d+))?"
)


@dataclass(slots=True)
class _GvcpInterfaceConfig:
    name: str
    ip: str
    broadcast: str


@dataclass(slots=True)
class _GvcpDiscoveredDevice:
    request_id: int
    interface: str
    host_ip: str
    ip: str
    subnet_mask: str
    gateway: str
    mac_address: str
    manufacturer: str
    model: str
    device_version: str
    manufacturer_specific_info: str
    serial_number: str
    user_defined_name: str


def discover_gige_vision_devices(*, timeout_s: float = 0.2) -> list[dict[str, str]]:
    """Best-effort GVCP discovery fallback for diagnostics when the MVS SDK cannot enumerate."""

    interfaces = _discover_gvcp_interfaces()
    if not interfaces:
        return []

    discovered: list[dict[str, str]] = []
    seen_keys: set[tuple[str, str, str]] = set()
    for index, interface in enumerate(interfaces, start=1):
        request_id = index & 0xFFFF
        if request_id == 0:
            request_id = 1
        for device in _discover_gvcp_devices_on_interface(
            interface=interface,
            request_id=request_id,
            timeout_s=timeout_s,
        ):
            dedupe_key = (device.interface, device.ip, device.serial_number or device.mac_address)
            if dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)
            discovered.append(
                {
                    "interface": device.interface,
                    "host_ip": device.host_ip,
                    "ip": device.ip,
                    "subnet_mask": device.subnet_mask,
                    "gateway": device.gateway,
                    "mac_address": device.mac_address,
                    "manufacturer": device.manufacturer,
                    "model": device.model,
                    "device_version": device.device_version,
                    "manufacturer_specific_info": device.manufacturer_specific_info,
                    "serial_number": device.serial_number,
                    "user_defined_name": device.user_defined_name,
                }
            )
    return discovered


def _discover_gvcp_devices_on_interface(
    *,
    interface: _GvcpInterfaceConfig,
    request_id: int,
    timeout_s: float,
) -> list[_GvcpDiscoveredDevice]:
    packet = _GVCP_DISCOVERY_HEADER.pack(_GVCP_KEY, _GVCP_DISCOVERY_COMMAND, 0, request_id)
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    except OSError:
        return []

    discovered: list[_GvcpDiscoveredDevice] = []
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        if hasattr(socket, "IP_BOUND_IF"):
            sock.setsockopt(
                socket.IPPROTO_IP,
                socket.IP_BOUND_IF,
                socket.if_nametoindex(interface.name),
            )
        sock.bind((interface.ip, 0))
        sock.sendto(packet, (interface.broadcast, _GVCP_DISCOVERY_PORT))

        deadline = time.monotonic() + timeout_s
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            sock.settimeout(remaining)
            try:
                payload, address = sock.recvfrom(4096)
            except socket.timeout:
                break
            except OSError:
                return discovered
            device = _parse_gvcp_discovery_ack(
                payload,
                request_id=request_id,
                interface_name=interface.name,
                host_ip=interface.ip,
                source_ip=address[0],
            )
            if device is not None:
                discovered.append(device)
    except OSError:
        return discovered
    finally:
        sock.close()
    return discovered


def _discover_gvcp_interfaces() -> list[_GvcpInterfaceConfig]:
    ifconfig = shutil.which("ifconfig")
    if ifconfig is None:
        return []
    try:
        result = subprocess.run(
            [ifconfig, "-a"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return []
    if result.returncode != 0:
        return []

    interfaces: list[_GvcpInterfaceConfig] = []
    current_name = ""
    current_lines: list[str] = []
    for line in result.stdout.splitlines():
        if line and not line[0].isspace():
            if current_name:
                config = _parse_ifconfig_block(current_name, current_lines)
                if config is not None:
                    interfaces.append(config)
            current_name = line.split(":", 1)[0]
            current_lines = [line]
            continue
        current_lines.append(line)

    if current_name:
        config = _parse_ifconfig_block(current_name, current_lines)
        if config is not None:
            interfaces.append(config)
    return interfaces


def _parse_ifconfig_block(name: str, lines: list[str]) -> _GvcpInterfaceConfig | None:
    if name.startswith("lo"):
        return None
    block = "\n".join(lines)
    if "status: active" not in block:
        return None
    match = _IFCONFIG_INET_PATTERN.search(block)
    if match is None:
        return None
    ip = match.group("ip") or ""
    broadcast = match.group("broadcast") or ""
    if not ip or not broadcast:
        return None
    return _GvcpInterfaceConfig(name=name, ip=ip, broadcast=broadcast)


def _parse_gvcp_discovery_ack(
    payload: bytes,
    *,
    request_id: int,
    interface_name: str,
    host_ip: str,
    source_ip: str,
) -> _GvcpDiscoveredDevice | None:
    if len(payload) < _GVCP_DISCOVERY_HEADER.size:
        return None
    status, command, data_length, response_request_id = _GVCP_DISCOVERY_HEADER.unpack_from(payload, 0)
    if status != 0 or command != _GVCP_DISCOVERY_ACK or response_request_id != request_id:
        return None
    if data_length < 248 or len(payload) < _GVCP_DISCOVERY_HEADER.size + data_length:
        return None

    data = payload[_GVCP_DISCOVERY_HEADER.size : _GVCP_DISCOVERY_HEADER.size + data_length]
    current_ip = _ip_from_int(int.from_bytes(data[36:40], "big")) or source_ip
    subnet_mask = _ip_from_int(int.from_bytes(data[52:56], "big"))
    gateway = _ip_from_int(int.from_bytes(data[68:72], "big"))
    mac_high = int.from_bytes(data[8:12], "big")
    mac_low = int.from_bytes(data[12:16], "big")
    return _GvcpDiscoveredDevice(
        request_id=response_request_id,
        interface=interface_name,
        host_ip=host_ip,
        ip=current_ip,
        subnet_mask=subnet_mask,
        gateway=gateway,
        mac_address=_format_mac_address(mac_high, mac_low),
        manufacturer=_decode_sdk_char_buffer(data[72:104]),
        model=_decode_sdk_char_buffer(data[104:136]),
        device_version=_decode_sdk_char_buffer(data[136:168]),
        manufacturer_specific_info=_decode_sdk_char_buffer(data[168:216]),
        serial_number=_decode_sdk_char_buffer(data[216:232]),
        user_defined_name=_decode_sdk_char_buffer(data[232:248]),
    )


def _format_mac_address(mac_high: int, mac_low: int) -> str:
    mac_value = ((mac_high & 0xFFFF) << 32) | (mac_low & 0xFFFFFFFF)
    mac_bytes = mac_value.to_bytes(6, "big")
    return ":".join(f"{item:02x}" for item in mac_bytes)


def import_hik_mvs_sdk_module() -> Any:
    _prepend_hik_mvs_python_paths()
    try:
        return importlib.import_module(HIK_MVS_PYTHON_MODULE)
    except OSError as exc:
        source_loaded = _import_hik_mvs_sdk_module_with_library_override()
        if source_loaded is not None:
            return source_loaded
        raise RuntimeError(
            "Hik MVS SDK Python binding was found, but its native library could not be loaded."
            f" Configure {HIK_MVS_LIBRARY_PATH_ENV} if libMvCameraControl.dylib lives outside /usr/local/lib."
            f" Python executable: {sys.executable}."
        ) from exc
    except ImportError as exc:
        source_loaded = _import_hik_mvs_sdk_module_with_library_override()
        if source_loaded is not None:
            return source_loaded
        extra_hint = ""
        configured_paths = _configured_hik_mvs_python_paths()
        if configured_paths:
            extra_hint = (
                f" Tried {HIK_MVS_PYTHON_PATH_ENV}="
                f"{os.pathsep.join(str(path) for path in configured_paths)}."
            )
        library_hint = ""
        configured_library_path = _configured_hik_mvs_library_path()
        if configured_library_path is not None:
            library_hint = f" Tried {HIK_MVS_LIBRARY_PATH_ENV}={configured_library_path}."
        raise RuntimeError(
            "Hik MVS SDK Python binding MvCameraControl_class is not importable on this machine."
            f" Configure {HIK_MVS_PYTHON_PATH_ENV} if the SDK Python module lives outside sys.path."
            f" Configure {HIK_MVS_LIBRARY_PATH_ENV} if libMvCameraControl.dylib lives outside /usr/local/lib."
            f" Python executable: {sys.executable}.{extra_hint}{library_hint}"
        ) from exc


def _prepend_hik_mvs_python_paths() -> None:
    configured_paths = _configured_hik_mvs_python_paths()
    if not configured_paths:
        return
    existing_paths = {Path(entry).resolve() for entry in sys.path if entry}
    for path in reversed(configured_paths):
        resolved_path = path.resolve()
        if resolved_path in existing_paths:
            continue
        sys.path.insert(0, str(path))
        existing_paths.add(resolved_path)
    importlib.invalidate_caches()


def _configured_hik_mvs_python_paths() -> list[Path]:
    raw_value = os.environ.get(HIK_MVS_PYTHON_PATH_ENV, "")
    if not raw_value.strip():
        return []
    paths: list[Path] = []
    for raw_part in raw_value.split(os.pathsep):
        candidate = Path(raw_part).expanduser()
        if candidate.exists():
            paths.append(candidate)
    return paths


def _configured_hik_mvs_library_path() -> Path | None:
    raw_value = os.environ.get(HIK_MVS_LIBRARY_PATH_ENV, "").strip()
    if not raw_value:
        return None
    candidate = Path(raw_value).expanduser()
    if candidate.exists():
        return candidate
    return None


def _import_hik_mvs_sdk_module_with_library_override() -> Any | None:
    library_path = _configured_hik_mvs_library_path()
    if library_path is None:
        return None
    module_source = _find_hik_mvs_python_module_source()
    if module_source is None:
        return None
    sys.modules.pop(HIK_MVS_PYTHON_MODULE, None)
    return _load_hik_mvs_sdk_module_from_source(module_source, library_path)


def _find_hik_mvs_python_module_source() -> Path | None:
    for search_path in _configured_hik_mvs_python_paths():
        candidate = search_path / f"{HIK_MVS_PYTHON_MODULE}.py"
        if candidate.exists():
            return candidate
    for raw_path in sys.path:
        if not raw_path:
            continue
        candidate = Path(raw_path) / f"{HIK_MVS_PYTHON_MODULE}.py"
        if candidate.exists():
            return candidate
    return None


def _load_hik_mvs_sdk_module_from_source(module_source: Path, library_path: Path) -> Any:
    cache_key = (str(module_source.resolve()), str(library_path.resolve()))
    cached_module = _HIK_MVS_SOURCE_CACHE.get(cache_key)
    if cached_module is not None:
        return cached_module

    source_text = module_source.read_text(encoding="utf-8")
    patched_source = source_text.replace(
        'ctypes.cdll.LoadLibrary("/usr/local/lib/libMvCameraControl.dylib")',
        f'ctypes.cdll.LoadLibrary(r"{library_path}")',
    )
    module_name = f"{HIK_MVS_PYTHON_MODULE}__codex_override"
    module = types.ModuleType(module_name)
    module.__file__ = str(module_source)
    module.__package__ = ""

    module_dir = str(module_source.parent)
    should_remove = False
    if module_dir not in sys.path:
        sys.path.insert(0, module_dir)
        should_remove = True
    try:
        exec(compile(patched_source, str(module_source), "exec"), module.__dict__)
    finally:
        if should_remove:
            sys.path.pop(0)

    _HIK_MVS_SOURCE_CACHE[cache_key] = module
    return module


@dataclass(slots=True)
class _OfficialMvsDeviceDescriptor:
    index: int
    raw_info: Any
    transport: str
    model: str
    serial_number: str
    ip: str


@dataclass(slots=True)
class _HandleFramePayload:
    image: Any
    timestamp_ms: int | None = None
    frame_id: int | None = None
    meta: dict[str, Any] | None = None


class _Mono8RowView(Sequence[int]):
    """Lightweight row view over a flat mono8 frame buffer."""

    __slots__ = ("_buffer", "_start", "_width")

    def __init__(self, buffer_bytes: bytes, *, start: int, width: int) -> None:
        self._buffer = buffer_bytes
        self._start = start
        self._width = width

    def __len__(self) -> int:
        return self._width

    def __getitem__(self, index: int | slice) -> int | list[int]:
        if isinstance(index, slice):
            start, stop, step = index.indices(self._width)
            return [self[position] for position in range(start, stop, step)]
        if index < 0:
            index += self._width
        if index < 0 or index >= self._width:
            raise IndexError(index)
        return int(self._buffer[self._start + index])


class _Mono8ImageView(Sequence[Sequence[int]]):
    """Sequence-compatible mono8 image that avoids materializing nested Python lists."""

    __slots__ = ("_buffer", "width", "height")

    def __init__(self, buffer_bytes: bytes, *, width: int, height: int) -> None:
        self._buffer = buffer_bytes
        self.width = width
        self.height = height

    @property
    def shape(self) -> tuple[int, int]:
        return (self.height, self.width)

    def __len__(self) -> int:
        return self.height

    def __getitem__(self, index: int | slice) -> Sequence[int] | list[Sequence[int]]:
        if isinstance(index, slice):
            start, stop, step = index.indices(self.height)
            return [self[position] for position in range(start, stop, step)]
        if index < 0:
            index += self.height
        if index < 0 or index >= self.height:
            raise IndexError(index)
        return _Mono8RowView(self._buffer, start=index * self.width, width=self.width)

    def downsample_rows(self, *, max_width: int = 640, max_height: int = 480) -> list[list[int]]:
        if self.width < 1 or self.height < 1:
            return [[0]]
        scale = max(self.width / max_width, self.height / max_height, 1.0)
        if scale <= 1.0:
            return [list(self[row_index]) for row_index in range(self.height)]
        output_width = max(1, int(self.width / scale))
        output_height = max(1, int(self.height / scale))
        rows: list[list[int]] = []
        for output_y in range(output_height):
            source_y = min(self.height - 1, int(output_y * scale))
            row_offset = source_y * self.width
            row: list[int] = []
            for output_x in range(output_width):
                source_x = min(self.width - 1, int(output_x * scale))
                row.append(int(self._buffer[row_offset + source_x]))
            rows.append(row)
        return rows


class _OfficialHikMvsHandle:
    """Compatibility bridge for Hik's official `MvCamera` Python binding."""

    def __init__(
        self,
        *,
        sdk_module: Any,
        model: str,
        transport: str,
        serial_number: str,
        ip: str,
        trigger_mode: str,
        pixel_format: str,
        exposure_us: int,
        gain_db: float,
        timeout_ms: int,
        device_roi: DeviceRoiConfig | None,
        decimation: int | None,
        binning: int | None,
        target_frame_rate_hz: float | None,
    ) -> None:
        self._sdk = sdk_module
        self._configured_model = model.strip()
        self._configured_serial_number = serial_number.strip()
        self._configured_ip = ip.strip()
        self._configured_trigger_mode = trigger_mode.strip() or "free_run"
        self._configured_pixel_format = pixel_format.strip().lower() or MONO8_PIXEL_FORMAT
        self._configured_exposure_us = exposure_us
        self._configured_gain_db = gain_db
        self._default_timeout_ms = timeout_ms
        self._configured_device_roi = device_roi or DeviceRoiConfig()
        self._configured_decimation = decimation
        self._configured_binning = binning
        self._configured_target_frame_rate_hz = (
            None if target_frame_rate_hz is None or target_frame_rate_hz <= 0 else float(target_frame_rate_hz)
        )
        self.transport = transport

        self.model = self._configured_model
        self.serial_number = self._configured_serial_number
        self.ip = self._configured_ip

        self._camera = sdk_module.MvCamera()
        self._payload_size = 0
        self._data_buffer: Any | None = None
        self._opened = False
        self._grabbing = False
        self._resulting_frame_rate: float | None = None

    def open(self) -> None:
        if self._opened:
            return
        if self._configured_pixel_format != MONO8_PIXEL_FORMAT:
            raise RuntimeError(
                "Official Hik MVS compatibility bridge currently supports only mono8 preview frames"
            )

        descriptor = self._select_device()
        self.model = descriptor.model or self.model
        self.serial_number = descriptor.serial_number or self.serial_number
        self.ip = descriptor.ip or self.ip

        try:
            self._sdk_call(
                self._camera.MV_CC_CreateHandle(descriptor.raw_info),
                "create handle",
            )
            self._sdk_call(
                self._camera.MV_CC_OpenDevice(
                    getattr(self._sdk, "MV_ACCESS_Exclusive", 1),
                    0,
                ),
                "open device",
            )
            self._configure_network_transport(descriptor)
            self._configure_trigger_mode()
            self._configure_pixel_format()
            self._configure_analog_controls()
            self._configure_device_roi()
            self._configure_frame_rate()
            self._resulting_frame_rate = self._read_optional_float_value("ResultingFrameRate")
            self._payload_size = self._read_payload_size()
            self._data_buffer = (ctypes.c_ubyte * self._payload_size)()
            self._sdk_call(self._camera.MV_CC_StartGrabbing(), "start grabbing")
            self._grabbing = True
            self._opened = True
        except Exception:
            try:
                self.close()
            except Exception:
                pass
            raise

    def is_opened(self) -> bool:
        return self._opened

    def read_frame(self, *, timeout_ms: int | None = None) -> _HandleFramePayload:
        if not self._opened:
            self.open()
        if self._data_buffer is None or self._payload_size < 1:
            raise RuntimeError("Hik camera payload buffer is not initialized")

        frame_info = self._sdk.MV_FRAME_OUT_INFO_EX()
        timeout = int(timeout_ms or self._default_timeout_ms)
        self._sdk_call(
            self._camera.MV_CC_GetOneFrameTimeout(
                self._data_buffer,
                self._payload_size,
                frame_info,
                timeout,
            ),
            "read frame",
        )
        frame_id = _first_positive_int(
            getattr(frame_info, "nFrameNum", None),
            getattr(frame_info, "nFrameCounter", None),
        )
        meta: dict[str, Any] = {}
        if self._resulting_frame_rate is not None:
            meta["camera_resulting_fps"] = float(self._resulting_frame_rate)
        if self._configured_target_frame_rate_hz is not None:
            meta["camera_target_frame_rate_hz"] = float(self._configured_target_frame_rate_hz)
        frame_counter = _positive_int_or_none(getattr(frame_info, "nFrameCounter", None))
        if frame_counter is not None:
            meta["camera_frame_counter"] = frame_counter
        lost_packet_count = _positive_int_or_none(getattr(frame_info, "nLostPacket", None))
        if lost_packet_count is not None:
            meta["camera_lost_packet_count"] = lost_packet_count
        return _HandleFramePayload(
            image=self._frame_to_rows(frame_info),
            timestamp_ms=int(time.time() * 1000),
            frame_id=frame_id,
            meta=meta,
        )

    def close(self) -> None:
        errors: list[str] = []
        if self._grabbing:
            errors.extend(self._best_effort_sdk_call("stop grabbing", self._camera.MV_CC_StopGrabbing))
            self._grabbing = False
        if self._opened:
            errors.extend(self._best_effort_sdk_call("close device", self._camera.MV_CC_CloseDevice))
        errors.extend(self._best_effort_sdk_call("destroy handle", self._camera.MV_CC_DestroyHandle))
        self._opened = False
        self._data_buffer = None
        self._payload_size = 0
        if errors:
            raise RuntimeError("; ".join(errors))

    def _select_device(self) -> _OfficialMvsDeviceDescriptor:
        device_list = self._sdk.MV_CC_DEVICE_INFO_LIST()
        layer_type = self._layer_type()
        self._sdk_call(
            self._sdk.MvCamera.MV_CC_EnumDevices(layer_type, device_list),
            "enumerate devices",
        )
        device_count = int(getattr(device_list, "nDeviceNum", 0))
        if device_count < 1:
            raise RuntimeError("No Hik cameras were discovered by the MVS SDK")

        descriptors: list[_OfficialMvsDeviceDescriptor] = []
        for index in range(device_count):
            raw_entry = device_list.pDeviceInfo[index]
            if raw_entry is None:
                continue
            raw_info = raw_entry.contents if hasattr(raw_entry, "contents") else raw_entry
            descriptors.append(self._describe_device(index, raw_info))
        if not descriptors:
            raise RuntimeError("Hik MVS returned device slots, but none were readable")

        serial_number = self._configured_serial_number
        ip = self._configured_ip
        model = self._configured_model

        filtered = descriptors
        if serial_number:
            filtered = [item for item in filtered if item.serial_number == serial_number]
        if ip:
            filtered = [item for item in filtered if item.ip == ip]
        if model:
            matched_model = [item for item in filtered if item.model == model]
            if matched_model:
                filtered = matched_model
        if filtered:
            return filtered[0]

        criteria = []
        if serial_number:
            criteria.append(f"serial_number={serial_number}")
        if ip:
            criteria.append(f"ip={ip}")
        if model:
            criteria.append(f"model={model}")
        detail = ", ".join(criteria) if criteria else "first discovered selection"
        raise RuntimeError(f"No Hik camera matched the configured selection ({detail})")

    def _describe_device(self, index: int, raw_info: Any) -> _OfficialMvsDeviceDescriptor:
        transport_code = int(getattr(raw_info, "nTLayerType", 0))
        gige_code = int(getattr(self._sdk, "MV_GIGE_DEVICE", 1))
        usb_code = int(getattr(self._sdk, "MV_USB_DEVICE", 4))

        if transport_code == gige_code:
            gige_info = raw_info.SpecialInfo.stGigEInfo
            return _OfficialMvsDeviceDescriptor(
                index=index,
                raw_info=raw_info,
                transport="gige_vision",
                model=_decode_sdk_char_buffer(getattr(gige_info, "chModelName", "")),
                serial_number=_decode_sdk_char_buffer(getattr(gige_info, "chSerialNumber", "")),
                ip=_ip_from_int(int(getattr(gige_info, "nCurrentIp", 0))),
            )
        if transport_code == usb_code:
            usb_info = raw_info.SpecialInfo.stUsb3VInfo
            return _OfficialMvsDeviceDescriptor(
                index=index,
                raw_info=raw_info,
                transport="usb3_vision",
                model=_decode_sdk_char_buffer(getattr(usb_info, "chModelName", "")),
                serial_number=_decode_sdk_char_buffer(getattr(usb_info, "chSerialNumber", "")),
                ip="",
            )
        return _OfficialMvsDeviceDescriptor(
            index=index,
            raw_info=raw_info,
            transport=f"unknown:{transport_code}",
            model="",
            serial_number="",
            ip="",
        )

    def _layer_type(self) -> int:
        if self.transport == "gige_vision":
            return int(getattr(self._sdk, "MV_GIGE_DEVICE", 1))
        return int(getattr(self._sdk, "MV_GIGE_DEVICE", 1)) | int(getattr(self._sdk, "MV_USB_DEVICE", 4))

    def _configure_network_transport(self, descriptor: _OfficialMvsDeviceDescriptor) -> None:
        if descriptor.transport != "gige_vision":
            return
        get_packet_size = getattr(self._camera, "MV_CC_GetOptimalPacketSize", None)
        set_int_value = getattr(self._camera, "MV_CC_SetIntValue", None)
        if not callable(get_packet_size) or not callable(set_int_value):
            return
        packet_size = int(get_packet_size())
        if packet_size > 0:
            self._sdk_call(set_int_value("GevSCPSPacketSize", packet_size), "set packet size")

    def _configure_trigger_mode(self) -> None:
        if self._configured_trigger_mode not in {"free_run", "free-run", "continuous"}:
            raise RuntimeError(
                f"Unsupported Hik trigger_mode for current bridge: {self._configured_trigger_mode}"
            )
        set_enum_value = getattr(self._camera, "MV_CC_SetEnumValue", None)
        if not callable(set_enum_value):
            return
        trigger_off = int(getattr(self._sdk, "MV_TRIGGER_MODE_OFF", 0))
        self._sdk_call(set_enum_value("TriggerMode", trigger_off), "set trigger mode")

    def _configure_pixel_format(self) -> None:
        set_enum_value_by_string = getattr(self._camera, "MV_CC_SetEnumValueByString", None)
        if not callable(set_enum_value_by_string):
            return
        pixel_format_symbol = {
            MONO8_PIXEL_FORMAT: "Mono8",
        }.get(self._configured_pixel_format, "")
        if not pixel_format_symbol:
            return
        ret = int(set_enum_value_by_string("PixelFormat", pixel_format_symbol))
        if ret != 0:
            # Some cameras already default to Mono8 but reject the string setter.
            # We validate the actual frame pixel type during read.
            return

    def _configure_analog_controls(self) -> None:
        set_float_value = getattr(self._camera, "MV_CC_SetFloatValue", None)
        if not callable(set_float_value):
            return
        self._sdk_call(
            set_float_value("ExposureTime", float(self._configured_exposure_us)),
            "set exposure time",
        )
        self._sdk_call(
            set_float_value("Gain", float(self._configured_gain_db)),
            "set gain",
        )

    def _configure_device_roi(self) -> None:
        if self._configured_device_roi.width < 1 or self._configured_device_roi.height < 1:
            self._reset_device_roi_to_full_frame()
            return
        set_int_value = getattr(self._camera, "MV_CC_SetIntValue", None)
        if not callable(set_int_value):
            return
        for key, value in (
            ("Width", int(self._configured_device_roi.width)),
            ("Height", int(self._configured_device_roi.height)),
            ("OffsetX", int(self._configured_device_roi.x)),
            ("OffsetY", int(self._configured_device_roi.y)),
        ):
            self._sdk_call(set_int_value(key, value), f"set {key.lower()}")

    def _reset_device_roi_to_full_frame(self) -> None:
        set_int_value = getattr(self._camera, "MV_CC_SetIntValue", None)
        if not callable(set_int_value):
            return
        width_max = self._read_optional_int_value("WidthMax")
        height_max = self._read_optional_int_value("HeightMax")
        if width_max is None or height_max is None:
            return
        for key, value in (
            ("OffsetX", 0),
            ("OffsetY", 0),
            ("Width", width_max),
            ("Height", height_max),
        ):
            self._sdk_call(set_int_value(key, value), f"reset {key.lower()}")

    def _configure_frame_rate(self) -> None:
        if self._configured_target_frame_rate_hz is None:
            return
        set_bool_value = getattr(self._camera, "MV_CC_SetBoolValue", None)
        if callable(set_bool_value):
            self._sdk_call(
                set_bool_value("AcquisitionFrameRateEnable", True),
                "enable acquisition frame rate",
            )
        set_float_value = getattr(self._camera, "MV_CC_SetFloatValue", None)
        if not callable(set_float_value):
            return
        self._sdk_call(
            set_float_value("AcquisitionFrameRate", float(self._configured_target_frame_rate_hz)),
            "set acquisition frame rate",
        )

    def _read_payload_size(self) -> int:
        payload_size = self._read_optional_int_value("PayloadSize")
        if payload_size is None:
            payload_size = 0
        if payload_size < 1:
            raise RuntimeError(f"Hik camera reported an invalid payload size: {payload_size}")
        return payload_size

    def _read_optional_int_value(self, key: str) -> int | None:
        get_int_value = getattr(self._camera, "MV_CC_GetIntValue", None)
        int_value_type = getattr(self._sdk, "MVCC_INTVALUE", None)
        if not callable(get_int_value) or int_value_type is None:
            return None
        try:
            int_value = int_value_type()
            ret = int(get_int_value(key, int_value))
        except Exception:
            return None
        if ret != 0:
            return None
        try:
            return int(getattr(int_value, "nCurValue"))
        except (TypeError, ValueError, AttributeError):
            return None

    def _read_optional_float_value(self, key: str) -> float | None:
        get_float_value = getattr(self._camera, "MV_CC_GetFloatValue", None)
        float_value_type = getattr(self._sdk, "MVCC_FLOATVALUE", None)
        if not callable(get_float_value) or float_value_type is None:
            return None
        try:
            float_value = float_value_type()
            ret = int(get_float_value(key, float_value))
        except Exception:
            return None
        if ret != 0:
            return None
        try:
            return float(getattr(float_value, "fCurValue"))
        except (TypeError, ValueError, AttributeError):
            return None

    def _frame_to_rows(self, frame_info: Any) -> _Mono8ImageView:
        width = int(getattr(frame_info, "nWidth", 0))
        height = int(getattr(frame_info, "nHeight", 0))
        if width < 1 or height < 1:
            raise RuntimeError(f"Hik camera returned an empty frame: {width}x{height}")

        mono8_pixel_type = getattr(self._sdk, "PixelType_Gvsp_Mono8", None)
        frame_pixel_type = getattr(frame_info, "enPixelType", None)
        if mono8_pixel_type is not None and frame_pixel_type != mono8_pixel_type:
            raise RuntimeError(
                "Hik frame pixel type is not Mono8. Configure the camera to output Mono8 for the current preview flow."
            )

        expected_length = width * height
        frame_length = int(getattr(frame_info, "nFrameLen", 0) or expected_length)
        available_length = min(expected_length, frame_length, self._payload_size)
        if available_length < expected_length or self._data_buffer is None:
            raise RuntimeError(
                f"Hik frame buffer is shorter than expected: need {expected_length} bytes, got {available_length}"
            )

        flat_pixels = bytes(bytearray(self._data_buffer[:expected_length]))
        return _Mono8ImageView(flat_pixels, width=width, height=height)

    def _sdk_call(self, ret_code: Any, action: str) -> None:
        ret = int(ret_code)
        if ret != 0:
            raise RuntimeError(f"Failed to {action} via Hik MVS SDK (ret=0x{ret:x})")

    def _best_effort_sdk_call(self, action: str, method: Callable[[], Any]) -> list[str]:
        try:
            ret = int(method())
        except Exception as exc:
            return [f"Failed to {action} via Hik MVS SDK: {exc}"]
        if ret != 0:
            return [f"Failed to {action} via Hik MVS SDK (ret=0x{ret:x})"]
        return []


def _decode_sdk_char_buffer(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, bytes):
        raw = value.split(b"\x00", 1)[0]
        return raw.decode("utf-8", errors="ignore").strip()

    byte_values: list[int] = []
    try:
        for item in value:
            item_int = int(item)
            if item_int == 0:
                break
            byte_values.append(item_int)
    except TypeError:
        return str(value).strip()
    return bytes(byte_values).decode("utf-8", errors="ignore").strip()


def _ip_from_int(ip_value: int) -> str:
    if ip_value <= 0:
        return ""
    return ".".join(str((ip_value >> shift) & 0xFF) for shift in (24, 16, 8, 0))


def _positive_int_or_none(value: Any) -> int | None:
    try:
        resolved = int(value)
    except (TypeError, ValueError):
        return None
    return resolved if resolved > 0 else None


def _first_positive_int(*values: Any) -> int | None:
    for value in values:
        resolved = _positive_int_or_none(value)
        if resolved is not None:
            return resolved
    return None


def _invoke_create_camera_handle(factory: Callable[..., Any], **kwargs: Any) -> Any:
    try:
        signature = inspect.signature(factory)
    except (TypeError, ValueError):
        signature = None

    if signature is None:
        try:
            return factory(**kwargs)
        except TypeError:
            legacy_kwargs = {
                key: value
                for key, value in kwargs.items()
                if key not in {"device_roi", "decimation", "binning", "profile_name", "target_frame_rate_hz"}
            }
            return factory(**legacy_kwargs)

    supported_kwargs = {
        key: value
        for key, value in kwargs.items()
        if key in signature.parameters
    }
    return factory(**supported_kwargs)


class HikGigeMvsCamera(CameraPort):
    def __init__(
        self,
        model: str,
        transport: str,
        sdk_name: str = "hik_mvs",
        serial_number: str = "",
        ip: str = "",
        trigger_mode: str = "free_run",
        pixel_format: str = "mono8",
        exposure_us: int = 10_000,
        gain_db: float = 0.0,
        timeout_ms: int = 1_000,
        device_roi: DeviceRoiConfig | None = None,
        decimation: int | None = None,
        binning: int | None = None,
        target_frame_rate_hz: float | None = None,
        profile_name: str = "measurement",
        source_name: str = "hik_gige_mvs",
        backend_name: str = "hik_gige_mvs",
        camera_factory: Callable[[], Any] | None = None,
        auto_open: bool = False,
    ) -> None:
        if not transport.strip():
            raise ValueError("transport must not be empty")
        if not sdk_name.strip():
            raise ValueError("sdk_name must not be empty")
        if not trigger_mode.strip():
            raise ValueError("trigger_mode must not be empty")
        if timeout_ms < 1:
            raise ValueError("timeout_ms must be >= 1")

        self.model = model
        self.transport = transport
        self.sdk_name = sdk_name
        self.serial_number = serial_number
        self.ip = ip
        self.trigger_mode = trigger_mode
        self.pixel_format = pixel_format
        self.exposure_us = exposure_us
        self.gain_db = gain_db
        self.timeout_ms = timeout_ms
        self.device_roi = device_roi or DeviceRoiConfig()
        self.decimation = decimation
        self.binning = binning
        self.target_frame_rate_hz = (
            None if target_frame_rate_hz is None or target_frame_rate_hz <= 0 else float(target_frame_rate_hz)
        )
        self.profile_name = profile_name
        self.source_name = source_name
        self.backend_name = backend_name
        self.camera_factory = camera_factory
        self._camera: Any | None = None
        self._frame_id = 0

        if auto_open:
            self.open()

    def open(self) -> None:
        if self.is_opened():
            return
        camera_factory = self.camera_factory or self._default_camera_factory()
        try:
            camera = camera_factory()
        except Exception as exc:  # pragma: no cover - raised through tests via injection
            raise RuntimeError("Failed to create Hik MVS camera handle") from exc
        self._open_handle(camera)
        if not self._handle_is_opened(camera):
            self._close_handle(camera)
            raise RuntimeError("Failed to open Hik GigE / MVS camera")
        self._camera = camera

    def is_opened(self) -> bool:
        return self._camera is not None and self._handle_is_opened(self._camera)

    def read_frame(self) -> FramePacket:
        if not self.is_opened():
            self.open()
        assert self._camera is not None
        raw_frame = self._read_from_handle(self._camera)
        if isinstance(raw_frame, _HandleFramePayload):
            frame = raw_frame.image
            timestamp_ms = (
                int(raw_frame.timestamp_ms)
                if raw_frame.timestamp_ms is not None and int(raw_frame.timestamp_ms) > 0
                else int(time.time() * 1000)
            )
            frame_id = raw_frame.frame_id
            extra_meta = dict(raw_frame.meta or {})
        else:
            frame = raw_frame
            timestamp_ms = int(time.time() * 1000)
            frame_id = None
            extra_meta = {}

        if frame_id is None or frame_id <= 0:
            self._frame_id += 1
            frame_id = self._frame_id
        else:
            self._frame_id = max(self._frame_id, int(frame_id))
        return FramePacket(
            timestamp_ms=timestamp_ms,
            source=self.source_name,
            image=frame,
            frame_id=int(frame_id),
            meta={
                "transport": self.transport,
                "backend": self.backend_name,
                "model": self.model,
                "serial_number": self.serial_number,
                "ip": self.ip,
                "trigger_mode": self.trigger_mode,
                "sdk": self.sdk_name,
                "pixel_format": self.pixel_format,
                "profile_name": self.profile_name,
                "device_roi": {
                    "x": self.device_roi.x,
                    "y": self.device_roi.y,
                    "width": self.device_roi.width,
                    "height": self.device_roi.height,
                },
                "decimation": self.decimation,
                "binning": self.binning,
                "target_frame_rate_hz": self.target_frame_rate_hz,
                **extra_meta,
            },
        )

    def probe_once(self, *, selection_mode: str = "pinned") -> dict[str, Any]:
        if selection_mode not in {"pinned", "first_discovered"}:
            raise ValueError(f"Unsupported camera selection mode: {selection_mode}")

        _identity, matched_by = self._resolve_identity(required=selection_mode == "pinned")
        try:
            packet = self.read_frame()
            assert self._camera is not None
            detected_device = self._detected_device_info(self._camera)
        finally:
            self.close()
        width, height = self._frame_dimensions(packet.image)
        return {
            "backend": self.backend_name,
            "transport": self.transport,
            "sdk": self.sdk_name,
            "matched_by": matched_by,
            "detected_model": detected_device["model"] or self.model.strip(),
            "detected_serial_number": detected_device["serial_number"] or self.serial_number.strip(),
            "detected_ip": detected_device["ip"] or self.ip.strip(),
            "frame_shape": {
                "width": width,
                "height": height,
            },
            "pixel_format": self.pixel_format,
            "frame_id": packet.frame_id,
            "timestamp_ms": packet.timestamp_ms,
        }

    def close(self) -> None:
        if self._camera is None:
            return
        self._close_handle(self._camera)
        self._camera = None

    def _default_camera_factory(self) -> Callable[[], Any]:
        hik_mvs = import_hik_mvs_sdk_module()

        create_handle = getattr(hik_mvs, "create_camera_handle", None)
        if callable(create_handle):
            return lambda: _invoke_create_camera_handle(
                create_handle,
                model=self.model,
                transport=self.transport,
                serial_number=self.serial_number,
                ip=self.ip,
                trigger_mode=self.trigger_mode,
                pixel_format=self.pixel_format,
                exposure_us=self.exposure_us,
                gain_db=self.gain_db,
                timeout_ms=self.timeout_ms,
                device_roi=self.device_roi,
                decimation=self.decimation,
                binning=self.binning,
                target_frame_rate_hz=self.target_frame_rate_hz,
                profile_name=self.profile_name,
            )
        official_camera_class = getattr(hik_mvs, "MvCamera", None)
        if official_camera_class is not None:
            return lambda: _OfficialHikMvsHandle(
                sdk_module=hik_mvs,
                model=self.model,
                transport=self.transport,
                serial_number=self.serial_number,
                ip=self.ip,
                trigger_mode=self.trigger_mode,
                pixel_format=self.pixel_format,
                exposure_us=self.exposure_us,
                gain_db=self.gain_db,
                timeout_ms=self.timeout_ms,
                device_roi=self.device_roi,
                decimation=self.decimation,
                binning=self.binning,
                target_frame_rate_hz=self.target_frame_rate_hz,
            )
        raise RuntimeError(
            "Hik MVS SDK was imported, but no supported camera factory was found for live GigE access"
        )

    @staticmethod
    def _open_handle(camera: Any) -> None:
        for method_name in ("open", "start", "start_grabbing"):
            method = getattr(camera, method_name, None)
            if callable(method):
                method()
                return

    def _read_from_handle(self, camera: Any) -> Any:
        for method_name in ("read_frame", "get_frame", "read"):
            method = getattr(camera, method_name, None)
            if not callable(method):
                continue
            frame = self._invoke_frame_reader(method)
            if frame is None:
                raise RuntimeError("Failed to read frame from Hik GigE / MVS camera")
            return frame
        raise RuntimeError("Camera handle does not provide a supported frame read method")

    def _invoke_frame_reader(self, reader: Callable[..., Any]) -> Any:
        try:
            result = reader(timeout_ms=self.timeout_ms)
        except TypeError:
            try:
                result = reader(self.timeout_ms)
            except TypeError:
                result = reader()
        if isinstance(result, tuple) and len(result) == 2:
            ok, frame = result
            return frame if ok else None
        return result

    def _resolve_identity(self, *, required: bool) -> tuple[str, str]:
        serial_number = self.serial_number.strip()
        if serial_number:
            return serial_number, "serial_number"
        ip = self.ip.strip()
        if ip:
            return ip, "ip"
        if required:
            raise ValueError("Camera identity is missing. Configure serial_number or ip before probing.")
        return "", "first_discovered"

    @staticmethod
    def _frame_dimensions(image: Any) -> tuple[int, int]:
        if hasattr(image, "shape"):
            shape = getattr(image, "shape")
            if len(shape) >= 2:
                return int(shape[1]), int(shape[0])
        if isinstance(image, (list, tuple)):
            height = len(image)
            if height == 0:
                return (0, 0)
            first_row = image[0]
            if isinstance(first_row, (list, tuple)):
                return (len(first_row), height)
            return (height, 1)
        raise RuntimeError("Unable to determine frame dimensions from probe image")

    def _detected_device_info(self, camera: Any) -> dict[str, str]:
        return {
            "model": self._extract_device_value(
                camera,
                attr_names=("model", "device_model", "camera_model"),
                method_names=("get_model", "model_name"),
                info_keys=("model", "device_model", "camera_model"),
            ),
            "serial_number": self._extract_device_value(
                camera,
                attr_names=("serial_number", "serial", "device_serial_number"),
                method_names=("get_serial_number", "get_serial"),
                info_keys=("serial_number", "serial", "device_serial_number"),
            ),
            "ip": self._extract_device_value(
                camera,
                attr_names=("ip", "ip_address", "device_ip"),
                method_names=("get_ip", "get_ip_address"),
                info_keys=("ip", "ip_address", "device_ip"),
            ),
        }

    def _extract_device_value(
        self,
        camera: Any,
        *,
        attr_names: tuple[str, ...],
        method_names: tuple[str, ...],
        info_keys: tuple[str, ...],
    ) -> str:
        for attr_name in attr_names:
            if hasattr(camera, attr_name):
                value = getattr(camera, attr_name)
                text = self._string_value(value)
                if text:
                    return text

        for method_name in method_names:
            method = getattr(camera, method_name, None)
            if callable(method):
                text = self._string_value(method())
                if text:
                    return text

        for info_name in ("get_device_info", "device_info", "device_meta"):
            info = getattr(camera, info_name, None)
            if callable(info):
                info = info()
            if isinstance(info, dict):
                for key in info_keys:
                    text = self._string_value(info.get(key))
                    if text:
                        return text

        return ""

    @staticmethod
    def _string_value(value: Any) -> str:
        if value is None:
            return ""
        text = str(value).strip()
        return text

    @staticmethod
    def _handle_is_opened(camera: Any) -> bool:
        for method_name in ("is_opened", "is_open", "isOpened"):
            method = getattr(camera, method_name, None)
            if callable(method):
                return bool(method())
        if hasattr(camera, "opened"):
            return bool(camera.opened)
        return True

    @staticmethod
    def _close_handle(camera: Any) -> None:
        for method_name in ("close", "stop_grabbing", "stop", "destroy"):
            method = getattr(camera, method_name, None)
            if callable(method):
                method()
                return
