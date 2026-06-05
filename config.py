import os
import warnings
from pathlib import Path

# --- Security ---
SECRET_KEY: str = os.environ.get("SECRET_KEY", "change-me-in-production")
if SECRET_KEY == "change-me-in-production":
    warnings.warn("SECRET_KEY is using the default value. Set the SECRET_KEY environment variable in production!", RuntimeWarning)

ADMIN_USER: str = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS: str = os.environ.get("ADMIN_PASS", "123")
if ADMIN_USER == "admin" and ADMIN_PASS == "123":
    warnings.warn("ADMIN_USER/ADMIN_PASS are using default values. Set them via environment variables in production!", RuntimeWarning)

# --- Database ---
DATABASE_URL: str = os.environ.get(
    "CGCPT_DB_URL",
    "mysql+pymysql://root@127.0.0.1:3306/cgcpt?charset=utf8mb4",
)

# --- Server ---
HOST: str = os.environ.get("HOST", "0.0.0.0")
PORT: int = int(os.environ.get("PORT", "5000"))
DEBUG: bool = os.environ.get("DEBUG", "true").lower() in ("true", "1", "yes")

# --- CORS ---
CORS_ORIGINS: str = os.environ.get("CORS_ORIGINS", "")

# --- Logging ---
LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO").upper()

# --- Directories ---
_base_dir: Path = Path(__file__).resolve().parent
DATABASE_DIR: Path = Path(os.environ.get("DATABASE_DIR", str(_base_dir / "database")))
UPLOAD_DIR: Path = Path(os.environ.get("UPLOAD_DIR", str(_base_dir / "uploads")))
MODEL_DIR: Path = Path(os.environ.get("MODEL_DIR", str(_base_dir / "models")))
