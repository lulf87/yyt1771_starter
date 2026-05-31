import numpy as np
import pytest
import math

from src.core.models import FramePacket, MetricBox, PixelPoint, RectRegion
import src.vision.contour_direction as contour_direction
from src.vision.contour_direction import (
    DirectionalContourConfig,
    DirectionalContourDetectionError,
    DirectionalContourMetricExtractor,
    detect_directional_contour,
    project_component_mask_onto_direction,
    project_points_onto_direction,
)


def _point_in_rotated_metric_box(box: MetricBox, point: PixelPoint) -> bool:
    angle_rad = np.deg2rad(box.angle_deg)
    cos_theta = float(np.cos(angle_rad))
    sin_theta = float(np.sin(angle_rad))
    translated_x = float(point.x) - float(box.center_x)
    translated_y = float(point.y) - float(box.center_y)
    local_x = translated_x * cos_theta + translated_y * sin_theta
    local_y = -translated_x * sin_theta + translated_y * cos_theta
    return abs(local_x) <= float(box.width) / 2.0 and abs(local_y) <= float(box.height) / 2.0


def test_directional_contour_extracts_boundary_ab_from_main_component() -> None:
    image = np.full((12, 20), 240, dtype=np.uint8)
    image[4:7, 3:12] = 30
    config = DirectionalContourConfig(
        analysis_roi=RectRegion(x=0, y=0, width=20, height=12),
        direction_angle_deg=0.0,
        threshold_mode="binary",
        min_target_area_px=6,
    )

    result = detect_directional_contour(image, config)

    assert result.point_a.x == 3
    assert result.point_b.x == 11
    assert result.point_a.y == result.point_b.y == 5
    assert result.point_a == result.axis_point_a
    assert result.point_b == result.axis_point_b
    assert result.metric_raw == 8.0
    assert result.component_area >= 20


def test_directional_contour_config_defaults_match_offline_truth_ab_contract() -> None:
    config = DirectionalContourConfig(
        analysis_roi=RectRegion(x=0, y=0, width=2048, height=1364),
        direction_angle_deg=0.0,
    )

    assert config.foreground_polarity == "dark_on_light"
    assert config.threshold_mode == "adaptive"
    assert config.ignore_internal_texture is False
    assert config.min_target_area_px == 200
    assert config.projection_mode == "max_chord"


def test_envelope_max_width_line_bundle_uses_multi_component_union() -> None:
    image = np.full((120, 220), 240, dtype=np.uint8)
    image[49:52, 40:82] = 30
    image[49:52, 150:192] = 30
    image[64:67, 52:96] = 30
    image[64:67, 134:178] = 30

    result = detect_directional_contour(
        image,
        DirectionalContourConfig(
            analysis_roi=RectRegion(x=0, y=0, width=220, height=120),
            direction_angle_deg=0.0,
            threshold_mode="binary",
            threshold_value=100.0,
            foreground_polarity="dark_on_light",
            min_target_area_px=8,
            projection_mode="envelope_max_width",
            target_geometry_mode="line_bundle",
            side_guard_ratio=0.08,
            processing_max_side_px=0,
        ),
    )

    assert result.projection_point_mode == "envelope_max_width"
    assert result.target_geometry_mode == "line_bundle"
    assert result.point_a.x == pytest.approx(40, abs=1)
    assert result.point_b.x == pytest.approx(191, abs=1)
    assert result.point_a.y == pytest.approx(50, abs=1)
    assert result.point_b.y == pytest.approx(50, abs=1)
    assert result.metric_raw == pytest.approx(151.0, abs=2.0)
    assert result.selected_component_count >= 2
    assert result.envelope_candidate_count >= 2
    assert result.envelope_support_px >= 6


def test_envelope_max_width_default_unchanged_when_width_extreme_mode_missing() -> None:
    image = np.full((120, 220), 240, dtype=np.uint8)
    image[46:56, 40:141] = 30
    image[60:70, 72:133] = 30
    image[74:84, 55:136] = 30

    result = detect_directional_contour(
        image,
        DirectionalContourConfig(
            analysis_roi=RectRegion(x=0, y=0, width=220, height=120),
            direction_angle_deg=0.0,
            metric_box=MetricBox(center_x=110, center_y=60, width=190, height=80, angle_deg=0.0),
            threshold_mode="binary",
            threshold_value=100.0,
            foreground_polarity="dark_on_light",
            min_target_area_px=8,
            projection_mode="envelope_max_width",
            target_geometry_mode="line_bundle",
            envelope_min_support_px=3,
            envelope_endpoint_min_support_px=3,
            processing_max_side_px=0,
        ),
    )

    assert result.metric_raw == pytest.approx(100.0, abs=2.0)
    assert result.selected_width_extreme_mode == "max_width"


def test_envelope_min_width_selects_smallest_valid_band() -> None:
    image = np.full((120, 220), 240, dtype=np.uint8)
    image[49:53, 40:141] = 30  # span ~100
    image[63:67, 72:133] = 30  # span ~60
    image[77:81, 55:136] = 30  # span ~80

    result = detect_directional_contour(
        image,
        DirectionalContourConfig(
            analysis_roi=RectRegion(x=0, y=0, width=220, height=120),
            direction_angle_deg=0.0,
            metric_box=MetricBox(center_x=110, center_y=60, width=190, height=80, angle_deg=0.0),
            threshold_mode="binary",
            threshold_value=100.0,
            foreground_polarity="dark_on_light",
            min_target_area_px=8,
            projection_mode="envelope_max_width",
            width_extreme_mode="min_width",
            target_geometry_mode="line_bundle",
            envelope_min_support_px=3,
            envelope_endpoint_min_support_px=3,
            processing_max_side_px=0,
        ),
    )

    assert result.projection_point_mode == "envelope_max_width"
    assert result.metric_raw == pytest.approx(60.0, abs=2.0)
    assert result.selected_width_extreme_mode == "min_width"
    assert result.candidate_selection_goal == "min_span"
    assert result.min_width_valid_candidate_count >= 1
    assert result.max_width_valid_candidate_count >= 3

    max_result = detect_directional_contour(
        image,
        DirectionalContourConfig(
            analysis_roi=RectRegion(x=0, y=0, width=220, height=120),
            direction_angle_deg=0.0,
            metric_box=MetricBox(center_x=110, center_y=60, width=190, height=80, angle_deg=0.0),
            threshold_mode="binary",
            threshold_value=100.0,
            foreground_polarity="dark_on_light",
            min_target_area_px=8,
            projection_mode="envelope_max_width",
            width_extreme_mode="max_width",
            target_geometry_mode="line_bundle",
            envelope_min_support_px=3,
            envelope_endpoint_min_support_px=3,
            processing_max_side_px=0,
        ),
    )

    assert max_result.metric_raw == pytest.approx(100.0, abs=2.0)


def test_envelope_min_width_does_not_fallback_to_max() -> None:
    image = np.full((120, 220), 240, dtype=np.uint8)
    image[49:53, 40:141] = 30  # max candidate span ~100
    image[63:67, 72:133] = 30  # smaller candidate span ~60, below the configured floor

    max_result = detect_directional_contour(
        image,
        DirectionalContourConfig(
            analysis_roi=RectRegion(x=0, y=0, width=220, height=120),
            direction_angle_deg=0.0,
            metric_box=MetricBox(center_x=110, center_y=60, width=190, height=80, angle_deg=0.0),
            threshold_mode="binary",
            threshold_value=100.0,
            foreground_polarity="dark_on_light",
            min_target_area_px=8,
            projection_mode="envelope_max_width",
            width_extreme_mode="max_width",
            target_geometry_mode="line_bundle",
            envelope_min_support_px=3,
            envelope_endpoint_min_support_px=3,
            min_width_min_span_px=140.0,
            min_width_min_span_ratio=0.0,
            processing_max_side_px=0,
        ),
    )

    assert max_result.metric_raw == pytest.approx(100.0, abs=2.0)

    with pytest.raises(DirectionalContourDetectionError) as exc_info:
        detect_directional_contour(
            image,
            DirectionalContourConfig(
                analysis_roi=RectRegion(x=0, y=0, width=220, height=120),
                direction_angle_deg=0.0,
                metric_box=MetricBox(center_x=110, center_y=60, width=190, height=80, angle_deg=0.0),
                threshold_mode="binary",
                threshold_value=100.0,
                foreground_polarity="dark_on_light",
                min_target_area_px=8,
                projection_mode="envelope_max_width",
                width_extreme_mode="min_width",
                target_geometry_mode="line_bundle",
                envelope_min_support_px=3,
                envelope_endpoint_min_support_px=3,
                min_width_min_span_px=140.0,
                min_width_min_span_ratio=0.0,
                processing_max_side_px=0,
            ),
        )

    assert exc_info.value.reason == "min_width_no_effective_candidate"


def test_envelope_min_width_uses_relaxed_candidate_before_max() -> None:
    image = np.full((120, 220), 240, dtype=np.uint8)
    image[49:53, 40:141] = 30  # max candidate span ~100
    image[63:67, 72:133] = 30  # relaxed min candidate span ~60
    image[77:81, 55:136] = 30  # middle candidate span ~80

    result = detect_directional_contour(
        image,
        DirectionalContourConfig(
            analysis_roi=RectRegion(x=0, y=0, width=220, height=120),
            direction_angle_deg=0.0,
            metric_box=MetricBox(center_x=110, center_y=60, width=190, height=80, angle_deg=0.0),
            threshold_mode="binary",
            threshold_value=100.0,
            foreground_polarity="dark_on_light",
            min_target_area_px=8,
            projection_mode="envelope_max_width",
            width_extreme_mode="min_width",
            target_geometry_mode="line_bundle",
            envelope_min_support_px=3,
            envelope_endpoint_support_radius_px=1.0,
            envelope_endpoint_min_support_px=20,
            min_width_min_span_px=20.0,
            min_width_min_span_ratio=0.0,
            processing_max_side_px=0,
        ),
    )

    assert result.metric_raw == pytest.approx(60.0, abs=2.0)
    assert result.candidate_reject_reason == "min_width_relaxed_candidate"
    assert result.min_width_valid_candidate_count == 0
    assert result.min_width_relaxed_candidate_count >= 1


def test_envelope_min_width_meta_reports_candidate_counts() -> None:
    image = np.full((120, 220), 240, dtype=np.uint8)
    image[49:53, 40:141] = 30
    image[63:67, 72:133] = 30
    image[77:81, 55:136] = 30

    metric = DirectionalContourMetricExtractor(
        DirectionalContourConfig(
            analysis_roi=RectRegion(x=0, y=0, width=220, height=120),
            direction_angle_deg=0.0,
            metric_box=MetricBox(center_x=110, center_y=60, width=190, height=80, angle_deg=0.0),
            threshold_mode="binary",
            threshold_value=100.0,
            foreground_polarity="dark_on_light",
            min_target_area_px=8,
            projection_mode="envelope_max_width",
            width_extreme_mode="min_width",
            target_geometry_mode="line_bundle",
            envelope_min_support_px=3,
            envelope_endpoint_support_radius_px=1.0,
            envelope_endpoint_min_support_px=20,
            min_width_min_span_px=20.0,
            min_width_min_span_ratio=0.0,
            processing_max_side_px=0,
        )
    ).extract(FramePacket(timestamp_ms=1, source="fixture", image=image))

    assert metric.meta["min_width_valid_candidate_count"] == 0
    assert metric.meta["min_width_relaxed_candidate_count"] >= 1
    assert metric.meta["max_width_valid_candidate_count"] == 0
    assert metric.meta["min_width_reject_reason"] == "min_width_relaxed_candidate"
    assert metric.meta["candidate_reject_reason"] == "min_width_relaxed_candidate"
    assert metric.meta["effective_envelope_min_support_px"] == 12
    assert metric.meta["endpoint_support_left_px"] < 20
    assert metric.meta["endpoint_support_right_px"] < 20
    debug = metric.meta["envelope_candidate_debug"]
    assert debug["smallest"][0]["span"] == pytest.approx(60.0, abs=2.0)
    assert debug["largest"][0]["span"] == pytest.approx(100.0, abs=2.0)
    assert debug["smallest"][0]["endpoint_weak"] is True


def test_envelope_min_width_reports_span_floor_in_original_pixels_after_downscale() -> None:
    image = np.full((120, 220), 240, dtype=np.uint8)
    image[46:56, 40:141] = 30
    image[60:70, 72:133] = 30
    image[74:84, 55:136] = 30

    result = detect_directional_contour(
        image,
        DirectionalContourConfig(
            analysis_roi=RectRegion(x=0, y=0, width=220, height=120),
            direction_angle_deg=0.0,
            metric_box=MetricBox(center_x=110, center_y=60, width=190, height=80, angle_deg=0.0),
            threshold_mode="binary",
            threshold_value=100.0,
            foreground_polarity="dark_on_light",
            min_target_area_px=8,
            projection_mode="envelope_max_width",
            width_extreme_mode="min_width",
            target_geometry_mode="line_bundle",
            envelope_min_support_px=2,
            envelope_endpoint_min_support_px=2,
            min_width_min_span_px=10.0,
            min_width_min_span_ratio=0.0,
            processing_max_side_px=110,
        ),
    )

    assert result.metric_raw == pytest.approx(60.0, abs=4.0)
    assert result.candidate_span_floor_px == pytest.approx(10.0, abs=0.5)


def test_envelope_min_width_ignores_zero_or_tip_span() -> None:
    image = np.full((120, 220), 240, dtype=np.uint8)
    image[60:66, 72:133] = 30
    image[44:50, 102:104] = 30  # tip-like span below floor

    result = detect_directional_contour(
        image,
        DirectionalContourConfig(
            analysis_roi=RectRegion(x=0, y=0, width=220, height=120),
            direction_angle_deg=0.0,
            metric_box=MetricBox(center_x=110, center_y=60, width=190, height=80, angle_deg=0.0),
            threshold_mode="binary",
            threshold_value=100.0,
            foreground_polarity="dark_on_light",
            min_target_area_px=4,
            projection_mode="envelope_max_width",
            width_extreme_mode="min_width",
            target_geometry_mode="single_component",
            envelope_min_support_px=2,
            envelope_endpoint_min_support_px=2,
            min_width_min_span_px=5.0,
            processing_max_side_px=0,
        ),
    )

    assert result.metric_raw == pytest.approx(60.0, abs=2.0)
    assert result.candidate_span_floor_px >= 5.0
    assert result.envelope_reject_reason in {None, ""}


def test_envelope_min_width_requires_support() -> None:
    image = np.full((120, 220), 240, dtype=np.uint8)
    image[60:68, 72:133] = 30
    image[42:43, 90:111] = 30  # lower span, but support below floor

    result = detect_directional_contour(
        image,
        DirectionalContourConfig(
            analysis_roi=RectRegion(x=0, y=0, width=220, height=120),
            direction_angle_deg=0.0,
            metric_box=MetricBox(center_x=110, center_y=60, width=190, height=80, angle_deg=0.0),
            threshold_mode="binary",
            threshold_value=100.0,
            foreground_polarity="dark_on_light",
            min_target_area_px=1,
            projection_mode="envelope_max_width",
            width_extreme_mode="min_width",
            target_geometry_mode="single_component",
            envelope_min_support_px=4,
            envelope_endpoint_min_support_px=2,
            processing_max_side_px=0,
        ),
    )

    assert result.metric_raw == pytest.approx(60.0, abs=2.0)
    assert result.envelope_support_px >= 4


def test_envelope_min_width_rejects_debris() -> None:
    image = np.full((160, 240), 240, dtype=np.uint8)
    image[72:78, 72:133] = 30
    image[24:30, 86:107] = 30

    result = detect_directional_contour(
        image,
        DirectionalContourConfig(
            analysis_roi=RectRegion(x=0, y=0, width=240, height=160),
            direction_angle_deg=0.0,
            metric_box=MetricBox(center_x=120, center_y=80, width=200, height=110, angle_deg=0.0),
            threshold_mode="binary",
            threshold_value=100.0,
            foreground_polarity="dark_on_light",
            min_target_area_px=6,
            projection_mode="envelope_max_width",
            width_extreme_mode="min_width",
            target_geometry_mode="line_bundle",
            envelope_min_support_px=3,
            envelope_endpoint_min_support_px=2,
            processing_max_side_px=0,
        ),
    )

    assert result.metric_raw == pytest.approx(60.0, abs=2.0)
    assert result.rejected_component_count >= 1


def test_envelope_min_width_axis_projected_points_parallel() -> None:
    image = np.full((160, 240), 240, dtype=np.uint8)
    angle_deg = 18.0
    angle_rad = math.radians(angle_deg)
    center_x = 120
    center_y = 80
    for local_x in range(-30, 31):
        for local_y in range(-3, 4):
            world_x = int(round(center_x + local_x * math.cos(angle_rad) - local_y * math.sin(angle_rad)))
            world_y = int(round(center_y + local_x * math.sin(angle_rad) + local_y * math.cos(angle_rad)))
            if 0 <= world_x < image.shape[1] and 0 <= world_y < image.shape[0]:
                image[world_y, world_x] = 30

    metric = DirectionalContourMetricExtractor(
        DirectionalContourConfig(
            analysis_roi=RectRegion(x=0, y=0, width=240, height=160),
            direction_angle_deg=angle_deg,
            metric_box=MetricBox(center_x=120, center_y=80, width=170, height=90, angle_deg=angle_deg),
            threshold_mode="binary",
            threshold_value=100.0,
            foreground_polarity="dark_on_light",
            min_target_area_px=8,
            projection_mode="envelope_max_width",
            width_extreme_mode="min_width",
            target_geometry_mode="single_component",
            envelope_min_support_px=3,
            envelope_endpoint_min_support_px=2,
            processing_max_side_px=0,
        )
    ).extract(FramePacket(timestamp_ms=1, source="fixture", image=image))

    assert metric.metric_raw == pytest.approx(60.0, abs=3.0)
    assert metric.meta["display_point_mode"] == "axis_projected"
    assert metric.meta["source_point_mode"] == "foreground_support"
    assert metric.meta["metric_raw_mode"] == "along_axis_span"
    assert metric.meta["selected_width_extreme_mode"] == "min_width"
    dx = metric.point_b_px[0] - metric.point_a_px[0]
    dy = metric.point_b_px[1] - metric.point_a_px[1]
    observed_angle = math.degrees(math.atan2(dy, dx))
    assert observed_angle == pytest.approx(angle_deg, abs=3.0)


def test_envelope_max_width_line_bundle_rejects_horizontal_background_scratch() -> None:
    # A dense vertical-stack line bundle (filaments along the measurement
    # direction) plus a wide, thick horizontal scratch far above it. The scratch
    # spans more of the measurement direction than the real bundle width, so a
    # pure global envelope would put B on the scratch. The target-aware core band
    # must reject the laterally isolated scratch so A/B stays on the sample body.
    image = np.full((220, 280), 240, dtype=np.uint8)
    for top in (90, 100, 110, 120, 130, 140):
        image[top : top + 8, 40:171] = 30
    image[30:34, 20:240] = 30

    result = detect_directional_contour(
        image,
        DirectionalContourConfig(
            analysis_roi=RectRegion(x=0, y=0, width=280, height=220),
            direction_angle_deg=0.0,
            threshold_mode="binary",
            threshold_value=100.0,
            foreground_polarity="dark_on_light",
            min_target_area_px=20,
            projection_mode="envelope_max_width",
            target_geometry_mode="line_bundle",
            side_guard_ratio=0.05,
            component_bridge_kernel=1,
            open_kernel=1,
            processing_max_side_px=0,
        ),
    )

    assert result.projection_point_mode == "envelope_max_width"
    # The selected span is the real bundle width (~130 px), not the scratch (~220).
    assert result.metric_raw == pytest.approx(130.0, abs=8.0)
    assert result.point_b.x <= 176
    assert result.point_a.x == pytest.approx(40, abs=5)
    # A/B must stay inside the bundle body band, never on the top scratch row.
    assert result.point_a.y >= 80
    assert result.point_b.y >= 80
    assert result.rejected_component_count >= 1


def test_envelope_max_width_line_bundle_rejects_background_dot_on_the_side() -> None:
    # One genuine filament on the left plus an isolated background dot on the
    # upper right. The dot sits in a different lateral band, so it must not be
    # unioned into the envelope to fabricate a wide cross-background span.
    image = np.full((160, 240), 240, dtype=np.uint8)
    image[68:83, 40:111] = 30
    image[30:35, 180:189] = 30

    result = detect_directional_contour(
        image,
        DirectionalContourConfig(
            analysis_roi=RectRegion(x=0, y=0, width=240, height=160),
            direction_angle_deg=0.0,
            threshold_mode="binary",
            threshold_value=100.0,
            foreground_polarity="dark_on_light",
            min_target_area_px=20,
            projection_mode="envelope_max_width",
            target_geometry_mode="line_bundle",
            side_guard_ratio=0.05,
            component_bridge_kernel=1,
            open_kernel=1,
            processing_max_side_px=0,
        ),
    )

    assert result.projection_point_mode == "envelope_max_width"
    # Span stays on the real filament (~70 px), no cross-background blow-up.
    assert result.metric_raw == pytest.approx(70.0, abs=8.0)
    assert result.point_b.x <= 120
    assert result.point_a.y >= 60
    assert result.point_b.y >= 60
    assert result.rejected_component_count >= 1


def test_line_bundle_transient_debris_same_lateral_band_is_not_trusted_source() -> None:
    # The detached dark blob sits in the same lateral/normal band as the real
    # line bundle, but it is far away along the measurement direction. It must
    # not become source_point_a or stretch the accepted envelope.
    image = np.full((170, 260), 240, dtype=np.uint8)
    for top in (72, 82, 92):
        image[top : top + 5, 92:181] = 30
    image[78:88, 32:50] = 30

    result = detect_directional_contour(
        image,
        DirectionalContourConfig(
            analysis_roi=RectRegion(x=0, y=0, width=260, height=170),
            direction_angle_deg=0.0,
            metric_box=MetricBox(center_x=130, center_y=84, width=230, height=90, angle_deg=0.0),
            threshold_mode="binary",
            threshold_value=100.0,
            foreground_polarity="dark_on_light",
            min_target_area_px=20,
            projection_mode="envelope_max_width",
            target_geometry_mode="line_bundle",
            side_guard_ratio=0.02,
            component_bridge_kernel=1,
            open_kernel=1,
            processing_max_side_px=0,
        ),
    )

    assert result.metric_raw == pytest.approx(88.0, abs=8.0)
    assert result.source_point_a.x >= 85
    assert result.source_point_b.x <= 185
    assert result.envelope_source_trust_state == "trusted"
    assert result.source_point_a_trusted is True
    assert result.source_point_b_trusted is True
    assert result.rejected_component_count >= 1
    assert any("along_detached" in reason for reason in result.rejected_component_reasons)


def test_envelope_max_width_line_bundle_picks_widest_middle_over_dense_bottom() -> None:
    # A connected line bundle whose widest cross-section is on the middle/upper
    # band: outer filaments fan out there (x in [40, 170]). The lower band is
    # denser (more foreground pixels packed together) but narrower (x in
    # [70, 149]). A pure thin-bin global max can underestimate the sparse-but-wide
    # middle and snap A/B to the dense-but-narrow bottom. The robust envelope must
    # report the genuinely widest middle band instead.
    image = np.full((200, 240), 240, dtype=np.uint8)
    # Inner filaments span both bands so the whole bundle is one lateral cluster
    # and the bottom band is dense.
    for left in (70, 85, 100, 115, 130, 145):
        image[60:137, left : left + 4] = 30
    # Outer filaments only exist on the middle/upper band -> widest cross-section.
    image[60:87, 40:44] = 30
    image[60:87, 166:170] = 30

    result = detect_directional_contour(
        image,
        DirectionalContourConfig(
            analysis_roi=RectRegion(x=0, y=0, width=240, height=200),
            direction_angle_deg=0.0,
            threshold_mode="binary",
            threshold_value=100.0,
            foreground_polarity="dark_on_light",
            min_target_area_px=20,
            projection_mode="envelope_max_width",
            target_geometry_mode="line_bundle",
            side_guard_ratio=0.0,
            component_bridge_kernel=1,
            open_kernel=1,
            processing_max_side_px=0,
        ),
    )

    assert result.projection_point_mode == "envelope_max_width"
    # Widest middle band span (~129 px), not the dense bottom span (~79 px).
    assert result.metric_raw == pytest.approx(129.0, abs=8.0)
    assert result.point_a.x == pytest.approx(40, abs=5)
    assert result.point_b.x >= 160
    # Endpoints stay on the middle/upper band, never on the dense lower band.
    assert result.point_a.y <= 95
    assert result.point_b.y <= 95


def test_mesh_lattice_transient_scratch_same_lateral_band_is_rejected() -> None:
    image = np.full((180, 260), 240, dtype=np.uint8)
    # Real lattice body.
    image[72:76, 92:182] = 30
    image[98:102, 92:182] = 30
    image[124:128, 92:182] = 30
    for left in (92, 122, 152, 178):
        image[72:128, left : left + 4] = 30
    # Detached same-band scratch in the ROI background.
    image[96:104, 30:58] = 30

    result = detect_directional_contour(
        image,
        DirectionalContourConfig(
            analysis_roi=RectRegion(x=0, y=0, width=260, height=180),
            direction_angle_deg=0.0,
            metric_box=MetricBox(center_x=130, center_y=100, width=230, height=116, angle_deg=0.0),
            threshold_mode="binary",
            threshold_value=100.0,
            foreground_polarity="dark_on_light",
            min_target_area_px=20,
            projection_mode="envelope_max_width",
            target_geometry_mode="mesh_lattice",
            side_guard_ratio=0.02,
            component_bridge_kernel=1,
            open_kernel=1,
            processing_max_side_px=0,
        ),
    )

    assert result.metric_raw == pytest.approx(89.0, abs=8.0)
    assert result.source_point_a.x >= 85
    assert result.source_point_b.x <= 186
    assert result.envelope_source_trust_state == "trusted"
    assert result.rejected_component_count >= 1
    assert any("along_detached" in reason for reason in result.rejected_component_reasons)


def test_envelope_max_width_mesh_lattice_ignores_internal_holes() -> None:
    image = np.full((150, 240), 240, dtype=np.uint8)
    image[35:38, 54:186] = 30
    image[74:77, 54:186] = 30
    image[113:116, 54:186] = 30
    image[35:116, 54:58] = 30
    image[35:116, 92:96] = 30
    image[35:116, 144:148] = 30
    image[35:116, 182:186] = 30

    result = detect_directional_contour(
        image,
        DirectionalContourConfig(
            analysis_roi=RectRegion(x=0, y=0, width=240, height=150),
            direction_angle_deg=0.0,
            threshold_mode="binary",
            threshold_value=100.0,
            foreground_polarity="dark_on_light",
            min_target_area_px=10,
            projection_mode="envelope_max_width",
            target_geometry_mode="mesh_lattice",
            side_guard_ratio=0.10,
            processing_max_side_px=0,
        ),
    )

    assert result.projection_point_mode == "envelope_max_width"
    assert result.target_geometry_mode == "mesh_lattice"
    assert result.point_a.x == pytest.approx(54, abs=2)
    assert result.point_b.x == pytest.approx(185, abs=2)
    assert result.metric_raw == pytest.approx(131.0, abs=3.0)
    assert result.selected_component_count >= 1
    assert result.envelope_candidate_count >= 3
    assert result.envelope_support_px >= 8


def test_envelope_max_width_respects_rotated_roi_and_side_guard_noise() -> None:
    image = np.full((180, 240), 240, dtype=np.uint8)
    box = MetricBox(center_x=120, center_y=90, width=180, height=82, angle_deg=30.0)
    _paint_test_line_local(image, box, -66, -18, local_y=0.0, width=3, value=30)
    _paint_test_line_local(image, box, 18, 70, local_y=0.0, width=3, value=30)
    _paint_test_line_local(image, box, -82, -76, local_y=-30.0, width=5, value=30)
    _paint_test_line_local(image, box, 76, 84, local_y=28.0, width=5, value=30)

    result = detect_directional_contour(
        image,
        DirectionalContourConfig(
            analysis_roi=RectRegion(x=0, y=0, width=240, height=180),
            metric_box=box,
            direction_angle_deg=box.angle_deg,
            threshold_mode="binary",
            threshold_value=100.0,
            foreground_polarity="dark_on_light",
            min_target_area_px=8,
            projection_mode="envelope_max_width",
            target_geometry_mode="line_bundle",
            side_guard_ratio=0.12,
            processing_max_side_px=0,
        ),
    )

    local_a = _point_local_coords(box, result.point_a)
    local_b = _point_local_coords(box, result.point_b)
    assert local_a[0] == pytest.approx(-66, abs=2.5)
    assert local_b[0] == pytest.approx(70, abs=2.5)
    assert abs(local_a[1]) <= 2.5
    assert abs(local_b[1]) <= 2.5
    assert result.metric_raw == pytest.approx(136.0, abs=4.0)
    assert result.side_guard_foreground_area > 0
    assert result.envelope_candidate_count >= 1


def test_envelope_max_width_respects_60deg_rotated_roi() -> None:
    image = np.full((220, 260), 240, dtype=np.uint8)
    box = MetricBox(center_x=130, center_y=110, width=170, height=80, angle_deg=60.0)
    _paint_test_line_local(image, box, -60, -16, local_y=0.0, width=3, value=30)
    _paint_test_line_local(image, box, 16, 64, local_y=0.0, width=3, value=30)
    # Side-guard noise sits inside the core lateral band but at the longitudinal
    # ends, so it survives the lateral-cluster filter and must be removed by the
    # side guard rather than fabricating a wider A/B span.
    _paint_test_line_local(image, box, -78, -72, local_y=-8.0, width=5, value=30)
    _paint_test_line_local(image, box, 72, 80, local_y=8.0, width=5, value=30)

    result = detect_directional_contour(
        image,
        DirectionalContourConfig(
            analysis_roi=RectRegion(x=0, y=0, width=260, height=220),
            metric_box=box,
            direction_angle_deg=box.angle_deg,
            threshold_mode="binary",
            threshold_value=100.0,
            foreground_polarity="dark_on_light",
            min_target_area_px=8,
            projection_mode="envelope_max_width",
            target_geometry_mode="line_bundle",
            side_guard_ratio=0.12,
            processing_max_side_px=0,
        ),
    )

    local_a = _point_local_coords(box, result.point_a)
    local_b = _point_local_coords(box, result.point_b)
    assert local_a[0] == pytest.approx(-60, abs=3.0)
    assert local_b[0] == pytest.approx(64, abs=3.0)
    assert abs(local_a[1]) <= 3.0
    assert abs(local_b[1]) <= 3.0
    assert result.metric_raw == pytest.approx(124.0, abs=5.0)
    assert result.side_guard_foreground_area > 0


def _segment_angle_deg(point_a, point_b) -> float:
    return math.degrees(math.atan2(float(point_b.y - point_a.y), float(point_b.x - point_a.x)))


def _angle_diff_deg(angle_a: float, angle_b: float) -> float:
    delta = abs((float(angle_a) - float(angle_b)) % 180.0)
    return min(delta, 180.0 - delta)


def test_envelope_axis_projection_horizontal_ab_is_parallel() -> None:
    # Two filaments whose extreme foreground pixels sit at different rows. The
    # axis-projected A/B must still be perfectly horizontal (angle 0).
    image = np.full((120, 220), 240, dtype=np.uint8)
    image[40:46, 40:120] = 30
    image[70:76, 110:182] = 30

    result = detect_directional_contour(
        image,
        DirectionalContourConfig(
            analysis_roi=RectRegion(x=0, y=0, width=220, height=120),
            direction_angle_deg=0.0,
            metric_box=MetricBox(center_x=110, center_y=60, width=200, height=100, angle_deg=0.0),
            threshold_mode="binary",
            threshold_value=100.0,
            foreground_polarity="dark_on_light",
            min_target_area_px=8,
            projection_mode="envelope_max_width",
            target_geometry_mode="line_bundle",
            component_bridge_kernel=1,
            open_kernel=1,
            processing_max_side_px=0,
        ),
    )

    assert result.projection_point_mode == "envelope_max_width"
    assert _angle_diff_deg(_segment_angle_deg(result.point_a, result.point_b), 0.0) <= 1.0
    assert result.point_a.y == result.point_b.y
    assert result.point_a == result.axis_point_a
    assert result.point_b == result.axis_point_b


@pytest.mark.parametrize("box_angle", [10.0, 30.0])
def test_envelope_axis_projection_rotated_ab_matches_metric_box_angle(box_angle: float) -> None:
    image = np.full((240, 260), 240, dtype=np.uint8)
    box = MetricBox(center_x=130, center_y=120, width=180, height=90, angle_deg=box_angle)
    # Two filaments offset laterally so their extreme foreground pixels are not
    # collinear with the measurement axis; the displayed A/B must still align to
    # the metric box angle.
    _paint_test_line_local(image, box, -64, 0, local_y=-10.0, width=4, value=30)
    _paint_test_line_local(image, box, 0, 64, local_y=10.0, width=4, value=30)

    result = detect_directional_contour(
        image,
        DirectionalContourConfig(
            analysis_roi=RectRegion(x=0, y=0, width=260, height=240),
            metric_box=box,
            direction_angle_deg=box_angle,
            threshold_mode="binary",
            threshold_value=100.0,
            foreground_polarity="dark_on_light",
            min_target_area_px=8,
            projection_mode="envelope_max_width",
            target_geometry_mode="line_bundle",
            component_bridge_kernel=1,
            open_kernel=1,
            processing_max_side_px=0,
        ),
    )

    assert result.projection_point_mode == "envelope_max_width"
    assert _angle_diff_deg(_segment_angle_deg(result.point_a, result.point_b), box_angle) <= 1.0


def test_envelope_source_points_may_differ_but_display_points_stay_parallel() -> None:
    # Two filaments that fall in the same lateral measurement window but at
    # slightly different rows: the left filament is a few px higher than the right
    # one. The source extremes are therefore on a tilted segment, while the
    # axis-projected display segment must stay parallel to the measurement axis.
    image = np.full((120, 240), 240, dtype=np.uint8)
    image[40:44, 40:122] = 30
    image[50:54, 118:190] = 30

    result = detect_directional_contour(
        image,
        DirectionalContourConfig(
            analysis_roi=RectRegion(x=0, y=0, width=240, height=120),
            direction_angle_deg=0.0,
            metric_box=MetricBox(center_x=120, center_y=60, width=220, height=100, angle_deg=0.0),
            threshold_mode="binary",
            threshold_value=100.0,
            foreground_polarity="dark_on_light",
            min_target_area_px=8,
            projection_mode="envelope_max_width",
            target_geometry_mode="line_bundle",
            component_bridge_kernel=1,
            open_kernel=1,
            processing_max_side_px=0,
        ),
    )

    source_angle = _segment_angle_deg(result.source_point_a, result.source_point_b)
    display_angle = _segment_angle_deg(result.point_a, result.point_b)
    assert _angle_diff_deg(display_angle, 0.0) <= 1.0
    # The source support segment is meaningfully tilted off the axis here.
    assert _angle_diff_deg(source_angle, 0.0) > 2.0
    assert (result.point_a, result.point_b) == (result.axis_point_a, result.axis_point_b)


def test_envelope_uses_metric_box_angle_over_stale_direction_angle() -> None:
    # The metric box is the source of truth: a stale direction_angle_deg must not
    # change the measurement direction, and a mismatch is flagged in the result.
    image = np.full((240, 260), 240, dtype=np.uint8)
    box = MetricBox(center_x=130, center_y=120, width=180, height=90, angle_deg=30.0)
    _paint_test_line_local(image, box, -60, 0, local_y=0.0, width=4, value=30)
    _paint_test_line_local(image, box, 0, 60, local_y=0.0, width=4, value=30)

    result = detect_directional_contour(
        image,
        DirectionalContourConfig(
            analysis_roi=RectRegion(x=0, y=0, width=260, height=240),
            metric_box=box,
            direction_angle_deg=0.0,  # stale, disagrees with the box angle
            threshold_mode="binary",
            threshold_value=100.0,
            foreground_polarity="dark_on_light",
            min_target_area_px=8,
            projection_mode="envelope_max_width",
            target_geometry_mode="line_bundle",
            component_bridge_kernel=1,
            open_kernel=1,
            processing_max_side_px=0,
        ),
    )

    assert result.resolved_measurement_angle_deg == pytest.approx(30.0, abs=1e-6)
    assert result.angle_mismatch_warning is True
    assert result.angle_delta_deg == pytest.approx(30.0, abs=1e-6)
    assert _angle_diff_deg(_segment_angle_deg(result.point_a, result.point_b), 30.0) <= 1.0


def test_envelope_metric_meta_exposes_debug_fields() -> None:
    image = np.full((80, 160), 240, dtype=np.uint8)
    image[38:41, 32:68] = 30
    image[38:41, 96:132] = 30
    extractor = DirectionalContourMetricExtractor(
        DirectionalContourConfig(
            analysis_roi=RectRegion(x=0, y=0, width=160, height=80),
            direction_angle_deg=0.0,
            threshold_mode="binary",
            threshold_value=100.0,
            foreground_polarity="dark_on_light",
            min_target_area_px=6,
            projection_mode="envelope_max_width",
            target_geometry_mode="line_bundle",
            side_guard_ratio=0.10,
            processing_max_side_px=0,
        )
    )

    metric = extractor.extract(FramePacket(timestamp_ms=123, source="fixture", image=image))

    assert metric.metric_raw == pytest.approx(99.0, abs=2.0)
    assert metric.meta["target_geometry_mode"] == "line_bundle"
    assert metric.meta["projection_point_mode"] == "envelope_max_width"
    assert metric.meta["selected_component_count"] >= 2
    assert metric.meta["envelope_candidate_count"] >= 1
    assert metric.meta["side_guard_foreground_area"] == 0
    assert metric.meta["envelope_support_px"] >= 6
    assert metric.meta["axis_offset_px"] == pytest.approx(39.0, abs=1.0)


def _make_processing_geometry(
    *, roi_x: int, roi_y: int, scale: float
) -> contour_direction._ProcessingGeometry:
    width = max(1, int(round(160 * scale)))
    height = max(1, int(round(100 * scale)))
    return contour_direction._ProcessingGeometry(
        crop=np.zeros((height, width), dtype=np.uint8),
        original_roi=RectRegion(x=roi_x, y=roi_y, width=160, height=100),
        scale_x=scale,
        scale_y=scale,
    )


def test_envelope_axis_prior_roundtrip_nonzero_roi() -> None:
    # An original-frame axis offset must round-trip through the processing-space
    # conversion and back, even when the analysis ROI origin is non-zero. The
    # naive ``global * scale`` conversion (the old bug) must NOT match.
    geometry = _make_processing_geometry(roi_x=137, roi_y=211, scale=0.5)
    angle_deg = 0.0
    global_axis = 423.0

    processing_axis = contour_direction._axis_offset_to_processing_space(
        global_axis, geometry, angle_deg
    )
    restored_global = contour_direction._axis_offset_to_original_space(
        processing_axis, geometry, angle_deg
    )

    assert restored_global == pytest.approx(global_axis, abs=1e-6)
    # For angle 0 the normal is [0, 1] so origin.normal == roi_y == 211; the
    # processing-space prior is therefore (423 - 211) * 0.5 == 106, not 423*0.5.
    assert processing_axis == pytest.approx((global_axis - 211.0) * 0.5, abs=1e-6)
    assert abs(processing_axis - global_axis * geometry.scale) > 1.0


def test_envelope_axis_prior_nonzero_roi_lands_on_processing_lateral() -> None:
    # A foreground row 30 px into a downscaled ROI must map to processing-local
    # lateral 15 (= 30 * scale), not the global value.
    geometry = _make_processing_geometry(roi_x=40, roi_y=211, scale=0.5)
    global_axis = 211.0 + 30.0  # 30 px below the ROI top edge in original space

    processing_axis = contour_direction._axis_offset_to_processing_space(
        global_axis, geometry, 0.0
    )

    assert processing_axis == pytest.approx(15.0, abs=1e-6)


@pytest.mark.parametrize("global_axis", [-50.0, 0.0, 73.5, 512.0])
def test_envelope_axis_prior_roundtrip_rotated_25deg(global_axis: float) -> None:
    geometry = _make_processing_geometry(roi_x=88, roi_y=140, scale=0.5)
    angle_deg = 25.0

    processing_axis = contour_direction._axis_offset_to_processing_space(
        global_axis, geometry, angle_deg
    )
    restored_global = contour_direction._axis_offset_to_original_space(
        processing_axis, geometry, angle_deg
    )

    assert restored_global == pytest.approx(global_axis, abs=1e-6)


def test_envelope_source_points_debug_only_display_points_parallel() -> None:
    # Source (foreground support) points may be tilted off the axis, but the
    # displayed A/B is axis-projected and parallel. The meta must advertise both
    # modes so a debug overlay never mistakes a support point for the final A/B.
    image = np.full((120, 240), 240, dtype=np.uint8)
    image[40:44, 40:122] = 30
    image[50:54, 118:190] = 30
    extractor = DirectionalContourMetricExtractor(
        DirectionalContourConfig(
            analysis_roi=RectRegion(x=0, y=0, width=240, height=120),
            direction_angle_deg=0.0,
            metric_box=MetricBox(center_x=120, center_y=60, width=220, height=100, angle_deg=0.0),
            threshold_mode="binary",
            threshold_value=100.0,
            foreground_polarity="dark_on_light",
            min_target_area_px=8,
            projection_mode="envelope_max_width",
            target_geometry_mode="line_bundle",
            component_bridge_kernel=1,
            open_kernel=1,
            processing_max_side_px=0,
        )
    )

    metric = extractor.extract(FramePacket(timestamp_ms=1, source="fixture", image=image))

    display_a = PixelPoint(x=int(metric.point_a_px[0]), y=int(metric.point_a_px[1]))
    display_b = PixelPoint(x=int(metric.point_b_px[0]), y=int(metric.point_b_px[1]))
    source_a = PixelPoint(x=int(metric.meta["source_point_a_px"][0]), y=int(metric.meta["source_point_a_px"][1]))
    source_b = PixelPoint(x=int(metric.meta["source_point_b_px"][0]), y=int(metric.meta["source_point_b_px"][1]))

    assert metric.meta["display_point_mode"] == "axis_projected"
    assert metric.meta["source_point_mode"] == "foreground_support"
    assert metric.meta["metric_raw_mode"] == "along_axis_span"
    assert _angle_diff_deg(_segment_angle_deg(display_a, display_b), 0.0) <= 1.0
    # Source support spans different filament rows, so it is tilted off the axis.
    assert _angle_diff_deg(_segment_angle_deg(source_a, source_b), 0.0) > 2.0
    assert (display_a.x, display_a.y) != (source_a.x, source_a.y) or (
        display_b.x,
        display_b.y,
    ) != (source_b.x, source_b.y)


def test_mesh_lattice_effective_support_visible_or_respected() -> None:
    # A configured support of 3 is the "not customized" default; mesh_lattice
    # raises the effective floor to 20. Both values must be exposed so the UI can
    # show what the algorithm actually used instead of misleading the operator.
    assert contour_direction.resolve_envelope_min_support_px("mesh_lattice", 3) == 20

    image = np.full((120, 200), 240, dtype=np.uint8)
    image[40:80, 40:160] = 30  # solid block, plenty of per-bin support
    extractor = DirectionalContourMetricExtractor(
        DirectionalContourConfig(
            analysis_roi=RectRegion(x=0, y=0, width=200, height=120),
            direction_angle_deg=0.0,
            metric_box=MetricBox(center_x=100, center_y=60, width=180, height=100, angle_deg=0.0),
            threshold_mode="binary",
            threshold_value=100.0,
            foreground_polarity="dark_on_light",
            min_target_area_px=20,
            projection_mode="envelope_max_width",
            target_geometry_mode="mesh_lattice",
            envelope_min_support_px=3,
            component_bridge_kernel=1,
            open_kernel=1,
            processing_max_side_px=0,
        )
    )

    metric = extractor.extract(FramePacket(timestamp_ms=1, source="fixture", image=image))

    assert metric.meta["target_geometry_mode"] == "mesh_lattice"
    assert metric.meta["configured_envelope_min_support_px"] == 3
    assert metric.meta["effective_envelope_min_support_px"] == 20
    # The algorithm actually used the raised floor, so support must clear it.
    assert int(metric.meta["envelope_support_px"]) >= 20


def test_directional_contour_refines_downsampled_boundary_points_on_original_frame() -> None:
    image = np.full((120, 1000), 230, dtype=np.uint8)
    image[46:55, 123:877] = 20
    config = DirectionalContourConfig(
        analysis_roi=RectRegion(x=0, y=0, width=1000, height=120),
        direction_angle_deg=0.0,
        threshold_mode="binary",
        threshold_value=100.0,
        foreground_polarity="dark_on_light",
        min_target_area_px=20,
        processing_max_side_px=120,
        projection_mode="mask_projection",
    )

    result = detect_directional_contour(image, config)

    assert result.metric_raw == pytest.approx(753.0, abs=2.0)
    assert result.point_a.x == pytest.approx(123, abs=2)
    assert result.point_b.x == pytest.approx(876, abs=2)
    assert image[result.point_a.y, result.point_a.x] == 20
    assert image[result.point_b.y, result.point_b.x] == 20


def test_directional_contour_respects_rotated_metric_box_mask() -> None:
    image = np.full((120, 160), 240, dtype=np.uint8)
    metric_box = MetricBox(center_x=82, center_y=66, width=74, height=22, angle_deg=24.0)
    angle_rad = np.deg2rad(metric_box.angle_deg)
    cos_theta = float(np.cos(angle_rad))
    sin_theta = float(np.sin(angle_rad))

    # A longer distracting contour inside the axis-aligned analysis ROI but
    # outside the rotated ROI must not define A/B.
    image[14:18, 8:150] = 30

    for local_x in range(-31, 32):
        for local_y in range(-3, 4):
            world_x = int(round(metric_box.center_x + local_x * cos_theta - local_y * sin_theta))
            world_y = int(round(metric_box.center_y + local_x * sin_theta + local_y * cos_theta))
            if 0 <= world_x < image.shape[1] and 0 <= world_y < image.shape[0]:
                image[world_y, world_x] = 30

    result = detect_directional_contour(
        image,
        DirectionalContourConfig(
            analysis_roi=RectRegion(x=0, y=0, width=160, height=120),
            metric_box=metric_box,
            direction_angle_deg=metric_box.angle_deg,
            threshold_mode="binary",
            foreground_polarity="dark_on_light",
            min_target_area_px=20,
            sensitivity=0.0,
            projection_mode="mask_projection",
        ),
    )

    assert result.metric_raw == pytest.approx(62.0, abs=4.0)
    assert _point_in_rotated_metric_box_with_tolerance(metric_box, result.point_a)
    assert _point_in_rotated_metric_box_with_tolerance(metric_box, result.point_b)
    assert result.point_a.y > 40
    assert result.point_b.y > 40


def test_directional_contour_uses_requested_direction_not_world_extremes() -> None:
    points = np.array(
        [
            [4.0, 12.0],
            [7.0, 9.0],
            [10.0, 6.0],
            [13.0, 3.0],
        ],
        dtype=float,
    )

    projection = project_points_onto_direction(points, -45.0, image_shape=(20, 20))

    assert projection.point_a.x == 4
    assert projection.point_a.y == 12
    assert projection.point_b.x == 13
    assert projection.point_b.y == 3
    assert projection.metric_raw > 12.0


def test_direction_selection_returns_contour_extrema_without_axis_projection() -> None:
    points = np.array(
        [
            [30.0, 0.0],
            [31.0, 0.0],
            [10.0, 60.0],
            [11.0, 60.0],
            [40.0, 30.0],
        ],
        dtype=float,
    )

    projection = project_points_onto_direction(points, 90.0, image_shape=(80, 80))

    assert (projection.point_a.x, projection.point_a.y) == (30, 0)
    assert (projection.point_b.x, projection.point_b.y) == (10, 60)
    assert (projection.source_point_a.x, projection.source_point_a.y) == (30, 0)
    assert (projection.source_point_b.x, projection.source_point_b.y) == (10, 60)
    assert projection.axis_point_a == projection.point_a
    assert projection.axis_point_b == projection.point_b
    assert projection.metric_raw == pytest.approx(np.hypot(20.0, 60.0))


def test_directional_ab_points_are_contour_points_not_axis_projections() -> None:
    points = np.array(
        [
            [30.0, 0.0],
            [31.0, 0.0],
            [10.0, 60.0],
            [11.0, 60.0],
            [40.0, 30.0],
        ],
        dtype=float,
    )

    projection = project_points_onto_direction(points, 90.0, image_shape=(80, 80))

    assert projection.point_a == projection.source_point_a
    assert projection.point_b == projection.source_point_b
    assert (projection.point_a.x, projection.point_a.y) == (30, 0)
    assert (projection.point_b.x, projection.point_b.y) == (10, 60)


def test_direction_selection_does_not_create_parallel_axis_points() -> None:
    points = np.array(
        [
            [163.0, 129.0],
            [457.0, 131.0],
            [320.0, 260.0],
            [345.0, 60.0],
        ],
        dtype=float,
    )

    projection = project_points_onto_direction(points, -70.0, image_shape=(320, 520))
    assert projection.point_a == projection.source_point_a
    assert projection.point_b == projection.source_point_b
    assert projection.axis_point_a == projection.point_a
    assert projection.axis_point_b == projection.point_b


def test_directional_contour_uses_contour_boundary_points_for_oblique_direction() -> None:
    image = np.full((90, 140), 240, dtype=np.uint8)
    yy, xx = np.mgrid[0 : image.shape[0], 0 : image.shape[1]]
    body = ((xx - 70.0) / 42.0) ** 2 + ((yy - 45.0) / 14.0) ** 2 <= 1.0
    image[body] = 30
    config = DirectionalContourConfig(
        analysis_roi=RectRegion(x=0, y=0, width=140, height=90),
        direction_angle_deg=-25.0,
        threshold_mode="binary",
        foreground_polarity="dark_on_light",
        min_target_area_px=80,
        sensitivity=0.0,
        projection_mode="mask_projection",
    )

    result = detect_directional_contour(image, config)
    assert result.point_a == result.source_point_a == result.axis_point_a
    assert result.point_b == result.source_point_b == result.axis_point_b
    assert image[result.point_a.y, result.point_a.x] == 30
    assert image[result.point_b.y, result.point_b.x] == 30
    assert result.projection_point_mode == "mask_projection"


def test_directional_contour_max_chord_finds_widest_parallel_contour_section() -> None:
    image = np.full((160, 240), 240, dtype=np.uint8)
    yy, xx = np.mgrid[0 : image.shape[0], 0 : image.shape[1]]
    body = ((xx - 120.0) / 70.0) ** 2 + ((yy - 80.0) / 22.0) ** 2 <= 1.0
    image[body] = 30
    config = DirectionalContourConfig(
        analysis_roi=RectRegion(x=20, y=35, width=200, height=90),
        direction_angle_deg=-70.0,
        threshold_mode="binary",
        foreground_polarity="dark_on_light",
        min_target_area_px=400,
        sensitivity=0.0,
        projection_mode="max_chord",
    )

    result = detect_directional_contour(image, config)
    same_direction_selection = project_component_mask_onto_direction(
        result.component_mask,
        result.roi,
        -70.0,
        image_shape=image.shape,
        clip_region=result.roi,
    )
    direction = contour_direction.directional_unit_vector(-70.0)
    normal = np.array([-direction[1], direction[0]], dtype=float)
    displayed = np.array(
        [
            result.point_b.x - result.point_a.x,
            result.point_b.y - result.point_a.y,
        ],
        dtype=float,
    )
    displayed /= np.linalg.norm(displayed)
    source_a = np.array([result.source_point_a.x, result.source_point_a.y], dtype=float)
    source_b = np.array([result.source_point_b.x, result.source_point_b.y], dtype=float)

    cross = float(direction[0] * displayed[1] - direction[1] * displayed[0])
    assert abs(cross) < 0.04
    assert abs(float(source_a @ normal) - float(source_b @ normal)) <= 3.0
    assert image[result.source_point_a.y, result.source_point_a.x] == 30
    assert image[result.source_point_b.y, result.source_point_b.x] == 30
    assert result.metric_raw == pytest.approx(same_direction_selection.metric_raw, abs=5.0)
    assert result.projection_point_mode == "max_chord"


def test_directional_contour_max_chord_can_follow_axis_prior() -> None:
    image = np.full((70, 110), 230, dtype=np.uint8)
    image[20:24, 24:84] = 35
    image[42:46, 6:104] = 35
    image[20:46, 52:56] = 35
    config = DirectionalContourConfig(
        analysis_roi=RectRegion(x=0, y=0, width=110, height=70),
        direction_angle_deg=0.0,
        foreground_polarity="dark_on_light",
        threshold_mode="binary",
        threshold_value=100.0,
        min_target_area_px=20,
        sensitivity=0.0,
        ignore_internal_texture=False,
        component_bridge_kernel=1,
        open_kernel=1,
        projection_mode="max_chord",
        max_chord_axis_prior_point=PixelPoint(x=54, y=22),
        max_chord_axis_prior_tolerance_px=6.0,
        processing_max_side_px=0,
    )

    result = detect_directional_contour(image, config)

    assert result.metric_raw < 70
    assert abs(result.point_a.y - 22) <= 1
    assert abs(result.point_b.y - 22) <= 1
    assert result.projection_point_mode == "max_chord"


def test_directional_contour_mask_mode_keeps_ab_on_detected_object_with_off_object_prior() -> None:
    image = np.full((70, 110), 230, dtype=np.uint8)
    image[42:46, 6:104] = 35
    config = DirectionalContourConfig(
        analysis_roi=RectRegion(x=0, y=0, width=110, height=70),
        direction_angle_deg=0.0,
        foreground_polarity="dark_on_light",
        threshold_mode="binary",
        threshold_value=100.0,
        min_target_area_px=20,
        sensitivity=0.0,
        ignore_internal_texture=False,
        component_bridge_kernel=1,
        open_kernel=1,
        projection_mode="mask_projection",
        max_chord_axis_prior_point=PixelPoint(x=54, y=22),
        max_chord_axis_prior_tolerance_px=8.0,
        processing_max_side_px=0,
    )

    result = detect_directional_contour(image, config)

    assert result.metric_raw >= 95.0
    assert result.projection_point_mode == "mask_projection"
    assert result.point_a == result.source_point_a == result.axis_point_a
    assert result.point_b == result.source_point_b == result.axis_point_b
    assert result.point_a.y >= 42
    assert result.point_b.y >= 42


def test_directional_contour_mask_projection_uses_prior_band_for_source_extrema() -> None:
    image = np.full((70, 110), 230, dtype=np.uint8)
    image[20:24, 24:84] = 35
    image[42:46, 6:104] = 35
    image[20:46, 52:56] = 35
    config = DirectionalContourConfig(
        analysis_roi=RectRegion(x=0, y=0, width=110, height=70),
        direction_angle_deg=0.0,
        foreground_polarity="dark_on_light",
        threshold_mode="binary",
        threshold_value=100.0,
        min_target_area_px=20,
        sensitivity=0.0,
        ignore_internal_texture=False,
        component_bridge_kernel=1,
        open_kernel=1,
        projection_mode="mask_projection",
        max_chord_axis_prior_point=PixelPoint(x=54, y=22),
        max_chord_axis_prior_tolerance_px=6.0,
        processing_max_side_px=0,
    )

    result = detect_directional_contour(image, config)

    assert result.metric_raw < 70.0
    assert abs(result.point_a.y - 22) <= 1
    assert abs(result.point_b.y - 22) <= 1
    assert abs(result.source_point_a.y - 22) <= 3
    assert abs(result.source_point_b.y - 22) <= 3
    assert 20 <= result.source_point_a.x <= 28
    assert 80 <= result.source_point_b.x <= 88


def test_directional_contour_refinement_keeps_axis_prior_in_original_roi_coordinates() -> None:
    image = np.full((240, 320), 230, dtype=np.uint8)
    image[108:116, 90:170] = 35
    image[148:156, 70:250] = 35
    image[108:156, 148:156] = 35
    config = DirectionalContourConfig(
        analysis_roi=RectRegion(x=50, y=80, width=240, height=120),
        direction_angle_deg=0.0,
        foreground_polarity="dark_on_light",
        threshold_mode="binary",
        threshold_value=100.0,
        min_target_area_px=5,
        sensitivity=0.0,
        ignore_internal_texture=False,
        component_bridge_kernel=1,
        open_kernel=1,
        projection_mode="mask_projection",
        max_chord_axis_prior_point=PixelPoint(x=130, y=112),
        max_chord_axis_prior_tolerance_px=8.0,
        processing_max_side_px=80,
    )

    result = detect_directional_contour(image, config)

    assert result.metric_raw < 100.0
    assert abs(result.point_a.y - 112) <= 2
    assert abs(result.point_b.y - 112) <= 2
    assert image[result.point_a.y, result.point_a.x] == 35
    assert image[result.point_b.y, result.point_b.x] == 35


def test_directional_contour_refinement_keeps_points_inside_rotated_metric_box() -> None:
    image = np.full((800, 1000), 230, dtype=np.uint8)
    metric_box = MetricBox(center_x=500, center_y=350, width=400, height=160, angle_deg=150.0)
    _paint_test_line_local(image, metric_box, -190.0, 310.0, width=17, value=35)
    config = DirectionalContourConfig(
        analysis_roi=RectRegion(x=100, y=80, width=800, height=640),
        metric_box=metric_box,
        direction_angle_deg=150.0,
        foreground_polarity="dark_on_light",
        threshold_mode="binary",
        threshold_value=100.0,
        min_target_area_px=2,
        sensitivity=0.0,
        ignore_internal_texture=False,
        component_bridge_kernel=1,
        open_kernel=1,
        projection_mode="mask_projection",
        processing_max_side_px=120,
    )

    result = detect_directional_contour(image, config)

    assert _point_in_rotated_metric_box_with_tolerance(metric_box, result.point_a)
    assert _point_in_rotated_metric_box_with_tolerance(metric_box, result.point_b)
    assert image[result.point_a.y, result.point_a.x] == 35
    assert image[result.point_b.y, result.point_b.x] == 35


def test_directional_contour_downsampled_refinement_avoids_second_full_component_pass(monkeypatch) -> None:
    image = np.full((800, 1000), 230, dtype=np.uint8)
    metric_box = MetricBox(center_x=500, center_y=350, width=420, height=160, angle_deg=30.0)
    _paint_test_line_local(image, metric_box, -190.0, 190.0, width=15, value=35)
    calls = 0
    original = contour_direction._largest_component_mask

    def counted_largest_component_mask(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(contour_direction, "_largest_component_mask", counted_largest_component_mask)

    result = detect_directional_contour(
        image,
        DirectionalContourConfig(
            analysis_roi=RectRegion(x=240, y=80, width=520, height=540),
            metric_box=metric_box,
            direction_angle_deg=30.0,
            threshold_mode="binary",
            threshold_value=100.0,
            foreground_polarity="dark_on_light",
            min_target_area_px=20,
            sensitivity=0.0,
            component_bridge_kernel=1,
            processing_max_side_px=120,
            projection_mode="max_chord",
        ),
    )

    assert calls == 1
    assert image[result.point_a.y, result.point_a.x] == 35
    assert image[result.point_b.y, result.point_b.x] == 35


def test_directional_contour_quality_uses_rotated_metric_box_reference() -> None:
    image = np.full((800, 1000), 230, dtype=np.uint8)
    metric_box = MetricBox(center_x=500, center_y=350, width=420, height=160, angle_deg=30.0)
    _paint_test_line_local(image, metric_box, -190.0, 190.0, width=15, value=35)
    config = DirectionalContourConfig(
        analysis_roi=RectRegion(x=240, y=80, width=520, height=540),
        metric_box=metric_box,
        direction_angle_deg=30.0,
        foreground_polarity="dark_on_light",
        threshold_mode="binary",
        threshold_value=100.0,
        min_target_area_px=20,
        sensitivity=0.0,
        ignore_internal_texture=False,
        component_bridge_kernel=1,
        open_kernel=1,
        projection_mode="mask_projection",
        processing_max_side_px=0,
    )

    result = detect_directional_contour(image, config)

    assert result.metric_raw >= 360.0
    assert result.quality >= 0.75


def test_directional_contour_quality_accepts_valid_object_smaller_than_roi_box() -> None:
    image = np.full((800, 1000), 230, dtype=np.uint8)
    metric_box = MetricBox(center_x=500, center_y=350, width=420, height=360, angle_deg=90.0)
    _paint_test_line_local(image, metric_box, -120.0, 120.0, width=13, value=35)
    config = DirectionalContourConfig(
        analysis_roi=RectRegion(x=300, y=120, width=400, height=520),
        metric_box=metric_box,
        direction_angle_deg=90.0,
        foreground_polarity="dark_on_light",
        threshold_mode="binary",
        threshold_value=100.0,
        min_target_area_px=20,
        sensitivity=0.0,
        ignore_internal_texture=False,
        component_bridge_kernel=1,
        open_kernel=1,
        projection_mode="mask_projection",
        processing_max_side_px=0,
    )

    result = detect_directional_contour(image, config)

    assert 230.0 <= result.metric_raw <= 260.0
    assert result.quality >= 0.75


def test_directional_contour_auto_selects_max_chord_for_wide_component() -> None:
    image = np.full((160, 240), 240, dtype=np.uint8)
    yy, xx = np.mgrid[0 : image.shape[0], 0 : image.shape[1]]
    body = ((xx - 120.0) / 70.0) ** 2 + ((yy - 80.0) / 22.0) ** 2 <= 1.0
    image[body] = 30
    config = DirectionalContourConfig(
        analysis_roi=RectRegion(x=20, y=35, width=200, height=90),
        direction_angle_deg=-70.0,
        threshold_mode="binary",
        foreground_polarity="dark_on_light",
        min_target_area_px=400,
        sensitivity=0.0,
        projection_mode="auto",
    )

    result = detect_directional_contour(image, config)

    assert result.projection_point_mode == "max_chord"
    assert 40.0 <= result.metric_raw <= 50.0


def test_directional_contour_auto_uses_mask_projection_for_textured_mesh_component() -> None:
    image = np.full((96, 160), 240, dtype=np.uint8)
    image[30:33, 24:136] = 30
    image[62:65, 24:136] = 30
    image[30:65, 24:27] = 30
    image[30:65, 133:136] = 30
    for x in range(36, 128, 12):
        image[33:62, x : x + 3] = 30
    for offset in range(0, 84, 14):
        for step in range(28):
            x = 30 + offset + step
            y = 34 + step
            if 24 <= x < 136 and 30 <= y < 65:
                image[y : y + 2, x : x + 2] = 30

    config = DirectionalContourConfig(
        analysis_roi=RectRegion(x=10, y=20, width=140, height=60),
        direction_angle_deg=0.0,
        threshold_mode="binary",
        foreground_polarity="dark_on_light",
        min_target_area_px=200,
        sensitivity=50.0,
        ignore_internal_texture=True,
        component_bridge_kernel=11,
        projection_mode="auto",
    )

    result = detect_directional_contour(image, config)

    assert result.projection_point_mode == "mask_projection"
    assert result.metric_raw >= 108.0
    assert result.point_a.x <= 28
    assert result.point_b.x >= 132


def test_component_mask_direction_selection_uses_real_boundary_points() -> None:
    mask = np.zeros((64, 128), dtype=np.uint8)
    mask[20:41, 20:80] = 255
    mask[26, 80] = 255
    roi = RectRegion(x=0, y=0, width=128, height=64)

    projection = project_component_mask_onto_direction(mask, roi, -20.0, image_shape=mask.shape)
    direction = contour_direction.directional_unit_vector(-20.0)
    displayed = np.array(
        [
            projection.point_b.x - projection.point_a.x,
            projection.point_b.y - projection.point_a.y,
        ],
        dtype=float,
    )
    displayed /= np.linalg.norm(displayed)
    cross = float(direction[0] * displayed[1] - direction[1] * displayed[0])

    assert abs(cross) < 0.04
    assert projection.point_a == projection.axis_point_a
    assert projection.point_b == projection.axis_point_b
    assert mask[projection.source_point_a.y, projection.source_point_a.x] == 255
    assert mask[projection.source_point_b.y, projection.source_point_b.x] == 255
    assert projection.metric_raw >= 60.0


def test_directional_contour_uses_real_chord_points_for_oblique_wire_like_shape() -> None:
    image = np.full((110, 150), 240, dtype=np.uint8)
    _paint_test_line(image, (22, 78), (86, 48), width=11, value=30)
    _paint_test_line(image, (86, 48), (90, 12), width=11, value=30)
    config = DirectionalContourConfig(
        analysis_roi=RectRegion(x=0, y=0, width=150, height=110),
        direction_angle_deg=-10.0,
        threshold_mode="binary",
        foreground_polarity="dark_on_light",
        min_target_area_px=80,
        sensitivity=0.0,
        component_bridge_kernel=1,
        projection_mode="mask_projection",
    )

    result = detect_directional_contour(image, config)

    assert result.projection_point_mode == "mask_projection"
    assert result.metric_raw > 50.0
    assert abs(result.point_b.y - result.point_a.y) <= 20
    assert image[result.point_a.y, result.point_a.x] == 30
    assert image[result.point_b.y, result.point_b.x] == 30


def test_directional_contour_auto_selects_mask_projection_for_wire_like_shape() -> None:
    image = np.full((110, 150), 240, dtype=np.uint8)
    _paint_test_line(image, (22, 78), (86, 48), width=11, value=30)
    _paint_test_line(image, (86, 48), (90, 12), width=11, value=30)
    config = DirectionalContourConfig(
        analysis_roi=RectRegion(x=0, y=0, width=150, height=110),
        direction_angle_deg=-10.0,
        threshold_mode="binary",
        foreground_polarity="dark_on_light",
        min_target_area_px=80,
        sensitivity=0.0,
        component_bridge_kernel=1,
        projection_mode="auto",
    )

    result = detect_directional_contour(image, config)

    assert result.projection_point_mode == "max_chord"
    assert result.metric_raw > 50.0
    assert abs(result.point_b.y - result.point_a.y) <= 20
    assert image[result.point_a.y, result.point_a.x] == 30
    assert image[result.point_b.y, result.point_b.x] == 30


def test_direction_selection_clips_boundary_points_to_roi() -> None:
    points = np.array(
        [
            [0.0, 598.0],
            [859.0, 220.0],
        ],
        dtype=float,
    )
    roi = RectRegion(x=0, y=220, width=860, height=380)

    projection = project_points_onto_direction(points, -18.0, image_shape=(620, 1120), clip_region=roi)

    assert roi.x <= projection.point_a.x < roi.x + roi.width
    assert roi.y <= projection.point_a.y < roi.y + roi.height
    assert roi.x <= projection.point_b.x < roi.x + roi.width
    assert roi.y <= projection.point_b.y < roi.y + roi.height
    assert projection.metric_raw > 900.0


def test_directional_contour_selects_largest_component_inside_roi() -> None:
    image = np.full((16, 28), 240, dtype=np.uint8)
    image[2:4, 2:5] = 30
    image[7:11, 12:23] = 30
    config = DirectionalContourConfig(
        analysis_roi=RectRegion(x=0, y=0, width=28, height=16),
        direction_angle_deg=0.0,
        threshold_mode="binary",
        min_target_area_px=8,
    )

    result = detect_directional_contour(image, config)

    assert result.point_a.x == 12
    assert result.point_b.x == 22
    assert result.component_area > 30


def test_directional_contour_bridges_nearby_fragments_for_boundary_span() -> None:
    image = np.full((24, 56), 240, dtype=np.uint8)
    image[9:14, 6:20] = 30
    image[9:14, 28:44] = 30
    config = DirectionalContourConfig(
        analysis_roi=RectRegion(x=0, y=0, width=56, height=24),
        direction_angle_deg=0.0,
        threshold_mode="binary",
        foreground_polarity="dark_on_light",
        min_target_area_px=20,
        sensitivity=0.0,
    )

    result = detect_directional_contour(image, config)

    assert result.point_a.x == 6
    assert result.point_b.x == 43
    assert result.metric_raw == pytest.approx(37.0, abs=1.0)


def test_directional_contour_prefers_supported_boundary_chord_over_fake_diagonal_span() -> None:
    image = np.full((64, 72), 240, dtype=np.uint8)
    image[0:31, 34:45] = 30
    image[33:45, 10:28] = 30
    config = DirectionalContourConfig(
        analysis_roi=RectRegion(x=0, y=0, width=72, height=64),
        direction_angle_deg=90.0,
        threshold_mode="binary",
        foreground_polarity="dark_on_light",
        min_target_area_px=80,
        sensitivity=0.0,
        projection_mode="mask_projection",
    )

    result = detect_directional_contour(image, config)

    assert result.point_a.y == 0
    assert result.point_b.y == 30
    assert result.metric_raw == 30.0
    assert image[result.point_a.y, result.point_a.x] == 30
    assert image[result.point_b.y, result.point_b.x] == 30


def test_directional_contour_rejects_projected_distal_gap_as_ab_span() -> None:
    image = np.full((72, 72), 240, dtype=np.uint8)
    image[0:36, 34:50] = 30
    image[49:60, 8:22] = 30
    config = DirectionalContourConfig(
        analysis_roi=RectRegion(x=0, y=0, width=72, height=72),
        direction_angle_deg=90.0,
        threshold_mode="binary",
        foreground_polarity="dark_on_light",
        min_target_area_px=80,
        sensitivity=0.0,
        projection_mode="mask_projection",
    )

    result = detect_directional_contour(image, config)

    assert result.point_a.y == 0
    assert result.point_b.y == 35
    assert result.metric_raw == 35.0
    assert image[result.point_a.y, result.point_a.x] == 30
    assert image[result.point_b.y, result.point_b.x] == 30


def test_directional_contour_preserves_thin_connected_wire_segments() -> None:
    image = np.full((80, 80), 240, dtype=np.uint8)
    image[0:20, 52:62] = 30
    image[62:72, 4:16] = 30
    for index, y in enumerate(range(20, 62)):
        x = 52 - index
        if 12 <= x < 52:
            image[y, x] = 30
    config = DirectionalContourConfig(
        analysis_roi=RectRegion(x=0, y=0, width=80, height=80),
        direction_angle_deg=90.0,
        threshold_mode="binary",
        threshold_value=200.0,
        foreground_polarity="dark_on_light",
        min_target_area_px=80,
        sensitivity=50.0,
        component_bridge_kernel=1,
        projection_mode="mask_projection",
    )

    result = detect_directional_contour(image, config)

    assert result.point_a.y == 0
    assert result.point_b.y >= 19
    assert result.metric_raw >= 19.0
    assert image[result.point_a.y, result.point_a.x] == 30
    assert image[result.point_b.y, result.point_b.x] == 30


def test_directional_contour_quality_accepts_valid_thin_wire_span() -> None:
    image = np.full((120, 160), 240, dtype=np.uint8)
    image[58:63, 20:141] = 30
    config = DirectionalContourConfig(
        analysis_roi=RectRegion(x=0, y=0, width=160, height=120),
        direction_angle_deg=0.0,
        threshold_mode="binary",
        foreground_polarity="dark_on_light",
        min_target_area_px=80,
        sensitivity=0.0,
    )

    result = detect_directional_contour(image, config)

    assert result.metric_raw >= 120.0
    assert result.quality >= 0.75


def test_directional_contour_without_cv2_handles_large_roi(monkeypatch) -> None:
    monkeypatch.setattr(contour_direction, "_try_import_cv2", lambda: None)
    image = np.full((480, 640), 245, dtype=np.uint8)
    image[130:410, 80:560] = 35
    image[190:260, 220:420] = 180
    config = DirectionalContourConfig(
        analysis_roi=RectRegion(x=20, y=80, width=580, height=360),
        direction_angle_deg=0.0,
        threshold_mode="binary",
        foreground_polarity="dark_on_light",
        min_target_area_px=500,
        ignore_internal_texture=True,
    )

    result = detect_directional_contour(image, config)

    assert result.point_a.x == 80
    assert result.point_b.x == 559
    assert result.metric_raw == 479.0
    assert result.component_area > 120_000


def test_directional_contour_keeps_projected_ab_inside_roi() -> None:
    image = np.full((40, 60), 240, dtype=np.uint8)
    for y in range(18, 34):
        start_x = max(0, int((34 - y) * 1.8))
        image[y, start_x : min(start_x + 36, 52)] = 30
    roi = RectRegion(x=0, y=15, width=48, height=22)
    config = DirectionalContourConfig(
        analysis_roi=roi,
        direction_angle_deg=-18.0,
        threshold_mode="binary",
        foreground_polarity="dark_on_light",
        min_target_area_px=20,
    )

    result = detect_directional_contour(image, config)

    assert roi.x <= result.point_a.x < roi.x + roi.width
    assert roi.y <= result.point_a.y < roi.y + roi.height
    assert roi.x <= result.point_b.x < roi.x + roi.width
    assert roi.y <= result.point_b.y < roi.y + roi.height


def test_directional_contour_metric_reports_machine_readable_failure_reason() -> None:
    image = np.full((8, 12), 240, dtype=np.uint8)
    extractor = DirectionalContourMetricExtractor(
        DirectionalContourConfig(
            analysis_roi=RectRegion(x=20, y=20, width=4, height=4),
            direction_angle_deg=0.0,
            threshold_mode="binary",
        )
    )

    metric = extractor.extract(FramePacket(timestamp_ms=123, source="fixture", image=image))

    assert metric.metric_raw is None
    assert metric.quality == 0.0
    assert metric.meta["reason"] == "roi_outside_image"
    assert metric.meta["direction_angle_deg"] == 0.0


def test_directional_contour_metric_wraps_success_as_shape_metric() -> None:
    image = np.full((12, 20), 240, dtype=np.uint8)
    image[4:7, 3:12] = 30
    extractor = DirectionalContourMetricExtractor(
        DirectionalContourConfig(
            analysis_roi=RectRegion(x=0, y=0, width=20, height=12),
            direction_angle_deg=0.0,
            threshold_mode="binary",
            min_target_area_px=6,
        )
    )

    metric = extractor.extract(FramePacket(timestamp_ms=123, source="fixture", image=image))

    assert metric.metric_name == "directional_contour_span"
    assert metric.metric_raw == 8.0
    assert metric.point_a_px == (3, 5)
    assert metric.point_b_px == (11, 5)
    assert "source_point_a_px" not in metric.meta
    assert "source_point_b_px" not in metric.meta
    assert "axis_point_a_px" not in metric.meta
    assert "axis_point_b_px" not in metric.meta
    assert metric.meta["projection_point_mode"] == "max_chord"
    assert metric.meta["selection_mode"] == "directional_contour_max_chord"


def _paint_test_line(
    image: np.ndarray,
    start: tuple[int, int],
    end: tuple[int, int],
    *,
    width: int,
    value: int,
) -> None:
    x0, y0 = start
    x1, y1 = end
    steps = max(abs(x1 - x0), abs(y1 - y0), 1)
    radius = max(0, int(width) // 2)
    for index in range(steps + 1):
        ratio = index / steps
        x = int(round(x0 + (x1 - x0) * ratio))
        y = int(round(y0 + (y1 - y0) * ratio))
        image[
            max(0, y - radius) : min(image.shape[0], y + radius + 1),
            max(0, x - radius) : min(image.shape[1], x + radius + 1),
        ] = value


def _point_in_rotated_metric_box_with_tolerance(box: MetricBox, point: PixelPoint, epsilon: float = 2.0) -> bool:
    angle_rad = math.radians(float(box.angle_deg))
    cos_theta = math.cos(angle_rad)
    sin_theta = math.sin(angle_rad)
    translated_x = float(point.x) - float(box.center_x)
    translated_y = float(point.y) - float(box.center_y)
    local_x = translated_x * cos_theta + translated_y * sin_theta
    local_y = -translated_x * sin_theta + translated_y * cos_theta
    return abs(local_x) <= float(box.width) / 2.0 + epsilon and abs(local_y) <= float(box.height) / 2.0 + epsilon


def _point_local_coords(box: MetricBox, point: PixelPoint) -> tuple[float, float]:
    angle_rad = math.radians(float(box.angle_deg))
    cos_theta = math.cos(angle_rad)
    sin_theta = math.sin(angle_rad)
    translated_x = float(point.x) - float(box.center_x)
    translated_y = float(point.y) - float(box.center_y)
    local_x = translated_x * cos_theta + translated_y * sin_theta
    local_y = -translated_x * sin_theta + translated_y * cos_theta
    return local_x, local_y


def _paint_test_line_local(
    image: np.ndarray,
    box: MetricBox,
    start_local_x: float,
    end_local_x: float,
    *,
    local_y: float = 0.0,
    width: int,
    value: int,
) -> None:
    angle_rad = math.radians(float(box.angle_deg))
    cos_theta = math.cos(angle_rad)
    sin_theta = math.sin(angle_rad)
    steps = max(2, int(abs(float(end_local_x) - float(start_local_x)) * 2))
    radius = max(0, int(width) // 2)
    for index in range(steps + 1):
        ratio = index / steps
        local_x = float(start_local_x) + (float(end_local_x) - float(start_local_x)) * ratio
        x = int(round(float(box.center_x) + local_x * cos_theta - float(local_y) * sin_theta))
        y = int(round(float(box.center_y) + local_x * sin_theta + float(local_y) * cos_theta))
        image[
            max(0, y - radius) : min(image.shape[0], y + radius + 1),
            max(0, x - radius) : min(image.shape[1], x + radius + 1),
        ] = value
