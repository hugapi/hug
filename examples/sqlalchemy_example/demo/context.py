from sqlalchemy.engine import create_engine
from sqlalchemy.orm.scoping import scoped_session
from sqlalchemy.orm.session import sessionmaker, Session


engine = create_engine("sqlite:///:memory:")


session_factory = scoped_session(sessionmaker(bind=engine))


class SqlalchemyContext(object):

    def __init__(self):
        self._db = session_factory()

    @property
    def db(self) -> Session:
        return self._db
        # return self.session_factory()

    def cleanup(self, exception=None):
        if exception:
            self.db.rollback()
            return
        self.db.commit()
