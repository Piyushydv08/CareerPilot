import os
from typing import List, Union
from pydantic import AnyHttpUrl, BeforeValidator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Annotated

def parse_cors_origins(v: Union[str, List[str]]) -> List[str]:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",")]
    elif isinstance(v, (list, str)):
        return v
    raise ValueError(v)

class Settings(BaseSettings):
    PROJECT_NAME: str = "CareerPilot AI Telemetry API"
    API_V1_STR: str = "/api/v1"
    
    # MongoDB Atlas String Setup
    MONGODB_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "careerpilot"
    
    # CORS Origin Configurations (Safely maps http://localhost:3000 strings)
    CORS_ORIGINS: Annotated[
        List[str], BeforeValidator(parse_cors_origins)
    ] = ["http://localhost:3000"]
    
    # App port
    PORT: int = 8000
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
