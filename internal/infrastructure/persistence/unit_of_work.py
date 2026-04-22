from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


def create_session_factory(database_url: str) -> sessionmaker:
    connect_args = (
        {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    )
    engine_kwargs = {}
    if database_url == "sqlite://":
        engine_kwargs["poolclass"] = StaticPool

    engine = create_engine(database_url, connect_args=connect_args, **engine_kwargs)
    return sessionmaker(bind=engine, expire_on_commit=False)
