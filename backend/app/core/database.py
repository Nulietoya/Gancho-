"""
Configuração de acesso ao banco de dados (SQLAlchemy).

`Base` é a classe da qual todos os modelos (ETAPA 4) vão herdar.
`get_db` é a dependency usada pelas rotas para obter uma sessão por
requisição, sempre fechada ao final (mesmo em caso de erro).
"""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(settings.database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
