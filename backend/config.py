from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List


class Settings(BaseSettings):
    DATABASE_URL: str
    TOKEN_TTL_HOURS: int = 24
    SECRET_KEY: str
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = ""
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    GITHUB_REDIRECT_URI: str = ""
    AUTH_APP_URL: str = "https://auth.mainpage.com"
    COOKIE_DOMAIN: str = ".mainpage.com"
    ENVIRONMENT: str = "production"
    # Accepts comma-separated string ("a,b,c") or JSON array ("[\"a\",\"b\"]")
    ALLOWED_ORIGINS: str = ""

    ADMIN_USERNAME: str = ""
    ADMIN_PASSWORD: str = ""
    USER1_USERNAME: str = ""
    USER1_PASSWORD: str = ""
    USER2_USERNAME: str = ""
    USER2_PASSWORD: str = ""

    @property
    def allowed_origins_list(self) -> List[str]:
        v = self.ALLOWED_ORIGINS.strip()
        if not v:
            return []
        if v.startswith("["):
            import json
            return json.loads(v)
        return [o.strip() for o in v.split(",") if o.strip()]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
