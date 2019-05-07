import hug

from demo.context import SqlalchemyContext
from demo.models import TestUser


@hug.authentication.basic
def basic_authentication(username, password, context: SqlalchemyContext):
    return context.db.query(
        context.db.query(TestUser)
        .filter(TestUser.username == username, TestUser.password == password)
        .exists()
    ).scalar()
