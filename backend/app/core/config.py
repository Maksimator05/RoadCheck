from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
    )

    DATABASE_URL: str = "postgresql://roadcheck:roadcheck@localhost:5432/roadcheck"
    SECRET_KEY: str = "change-me-in-production"
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    USE_MOCK_ML: bool = True
    ML_MODEL_PATH: str = "app/ml/weights/best.pt"
    ML_DEVICE: str = "cpu"
    ML_CONFIDENCE_THRESHOLD: float = 0.25
    ML_IOU_THRESHOLD: float = 0.45
    ML_LOAD_ON_STARTUP: bool = True


settings = Settings()
