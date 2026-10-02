import os
from dotenv import load_dotenv

# Base project directory
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Load environment variables from .env file
load_dotenv(os.path.join(BASE_DIR, ".env"))


class Config:
    """Application configuration settings loaded from environment variables."""
    SECRET_KEY = os.getenv("SECRET_KEY", "scorevision-super-secret-key-32bytes-secure")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", os.getenv("SECRET_KEY", "scorevision-super-jwt-key-32bytes-secure"))
    DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")

    # Database configuration
    raw_db_url = os.getenv("DATABASE_URL", "sqlite:///database/scorevision.db")

    # If using relative SQLite path, resolve against project BASE_DIR to prevent location ambiguity
    if raw_db_url.startswith("sqlite:///") and not raw_db_url.startswith("sqlite:////"):
        relative_path = raw_db_url.replace("sqlite:///", "")
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, relative_path)}"
    else:
        SQLALCHEMY_DATABASE_URI = raw_db_url

    SQLALCHEMY_TRACK_MODIFICATIONS = False
