import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "校园通知智能问答系统"
    SECRET_KEY: str = "campus-rag-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    DATABASE_URL: str = "sqlite:///./campus_rag.db"

    CHROMA_PERSIST_DIR: str = "./chroma_db"
    CHROMA_COLLECTION_NAME: str = "campus_notifications"

    UPLOAD_DIR: str = "./uploads"

    EMBEDDING_MODEL: str = "text-embedding-v4"
    EMBEDDING_API_KEY: str = os.getenv("EMBEDDING_API_KEY", "")
    EMBEDDING_BASE_URL: str = os.getenv("EMBEDDING_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    EMBEDDING_DIMENSION: int = 1024

    LLM_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    LLM_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    LLM_MODEL: str = "gpt-3.5-turbo"
    VISION_MODEL: str = "qwen-vl-max"

    RETRIEVAL_TOP_K: int = 5
    RETRIEVAL_MIN_SCORE: float = 0.5

    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
