from pdocs._version import __version__

ascii_art = rf"""

                      88
                      88
                      88
8b,dPPYba,    ,adPPYb,88   ,adPPYba,    ,adPPYba,  ,adPPYba,
88P'    "8a  a8"    `Y88  a8"     "8a  a8"     ""  I8[    ""
88       d8  8b       88  8b       d8  8b           `"Y8ba,
88b,   ,a8"  "8a,   ,d88  "8a,   ,a8"  "8a,   ,aa  aa    ]8I
88`YbbdP"'    `"8bbdP"Y8   `"YbbdP"'    `"Ybbd8"'  `"YbbdP"'
88
88        - Documentation Powered by Your Python Code -

Version: {__version__}
Copyright Timothy Edmund Crosley 2019 MIT License
"""

__doc__ = f"""
```python
{ascii_art}
```
"""
