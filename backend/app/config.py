import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://tlac:tlac@db:5432/tlac")
SESSION_TTL_MINUTES = int(os.getenv("SESSION_TTL_MINUTES", "480"))
SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "tlac_session")
CSRF_HEADER_NAME = "X-CSRF-Token"
