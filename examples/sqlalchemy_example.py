import hug

from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative.api import declarative_base
from sqlalchemy.orm.session import Session
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker


engine = create_engine("sqlite:///:memory:")

session_factory = scoped_session(sessionmaker(bind=engine))


Base = declarative_base()


class TestModel(Base):
    __tablename__ = 'test_model'
    id = Column(Integer, primary_key=True)
    name = Column(String)


Base.metadata.create_all(bind=engine)


@hug.directive()
class Resource(object):

    def __init__(self, *args, **kwargs):
        self._db = session_factory()
        self.autocommit = True

    @property
    def db(self) -> Session:
        return self._db

    def cleanup(self, exception=None):
        if exception:
            self.db.rollback()
            return
        if self.autocommit:
            self.db.commit()


@hug.directive()
def return_session() -> Session:
    return session_factory()


@hug.get('/hello')
def make_simple_query(resource: Resource):
    for word in ["hello", "world", ":)"]:
        test_model = TestModel()
        test_model.name = word
        resource.db.add(test_model)
        resource.db.flush()
    return " ".join([obj.name for obj in resource.db.query(TestModel).all()])
