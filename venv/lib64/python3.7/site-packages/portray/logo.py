from portray._version import __version__

ascii_art = rf"""
                      __
                     /\ \__
 _____     ___   _ __\ \ ,_\  _ __    __     __  __
/\ '__`\  / __`\/\`'__\ \ \/ /\`'__\/'__`\  /\ \/\ \
\ \ \L\ \/\ \L\ \ \ \/ \ \ \_\ \ \//\ \L\.\_\ \ \_\ \
 \ \ ,__/\ \____/\ \_\  \ \__\\ \_\\ \__/.\_\\/`____ \
  \ \ \/  \/___/  \/_/   \/__/ \/_/ \/__/\/_/ `/___/> \
   \ \_\                                         /\___/
    \/_/                                         \/__/
        Your Project with Great Documentation.

Version: {__version__}
Copyright Timothy Edmund Crosley 2019 MIT License
"""

__doc__ = f"""
```python
{ascii_art}
```
"""
