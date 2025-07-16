import os
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # clés obligatoires, mappées explicitement aux variables d'env
    pinecone_api_key: str = Field(..., env="PINECONE_API_KEY")
    openai_api_key: str   = Field(..., env="OPENAI_API_KEY")

    # configuration Pinecone
    pinecone_env: str       = Field("eu-west-1-aws",   env="PINECONE_ENV")
    index_name: str         = Field("sample-index",    env="PINECONE_INDEX_NAME")

    # hyper‑paramètres RAG
    top_k: int             = Field(4,               env="TOP_K")
    score_threshold: float = Field(0.15,            env="SCORE_THRESHOLD")

    # Configuration Email (optionnelle)
    email_expediteur: str       = Field("",               env="EMAIL_EXPEDITEUR")
    email_mot_de_passe: str     = Field("",               env="EMAIL_MOT_DE_PASSE") 
    email_commercial: str       = Field("",               env="EMAIL_COMMERCIAL")
    nom_commercial: str         = Field("Commercial",     env="NOM_COMMERCIAL")
    nom_entreprise: str         = Field("Butterfly Packaging", env="NOM_ENTREPRISE")
    smtp_server: str            = Field("smtp.gmail.com", env="SMTP_SERVER")
    smtp_port: int              = Field(587,              env="SMTP_PORT")
    email_actif: bool           = Field(False,            env="EMAIL_ACTIF")

    # charge le .env et ignore toute variable supplémentaire
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

settings = Settings()