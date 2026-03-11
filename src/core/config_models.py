"""Configuration models for the frozen scaffold."""

from dataclasses import dataclass


@dataclass(slots=True)
class RecipeConfig:
    sample_id: str
    camera_backend: str = "mock_camera"
    temp_backend: str = "mock_temp"
    plc_backend: str = "mock_plc"


@dataclass(slots=True)
class AppConfig:
    recipe_path: str = "configs/recipe_example.yaml"
    dry_run: bool = True
