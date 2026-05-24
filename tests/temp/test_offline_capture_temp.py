from pathlib import Path

from src.temp.offline_capture_temp import OfflineCaptureTempController


def _write_temperature_csv(capture_dir: Path) -> None:
    capture_dir.mkdir(parents=True)
    (capture_dir / "temperature.csv").write_text(
        "\n".join(
            [
                "frame_index,camera_timestamp_ms,temp_timestamp_ms,celsius,source,sampled_this_frame,error",
                "1,1000,1001,-0.5,lu92xx_modbus_rtu,1,",
                "2,1100,1001,-0.5,lu92xx_modbus_rtu,0,",
                "3,1200,1201,-0.4,lu92xx_modbus_rtu,1,",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_offline_capture_temp_holds_first_value_until_output_starts(tmp_path: Path) -> None:
    capture_dir = tmp_path / "fixture-capture"
    _write_temperature_csv(capture_dir)

    controller = OfflineCaptureTempController(capture_dir=capture_dir)

    assert controller.playback_sample_count() == 3
    assert controller.read().celsius == -0.5
    assert controller.read().celsius == -0.5

    controller.set_target_temperature(25.0)
    controller.set_output_power_percent(55.0)
    controller.start_output()

    assert controller.read_target_temperature() == 25.0
    assert controller.read_output_power_percent() == 55.0
    assert controller.read().celsius == -0.5
    assert controller.read().celsius == -0.5
    assert controller.read().celsius == -0.4

    controller.stop_output()

    assert controller.read_output_power_percent() == 0.0
    assert controller.read().celsius == -0.4
