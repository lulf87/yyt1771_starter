import sys

import pytest

import src.camera.hik_gige_mvs as hik_gige_mvs_module
from src.camera.hik_gige_mvs import (
    HIK_MVS_LIBRARY_PATH_ENV,
    HIK_MVS_PYTHON_MODULE,
    HIK_MVS_PYTHON_PATH_ENV,
    HikGigeMvsCamera,
    import_hik_mvs_sdk_module,
)
from src.core.config_models import DeviceRoiConfig


class FakeMvsHandle:
    def __init__(
        self,
        frames: list[object] | None = None,
        *,
        model: str = "MV-CU060-10GM",
        serial_number: str = "DEV-001",
        ip: str = "192.168.1.10",
    ) -> None:
        self.frames = list(frames or [])
        self.opened = False
        self.open_count = 0
        self.close_count = 0
        self.model = model
        self.serial_number = serial_number
        self.ip = ip

    def open(self) -> None:
        self.open_count += 1
        self.opened = True

    def is_opened(self) -> bool:
        return self.opened

    def read_frame(self, *, timeout_ms: int = 1000) -> object | None:
        assert timeout_ms == 750
        if not self.frames:
            return None
        return self.frames.pop(0)

    def close(self) -> None:
        self.close_count += 1
        self.opened = False


class _FakeOfficialGigEInfo:
    def __init__(self, *, model: str, serial_number: str, ip: str) -> None:
        self.chModelName = _to_sdk_char_array(model)
        self.chSerialNumber = _to_sdk_char_array(serial_number)
        self.nCurrentIp = _ip_to_int(ip)


class _FakeOfficialUsbInfo:
    def __init__(self) -> None:
        self.chModelName = _to_sdk_char_array("")
        self.chSerialNumber = _to_sdk_char_array("")


class _FakeOfficialSpecialInfo:
    def __init__(self, *, gige_info: _FakeOfficialGigEInfo | None = None) -> None:
        self.stGigEInfo = gige_info or _FakeOfficialGigEInfo(model="", serial_number="", ip="")
        self.stUsb3VInfo = _FakeOfficialUsbInfo()


class _FakeOfficialDeviceInfo:
    def __init__(self, *, model: str, serial_number: str, ip: str, transport_code: int) -> None:
        self.nTLayerType = transport_code
        self.SpecialInfo = _FakeOfficialSpecialInfo(
            gige_info=_FakeOfficialGigEInfo(model=model, serial_number=serial_number, ip=ip)
        )


class _FakeOfficialDevicePointer:
    def __init__(self, contents) -> None:
        self.contents = contents


class _FakeOfficialDeviceList:
    def __init__(self) -> None:
        self.nDeviceNum = 0
        self.pDeviceInfo = [None] * 256


class _FakeOfficialIntValue:
    def __init__(self) -> None:
        self.nCurValue = 0
        self.nMin = 0
        self.nMax = 0
        self.nInc = 1


class _FakeOfficialFloatValue:
    def __init__(self) -> None:
        self.fCurValue = 0.0


class _FakeOfficialFrameInfo:
    def __init__(self) -> None:
        self.nWidth = 0
        self.nHeight = 0
        self.enPixelType = 0
        self.nFrameLen = 0
        self.nFrameNum = 0
        self.nFrameCounter = 0
        self.nLostPacket = 0


class _FakeOfficialMvCamera:
    _module = None

    def __init__(self) -> None:
        assert self._module is not None
        self.module = self._module
        self.opened = False
        self.grabbing = False
        self.handle_created = False
        self.selected_device = None
        self.destroy_count = 0
        self.close_count = 0
        self.stop_count = 0
        self.configured_values: dict[str, object] = {}
        self.read_timeout_ms = None
        self.packet_size = 1500
        self.module.created_cameras.append(self)

    @classmethod
    def MV_CC_EnumDevices(cls, nTLayerType, stDevList) -> int:
        module = cls._module
        assert module is not None
        stDevList.nDeviceNum = len(module.device_infos)
        for index, device in enumerate(module.device_infos):
            stDevList.pDeviceInfo[index] = _FakeOfficialDevicePointer(device)
        return module.enum_ret_code

    def MV_CC_CreateHandle(self, stDevInfo) -> int:
        self.handle_created = True
        self.selected_device = stDevInfo
        return 0

    def MV_CC_OpenDevice(self, nAccessMode=1, nSwitchoverKey=0) -> int:
        assert self.handle_created is True
        self.opened = True
        self.configured_values["access_mode"] = nAccessMode
        self.configured_values["switchover_key"] = nSwitchoverKey
        return 0

    def MV_CC_CloseDevice(self) -> int:
        self.close_count += 1
        self.opened = False
        return 0

    def MV_CC_DestroyHandle(self) -> int:
        self.destroy_count += 1
        self.handle_created = False
        return 0

    def MV_CC_GetOptimalPacketSize(self) -> int:
        return self.packet_size

    def MV_CC_SetIntValue(self, strKey, nValue) -> int:
        self.configured_values[strKey] = nValue
        self.module.int_values[strKey] = int(nValue)
        return 0

    def MV_CC_SetBoolValue(self, strKey, bValue) -> int:
        self.configured_values[strKey] = bool(bValue)
        return 0

    def MV_CC_SetEnumValue(self, strKey, nValue) -> int:
        self.configured_values[strKey] = nValue
        return 0

    def MV_CC_SetEnumValueByString(self, strKey, sValue) -> int:
        self.configured_values[strKey] = sValue
        return 0

    def MV_CC_SetFloatValue(self, strKey, fValue) -> int:
        self.configured_values[strKey] = fValue
        self.module.float_values[strKey] = float(fValue)
        if strKey == "AcquisitionFrameRate":
            self.module.float_values["ResultingFrameRate"] = float(fValue)
        return 0

    def MV_CC_GetFloatValue(self, strKey, stFloatValue) -> int:
        stFloatValue.fCurValue = float(self.module.float_values.get(strKey, 0.0))
        return 0

    def MV_CC_GetIntValue(self, strKey, stIntValue) -> int:
        if strKey == "PayloadSize" and strKey not in self.module.int_values:
            stIntValue.nCurValue = len(self.module.frame_rows) * len(self.module.frame_rows[0])
            stIntValue.nMax = stIntValue.nCurValue
            return 0
        stIntValue.nCurValue = int(self.module.int_values.get(strKey, 0))
        descriptor = self.module.int_descriptors.get(strKey, {})
        stIntValue.nMin = int(descriptor.get("min", 0))
        stIntValue.nMax = int(descriptor.get("max", stIntValue.nCurValue))
        stIntValue.nInc = int(descriptor.get("inc", 1))
        return 0

    def MV_CC_StartGrabbing(self) -> int:
        self.grabbing = True
        return 0

    def MV_CC_StopGrabbing(self) -> int:
        self.stop_count += 1
        self.grabbing = False
        return 0

    def MV_CC_GetOneFrameTimeout(self, pData, nDataSize, stFrameInfo, nMsec=1000) -> int:
        self.read_timeout_ms = nMsec
        rows = self.module.frame_rows
        flat = [pixel for row in rows for pixel in row]
        for index, pixel in enumerate(flat):
            pData[index] = pixel
        stFrameInfo.nWidth = len(rows[0])
        stFrameInfo.nHeight = len(rows)
        stFrameInfo.enPixelType = self.module.frame_pixel_type
        stFrameInfo.nFrameLen = len(flat)
        stFrameInfo.nFrameNum = self.module.frame_number
        stFrameInfo.nFrameCounter = self.module.frame_counter
        stFrameInfo.nLostPacket = self.module.lost_packet_count
        return self.module.frame_ret_code


class _FakeOfficialSdkModule:
    MV_GIGE_DEVICE = 1
    MV_USB_DEVICE = 4
    MV_ACCESS_Exclusive = 1
    MV_TRIGGER_MODE_OFF = 0
    PixelType_Gvsp_Mono8 = 17301505
    MV_CC_DEVICE_INFO_LIST = _FakeOfficialDeviceList
    MVCC_INTVALUE = _FakeOfficialIntValue
    MVCC_FLOATVALUE = _FakeOfficialFloatValue
    MV_FRAME_OUT_INFO_EX = _FakeOfficialFrameInfo

    def __init__(
        self,
        *,
        device_infos: list[_FakeOfficialDeviceInfo],
        frame_rows: list[list[int]],
        frame_pixel_type: int | None = None,
        enum_ret_code: int = 0,
        frame_ret_code: int = 0,
        int_values: dict[str, int] | None = None,
        int_descriptors: dict[str, dict[str, int]] | None = None,
        float_values: dict[str, float] | None = None,
        frame_number: int = 1,
        frame_counter: int = 1,
        lost_packet_count: int = 0,
    ) -> None:
        self.device_infos = device_infos
        self.frame_rows = frame_rows
        self.frame_pixel_type = frame_pixel_type or self.PixelType_Gvsp_Mono8
        self.enum_ret_code = enum_ret_code
        self.frame_ret_code = frame_ret_code
        self.int_values = dict(int_values or {})
        self.int_descriptors = dict(int_descriptors or {})
        self.float_values = dict(float_values or {})
        self.frame_number = frame_number
        self.frame_counter = frame_counter
        self.lost_packet_count = lost_packet_count
        self.created_cameras: list[_FakeOfficialMvCamera] = []
        camera_class = type("FakeOfficialMvCameraBound", (_FakeOfficialMvCamera,), {})
        camera_class._module = self
        self.MvCamera = camera_class


def _to_sdk_char_array(text: str) -> list[int]:
    return list(text.encode("utf-8")) + [0]


def _ip_to_int(ip: str) -> int:
    parts = [int(part) for part in ip.split(".")]
    return (parts[0] << 24) | (parts[1] << 16) | (parts[2] << 8) | parts[3]


def _build_camera(camera_factory) -> HikGigeMvsCamera:
    return HikGigeMvsCamera(
        model="MV-CU060-10GM",
        transport="gige_vision",
        sdk_name="hik_mvs",
        serial_number="DEV-001",
        trigger_mode="free_run",
        timeout_ms=750,
        camera_factory=camera_factory,
    )


def test_open_read_close_flow_returns_frame_packets_with_incrementing_ids() -> None:
    fake_handle = FakeMvsHandle(frames=[{"frame": 1}, {"frame": 2}])
    camera = _build_camera(lambda: fake_handle)

    camera.open()
    first = camera.read_frame()
    second = camera.read_frame()
    camera.close()

    assert fake_handle.open_count == 1
    assert fake_handle.close_count == 1
    assert first.image == {"frame": 1}
    assert second.image == {"frame": 2}
    assert first.frame_id == 1
    assert second.frame_id == 2
    assert first.meta["backend"] == "hik_gige_mvs"
    assert first.meta["transport"] == "gige_vision"
    assert first.meta["model"] == "MV-CU060-10GM"
    assert first.meta["serial_number"] == "DEV-001"
    assert first.meta["trigger_mode"] == "free_run"


def test_read_frame_auto_opens_camera_when_needed() -> None:
    fake_handle = FakeMvsHandle(frames=[{"frame": 1}])
    camera = _build_camera(lambda: fake_handle)

    packet = camera.read_frame()

    assert packet.frame_id == 1
    assert fake_handle.open_count == 1
    assert camera.is_opened() is True


def test_open_raises_clear_error_when_factory_cannot_create_handle() -> None:
    camera = _build_camera(lambda: (_ for _ in ()).throw(RuntimeError("sdk missing")))

    with pytest.raises(RuntimeError, match="create Hik MVS camera handle"):
        camera.open()


def test_probe_once_selection_mode_pinned_prefers_serial_number_as_identity() -> None:
    camera = HikGigeMvsCamera(
        model="MV-CU060-10GM",
        transport="gige_vision",
        sdk_name="hik_mvs",
        serial_number="MV-SERIAL-001",
        ip="192.168.1.10",
        pixel_format="mono8",
        timeout_ms=750,
        camera_factory=lambda: FakeMvsHandle(
            frames=[[[0, 255], [255, 0]]],
            serial_number="MV-SERIAL-001",
            ip="192.168.1.10",
        ),
    )

    payload = camera.probe_once(selection_mode="pinned")

    assert payload["matched_by"] == "serial_number"
    assert payload["detected_serial_number"] == "MV-SERIAL-001"
    assert payload["detected_ip"] == "192.168.1.10"
    assert payload["detected_model"] == "MV-CU060-10GM"
    assert payload["frame_shape"] == {"width": 2, "height": 2}
    assert payload["pixel_format"] == "mono8"
    assert payload["frame_id"] == 1
    assert isinstance(payload["timestamp_ms"], int)


def test_probe_once_selection_mode_pinned_falls_back_to_ip_identity() -> None:
    camera = HikGigeMvsCamera(
        model="MV-CU060-10GM",
        transport="gige_vision",
        sdk_name="hik_mvs",
        serial_number="",
        ip="192.168.1.10",
        timeout_ms=750,
        camera_factory=lambda: FakeMvsHandle(
            frames=[[[1, 2, 3]]],
            serial_number="",
            ip="192.168.1.10",
        ),
    )

    payload = camera.probe_once(selection_mode="pinned")

    assert payload["matched_by"] == "ip"
    assert payload["detected_serial_number"] == ""
    assert payload["detected_ip"] == "192.168.1.10"
    assert payload["frame_shape"] == {"width": 3, "height": 1}


def test_probe_once_rejects_missing_identity_in_pinned_mode() -> None:
    camera = HikGigeMvsCamera(
        model="",
        transport="gige_vision",
        sdk_name="hik_mvs",
        timeout_ms=750,
        camera_factory=lambda: FakeMvsHandle(frames=[[[0]]], serial_number="", ip=""),
    )

    with pytest.raises(ValueError, match="serial_number or ip"):
        camera.probe_once(selection_mode="pinned")


def test_probe_once_first_discovered_succeeds_without_identity() -> None:
    camera = HikGigeMvsCamera(
        model="",
        transport="gige_vision",
        sdk_name="hik_mvs",
        timeout_ms=750,
        camera_factory=lambda: FakeMvsHandle(
            frames=[[[0, 1, 2], [3, 4, 5]]],
            model="ANY-MODEL",
            serial_number="DISCOVERED-001",
            ip="192.168.1.88",
        ),
    )

    payload = camera.probe_once(selection_mode="first_discovered")

    assert payload["matched_by"] == "first_discovered"
    assert payload["detected_model"] == "ANY-MODEL"
    assert payload["detected_serial_number"] == "DISCOVERED-001"
    assert payload["detected_ip"] == "192.168.1.88"
    assert payload["frame_shape"] == {"width": 3, "height": 2}


def test_probe_once_surfaces_factory_failures_clearly() -> None:
    camera = HikGigeMvsCamera(
        model="MV-CU060-10GM",
        transport="gige_vision",
        sdk_name="hik_mvs",
        serial_number="MV-SERIAL-001",
        timeout_ms=750,
        camera_factory=lambda: (_ for _ in ()).throw(RuntimeError("sdk missing")),
    )

    with pytest.raises(RuntimeError, match="create Hik MVS camera handle"):
        camera.probe_once(selection_mode="pinned")


def test_parse_gvcp_discovery_ack_extracts_realistic_device_identity() -> None:
    payload = bytes.fromhex(
        "0000000300f812340002000080000001000034bd2001ab0d8000000700000005000000000000000000000000"
        "c0a803d3000000000000000000000000ffffff00000000000000000000000000c0a803fe48696b726f626f74"
        "0000000000000000000000000000000000000000000000004d562d43413036302d3131474d00000000000000"
        "00000000000000000000000056332e312e322032313038323320363735333239000000000000000000000000"
        "48696b726f626f74000000000000000000000000000000000000000000000000000000000000000000000000"
        "0000000030304a3637333738363236000000000057617463680000000000000000000000"
    )

    device = hik_gige_mvs_module._parse_gvcp_discovery_ack(
        payload,
        request_id=0x1234,
        interface_name="en7",
        host_ip="192.168.188.22",
        source_ip="192.168.3.211",
    )

    assert device is not None
    assert device.interface == "en7"
    assert device.host_ip == "192.168.188.22"
    assert device.ip == "192.168.3.211"
    assert device.subnet_mask == "255.255.255.0"
    assert device.gateway == "192.168.3.254"
    assert device.mac_address == "34:bd:20:01:ab:0d"
    assert device.manufacturer == "Hikrobot"
    assert device.model == "MV-CA060-11GM"
    assert device.device_version == "V3.1.2 210823 675329"
    assert device.manufacturer_specific_info == "Hikrobot"
    assert device.serial_number == "00J67378626"
    assert device.user_defined_name == "Watch"


def test_close_is_idempotent() -> None:
    fake_handle = FakeMvsHandle(frames=[{"frame": 1}])
    camera = _build_camera(lambda: fake_handle)
    camera.open()

    camera.close()
    camera.close()

    assert fake_handle.close_count == 1


@pytest.mark.parametrize(
    ("model", "transport", "sdk_name", "timeout_ms"),
    [
        ("MV-CU060-10GM", "", "hik_mvs", 750),
        ("MV-CU060-10GM", "gige_vision", "", 750),
        ("MV-CU060-10GM", "gige_vision", "hik_mvs", 0),
    ],
)
def test_missing_required_init_values_raise_value_error(
    model: str,
    transport: str,
    sdk_name: str,
    timeout_ms: int,
) -> None:
    with pytest.raises(ValueError):
        HikGigeMvsCamera(
            model=model,
            transport=transport,
            sdk_name=sdk_name,
            timeout_ms=timeout_ms,
            camera_factory=lambda: FakeMvsHandle(),
        )


def test_import_hik_mvs_sdk_module_supports_explicit_python_path_override(
    tmp_path: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "path", list(sys.path))
    sdk_python_dir = tmp_path / "sdk_python"
    sdk_python_dir.mkdir()
    module_file = sdk_python_dir / f"{HIK_MVS_PYTHON_MODULE}.py"
    module_file.write_text("SDK_MARKER = 'hik-mvs-from-env-path'\n", encoding="utf-8")

    monkeypatch.setenv(HIK_MVS_PYTHON_PATH_ENV, str(sdk_python_dir))
    monkeypatch.delitem(sys.modules, HIK_MVS_PYTHON_MODULE, raising=False)

    module = import_hik_mvs_sdk_module()

    assert module.SDK_MARKER == "hik-mvs-from-env-path"
    assert str(module_file) == str(module.__file__)
    monkeypatch.delitem(sys.modules, HIK_MVS_PYTHON_MODULE, raising=False)


def test_import_hik_mvs_sdk_module_error_mentions_env_override_hint(
    tmp_path: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "path", list(sys.path))
    empty_sdk_dir = tmp_path / "empty_sdk_python"
    empty_sdk_dir.mkdir()
    monkeypatch.setenv(HIK_MVS_PYTHON_PATH_ENV, str(empty_sdk_dir))
    monkeypatch.delitem(sys.modules, HIK_MVS_PYTHON_MODULE, raising=False)

    with pytest.raises(RuntimeError, match=HIK_MVS_PYTHON_PATH_ENV):
        import_hik_mvs_sdk_module()


def test_import_hik_mvs_sdk_module_supports_explicit_library_path_override(
    tmp_path: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "path", list(sys.path))
    sdk_python_dir = tmp_path / "sdk_python"
    sdk_python_dir.mkdir()
    module_file = sdk_python_dir / f"{HIK_MVS_PYTHON_MODULE}.py"
    module_file.write_text(
        '\n'.join(
            [
                "import ctypes",
                'MvCamCtrldll = ctypes.cdll.LoadLibrary("/usr/local/lib/libMvCameraControl.dylib")',
                "SDK_MARKER = 'hik-mvs-from-library-path'",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    fake_library = tmp_path / "libMvCameraControl.dylib"
    fake_library.write_text("fake dylib marker\n", encoding="utf-8")

    loaded_paths: list[str] = []

    def fake_load_library(path: str):
        loaded_paths.append(path)
        if path == "/usr/local/lib/libMvCameraControl.dylib":
            raise OSError("missing system library")
        return object()

    monkeypatch.setattr(hik_gige_mvs_module.ctypes.cdll, "LoadLibrary", fake_load_library)
    monkeypatch.setenv(HIK_MVS_PYTHON_PATH_ENV, str(sdk_python_dir))
    monkeypatch.setenv(HIK_MVS_LIBRARY_PATH_ENV, str(fake_library))
    monkeypatch.delitem(sys.modules, HIK_MVS_PYTHON_MODULE, raising=False)

    module = import_hik_mvs_sdk_module()

    assert module.SDK_MARKER == "hik-mvs-from-library-path"
    assert loaded_paths == [
        "/usr/local/lib/libMvCameraControl.dylib",
        str(fake_library),
    ]
    monkeypatch.delitem(sys.modules, HIK_MVS_PYTHON_MODULE, raising=False)


def test_default_factory_supports_official_hik_sdk_module(monkeypatch: pytest.MonkeyPatch) -> None:
    sdk_module = _FakeOfficialSdkModule(
        device_infos=[
            _FakeOfficialDeviceInfo(
                model="MV-CA060-11GM",
                serial_number="MV-SERIAL-001",
                ip="192.168.1.11",
                transport_code=_FakeOfficialSdkModule.MV_GIGE_DEVICE,
            )
        ],
        frame_rows=[[1, 2, 3], [4, 5, 6]],
        int_values={
            "Width": 3072,
            "Height": 2048,
            "OffsetX": 0,
            "OffsetY": 0,
        },
        int_descriptors={
            "Width": {"min": 64, "max": 3072, "inc": 8},
            "Height": {"min": 64, "max": 2048, "inc": 4},
            "OffsetX": {"min": 0, "max": 2752, "inc": 8},
            "OffsetY": {"min": 0, "max": 1920, "inc": 4},
        },
    )
    monkeypatch.setattr(hik_gige_mvs_module, "import_hik_mvs_sdk_module", lambda: sdk_module)

    camera = HikGigeMvsCamera(
        model="MV-CA060-11GM",
        transport="gige_vision",
        sdk_name="hik_mvs",
        serial_number="MV-SERIAL-001",
        pixel_format="mono8",
        exposure_us=12000,
        gain_db=2.5,
        timeout_ms=750,
    )

    packet = camera.read_frame()
    camera.close()

    assert len(packet.image) == 2
    assert len(packet.image[0]) == 3
    assert [list(row) for row in packet.image] == [[1, 2, 3], [4, 5, 6]]
    assert packet.meta["model"] == "MV-CA060-11GM"
    assert packet.meta["serial_number"] == "MV-SERIAL-001"
    assert packet.meta["trigger_mode"] == "free_run"
    fake_camera = sdk_module.created_cameras[0]
    assert fake_camera.read_timeout_ms == 750
    assert fake_camera.configured_values["TriggerMode"] == _FakeOfficialSdkModule.MV_TRIGGER_MODE_OFF
    assert fake_camera.configured_values["PixelFormat"] == "Mono8"
    assert fake_camera.configured_values["ExposureTime"] == 12000.0
    assert fake_camera.configured_values["Gain"] == 2.5
    assert fake_camera.configured_values["GevSCPSPacketSize"] == 1500
    assert fake_camera.stop_count == 1
    assert fake_camera.close_count == 1
    assert fake_camera.destroy_count == 1


def test_default_factory_official_sdk_frame_supports_native_downsample_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sdk_module = _FakeOfficialSdkModule(
        device_infos=[
            _FakeOfficialDeviceInfo(
                model="MV-CA060-11GM",
                serial_number="MV-SERIAL-001",
                ip="192.168.1.11",
                transport_code=_FakeOfficialSdkModule.MV_GIGE_DEVICE,
            )
        ],
        frame_rows=[
            [1, 2, 3, 4],
            [5, 6, 7, 8],
            [9, 10, 11, 12],
            [13, 14, 15, 16],
        ],
    )
    monkeypatch.setattr(hik_gige_mvs_module, "import_hik_mvs_sdk_module", lambda: sdk_module)

    camera = HikGigeMvsCamera(
        model="MV-CA060-11GM",
        transport="gige_vision",
        sdk_name="hik_mvs",
        serial_number="MV-SERIAL-001",
        pixel_format="mono8",
        timeout_ms=750,
    )

    packet = camera.read_frame()
    camera.close()

    downsampled = packet.image.downsample_rows(max_width=2, max_height=2)

    assert downsampled == [[1, 3], [9, 11]]


def test_default_factory_official_sdk_frame_supports_native_bitmap_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sdk_module = _FakeOfficialSdkModule(
        device_infos=[
            _FakeOfficialDeviceInfo(
                model="MV-CA060-11GM",
                serial_number="MV-SERIAL-001",
                ip="192.168.1.11",
                transport_code=_FakeOfficialSdkModule.MV_GIGE_DEVICE,
            )
        ],
        frame_rows=[
            [1, 2, 3, 4],
            [5, 6, 7, 8],
            [9, 10, 11, 12],
            [13, 14, 15, 16],
        ],
    )
    monkeypatch.setattr(hik_gige_mvs_module, "import_hik_mvs_sdk_module", lambda: sdk_module)

    camera = HikGigeMvsCamera(
        model="MV-CA060-11GM",
        transport="gige_vision",
        sdk_name="hik_mvs",
        serial_number="MV-SERIAL-001",
        pixel_format="mono8",
        timeout_ms=750,
    )

    packet = camera.read_frame()
    camera.close()

    width, height, pixels = packet.image.downsample_bitmap_payload(max_width=2, max_height=2)

    assert (width, height) == (2, 2)
    assert isinstance(pixels, bytes)
    assert len(pixels) == 4


def test_default_factory_applies_measurement_roi_to_official_hik_sdk_module(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sdk_module = _FakeOfficialSdkModule(
        device_infos=[
            _FakeOfficialDeviceInfo(
                model="MV-CA060-11GM",
                serial_number="MV-SERIAL-001",
                ip="192.168.1.11",
                transport_code=_FakeOfficialSdkModule.MV_GIGE_DEVICE,
            )
        ],
        frame_rows=[[1, 2, 3], [4, 5, 6]],
        int_values={
            "Width": 3072,
            "Height": 2048,
            "OffsetX": 0,
            "OffsetY": 0,
        },
        int_descriptors={
            "Width": {"min": 64, "max": 3072, "inc": 8},
            "Height": {"min": 64, "max": 2048, "inc": 4},
            "OffsetX": {"min": 0, "max": 2752, "inc": 8},
            "OffsetY": {"min": 0, "max": 1920, "inc": 4},
        },
    )
    monkeypatch.setattr(hik_gige_mvs_module, "import_hik_mvs_sdk_module", lambda: sdk_module)

    camera = HikGigeMvsCamera(
        model="MV-CA060-11GM",
        transport="gige_vision",
        sdk_name="hik_mvs",
        serial_number="MV-SERIAL-001",
        pixel_format="mono8",
        exposure_us=12000,
        gain_db=2.5,
        timeout_ms=750,
        device_roi=DeviceRoiConfig(x=8, y=12, width=320, height=128),
        profile_name="measurement",
    )

    packet = camera.read_frame()
    camera.close()

    fake_camera = sdk_module.created_cameras[0]
    assert packet.meta["profile_name"] == "measurement"
    assert packet.meta["device_roi"] == {"x": 8, "y": 12, "width": 320, "height": 128}
    assert packet.meta["requested_device_roi"] == {"x": 8, "y": 12, "width": 320, "height": 128}
    assert fake_camera.configured_values["Width"] == 320
    assert fake_camera.configured_values["Height"] == 128
    assert fake_camera.configured_values["OffsetX"] == 8
    assert fake_camera.configured_values["OffsetY"] == 12


def test_default_factory_legalizes_measurement_roi_and_reports_applied_device_roi(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sdk_module = _FakeOfficialSdkModule(
        device_infos=[
            _FakeOfficialDeviceInfo(
                model="MV-CA060-11GM",
                serial_number="MV-SERIAL-001",
                ip="192.168.1.11",
                transport_code=_FakeOfficialSdkModule.MV_GIGE_DEVICE,
            )
        ],
        frame_rows=[[1, 2, 3], [4, 5, 6]],
        int_values={
            "Width": 3072,
            "Height": 2048,
            "OffsetX": 0,
            "OffsetY": 0,
        },
        int_descriptors={
            "Width": {"min": 64, "max": 3072, "inc": 8},
            "Height": {"min": 64, "max": 2048, "inc": 4},
            "OffsetX": {"min": 0, "max": 2752, "inc": 8},
            "OffsetY": {"min": 0, "max": 1920, "inc": 4},
        },
    )
    monkeypatch.setattr(hik_gige_mvs_module, "import_hik_mvs_sdk_module", lambda: sdk_module)

    camera = HikGigeMvsCamera(
        model="MV-CA060-11GM",
        transport="gige_vision",
        sdk_name="hik_mvs",
        serial_number="MV-SERIAL-001",
        pixel_format="mono8",
        timeout_ms=750,
        device_roi=DeviceRoiConfig(x=13, y=9, width=321, height=129),
        profile_name="measurement",
    )

    packet = camera.read_frame()
    camera.close()

    fake_camera = sdk_module.created_cameras[0]
    assert fake_camera.configured_values["Width"] == 320
    assert fake_camera.configured_values["Height"] == 128
    assert fake_camera.configured_values["OffsetX"] == 8
    assert fake_camera.configured_values["OffsetY"] == 8
    assert packet.meta["requested_device_roi"] == {"x": 13, "y": 9, "width": 321, "height": 129}
    assert packet.meta["device_roi"] == {"x": 8, "y": 8, "width": 320, "height": 128}
    assert camera.get_applied_device_roi() == DeviceRoiConfig(x=8, y=8, width=320, height=128)


def test_default_factory_resets_stale_device_roi_to_full_frame_when_measurement_roi_is_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sdk_module = _FakeOfficialSdkModule(
        device_infos=[
            _FakeOfficialDeviceInfo(
                model="MV-CA060-11GM",
                serial_number="MV-SERIAL-001",
                ip="192.168.1.11",
                transport_code=_FakeOfficialSdkModule.MV_GIGE_DEVICE,
            )
        ],
        frame_rows=[[1, 2], [3, 4]],
        int_values={
            "WidthMax": 3072,
            "HeightMax": 2048,
            "Width": 512,
            "Height": 512,
            "OffsetX": 128,
            "OffsetY": 64,
        },
    )
    monkeypatch.setattr(hik_gige_mvs_module, "import_hik_mvs_sdk_module", lambda: sdk_module)

    camera = HikGigeMvsCamera(
        model="MV-CA060-11GM",
        transport="gige_vision",
        sdk_name="hik_mvs",
        serial_number="MV-SERIAL-001",
        pixel_format="mono8",
        timeout_ms=750,
        profile_name="measurement",
    )

    camera.read_frame()
    camera.close()

    fake_camera = sdk_module.created_cameras[0]
    assert fake_camera.configured_values["OffsetX"] == 0
    assert fake_camera.configured_values["OffsetY"] == 0
    assert fake_camera.configured_values["Width"] == 3072
    assert fake_camera.configured_values["Height"] == 2048


def test_default_factory_applies_target_frame_rate_and_surfaces_hardware_frame_facts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sdk_module = _FakeOfficialSdkModule(
        device_infos=[
            _FakeOfficialDeviceInfo(
                model="MV-CA060-11GM",
                serial_number="MV-SERIAL-001",
                ip="192.168.1.11",
                transport_code=_FakeOfficialSdkModule.MV_GIGE_DEVICE,
            )
        ],
        frame_rows=[[1, 2], [3, 4]],
        float_values={
            "AcquisitionFrameRate": 17.78,
            "ResultingFrameRate": 17.78,
        },
        frame_number=41,
        frame_counter=41,
        lost_packet_count=3,
    )
    monkeypatch.setattr(hik_gige_mvs_module, "import_hik_mvs_sdk_module", lambda: sdk_module)

    camera = HikGigeMvsCamera(
        model="MV-CA060-11GM",
        transport="gige_vision",
        sdk_name="hik_mvs",
        serial_number="MV-SERIAL-001",
        pixel_format="mono8",
        timeout_ms=750,
        target_frame_rate_hz=50.0,
        profile_name="measurement",
    )

    packet = camera.read_frame()
    camera.close()

    fake_camera = sdk_module.created_cameras[0]
    assert fake_camera.configured_values["AcquisitionFrameRateEnable"] is True
    assert fake_camera.configured_values["AcquisitionFrameRate"] == 50.0
    assert packet.frame_id == 41
    assert packet.meta["camera_resulting_fps"] == 50.0
    assert packet.meta["camera_target_frame_rate_hz"] == 50.0
    assert packet.meta["camera_frame_counter"] == 41
    assert packet.meta["camera_lost_packet_count"] == 3
    assert packet.meta["target_frame_rate_hz"] == 50.0


def test_probe_once_supports_official_hik_sdk_module_in_first_discovered_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sdk_module = _FakeOfficialSdkModule(
        device_infos=[
            _FakeOfficialDeviceInfo(
                model="MV-CA060-11GM",
                serial_number="DISCOVERED-001",
                ip="192.168.1.12",
                transport_code=_FakeOfficialSdkModule.MV_GIGE_DEVICE,
            )
        ],
        frame_rows=[[9, 8], [7, 6]],
    )
    monkeypatch.setattr(hik_gige_mvs_module, "import_hik_mvs_sdk_module", lambda: sdk_module)

    camera = HikGigeMvsCamera(
        model="",
        transport="gige_vision",
        sdk_name="hik_mvs",
        serial_number="",
        ip="",
        timeout_ms=750,
    )

    payload = camera.probe_once(selection_mode="first_discovered")

    assert payload["matched_by"] == "first_discovered"
    assert payload["detected_model"] == "MV-CA060-11GM"
    assert payload["detected_serial_number"] == "DISCOVERED-001"
    assert payload["detected_ip"] == "192.168.1.12"
    assert payload["frame_shape"] == {"width": 2, "height": 2}


def test_official_hik_sdk_module_surfaces_selection_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    sdk_module = _FakeOfficialSdkModule(
        device_infos=[
            _FakeOfficialDeviceInfo(
                model="MV-CA060-11GM",
                serial_number="OTHER-DEVICE",
                ip="192.168.1.13",
                transport_code=_FakeOfficialSdkModule.MV_GIGE_DEVICE,
            )
        ],
        frame_rows=[[1]],
    )
    monkeypatch.setattr(hik_gige_mvs_module, "import_hik_mvs_sdk_module", lambda: sdk_module)

    camera = HikGigeMvsCamera(
        model="MV-CA060-11GM",
        transport="gige_vision",
        sdk_name="hik_mvs",
        serial_number="MV-SERIAL-001",
        timeout_ms=750,
    )

    with pytest.raises(RuntimeError, match="serial_number=MV-SERIAL-001"):
        camera.read_frame()
