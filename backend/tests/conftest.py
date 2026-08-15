import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base
from app import models
@pytest.fixture()
def db():
    engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool,future=True);Base.metadata.create_all(engine);Session=sessionmaker(bind=engine,autoflush=False,autocommit=False,future=True)
    with Session() as session:yield session
