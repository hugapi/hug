from sqlalchemy.sql.schema import Column
from sqlalchemy.sql.sqltypes import Integer, String

from demo.base import Base


class TestModel(Base):
    __tablename__ = "test_model"
    id = Column(Integer, primary_key=True)
    name = Column(String)


class TestUser(Base):
    __tablename__ = "test_user"
    id = Column(Integer, primary_key=True)
    username = Column(String)
    password = Column(
        String
    )  # do not store plain password in the database, hash it, see porridge for example
