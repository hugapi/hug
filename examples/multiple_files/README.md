# Splitting the API into multiple files

Example of an API defined in multiple Python modules and combined together
using the `extend_api()` helper.

Run with `hug -f api.py`. There are three API endpoints:
- `http://localhost:8000/` – `say_hi()` from `api.py`
- `http://localhost:8000/part1` – `part1()` from `part_1.py`
- `http://localhost:8000/part2` – `part2()` from `part_2.py`
