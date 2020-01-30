import functools
from PyQt5.QtCore import QSettings

TRACE_LOG_SETTING = "trace_log_setting"

def tracelog(func):
    """Print the function signature and return value"""

    @functools.wraps(func)
    def wrapper_debug(*args, **kwargs):
        if QSettings().value(TRACE_LOG_SETTING):
            args_repr = [repr(a) for a in args]  # 1
            kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]  # 2
            signature = ", ".join(args_repr + kwargs_repr)  # 3
            print(f"Calling {func.__name__}({signature})")
        value = func(*args, **kwargs)
        if QSettings().value(TRACE_LOG_SETTING):
            print(f"{func.__name__!r} returned {value!r}")  # 4
        return value

    return wrapper_debug

    # TODO Make trace output settable from UI flag
    # TODO Trace: Use from tracelog