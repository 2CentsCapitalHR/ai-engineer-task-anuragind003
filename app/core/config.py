from __future__ import annotations

import os
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    google_api_key: str | None = Field(default=None, alias="GOOGLE_API_KEY")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    ollama_host: str | None = Field(default=None, alias="OLLAMA_HOST")
    llm_provider: str = Field(default=os.getenv("LLM_PROVIDER", "gemini"), alias="LLM_PROVIDER")
    llm_model: str = Field(default=os.getenv("LLM_MODEL", "gemini-2.0-flash"), alias="LLM_MODEL")
    embedding_model: str = Field(
        default=os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
        alias="EMBEDDING_MODEL",
    )

    faiss_index_dir: str = Field(default="data/faiss_index", alias="FAISS_INDEX_DIR")
    references_dir: str = Field(default="references", alias="REFERENCES_DIR")
    upload_dir: str = Field(default="data/uploads", alias="UPLOAD_DIR")
    output_dir: str = Field(default="data/outputs", alias="OUTPUT_DIR")

    max_chunk_tokens: int = Field(default=400, alias="MAX_CHUNK_TOKENS")
    chunk_overlap: int = Field(default=80, alias="CHUNK_OVERLAP")

    class Config:
        env_file = ".env"
        case_sensitive = False
        populate_by_name = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[arg-type]
