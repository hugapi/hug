import hug
import happy_birthday
from falcon import HTTP_400, HTTP_404, HTTP_200

def tests_happy_birthday():
    response = hug.test.get(happy_birthday, 'happy_birthday', {'name': 'Timothy', 'age': 25})
    assert response.status == HTTP_200
    assert response.data is not None
