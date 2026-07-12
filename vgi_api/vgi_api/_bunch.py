"""CHANGE(py3.14): minimal replacement for the abandoned `bunch` package.

`bunch` (last released 2011) no longer installs on Python >= 3.11: its
setup.py opens files with the Python-2 `'rU'` mode, which was removed from
the language. The code only ever used the `Bunch` class — a dict whose keys
are also readable/writable as attributes — so it is vendored here.
"""


class Bunch(dict):
    """A dict with attribute-style access: ``b.key`` == ``b["key"]``."""

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError:
            raise AttributeError(key)
