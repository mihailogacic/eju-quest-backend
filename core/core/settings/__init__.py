import os

if os.getenv("PRODUCTION") == "True":
    from .production import *  # noqa
else:
    from .development import *  # noqa

