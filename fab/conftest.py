import os
import sys

_status = 0


def pytest_sessionfinish(session, exitstatus):
    global _status
    _status = int(exitstatus)


def pytest_unconfigure(config):
    # secsgem 0.3.0 can leave non-daemon socket threads that block interpreter exit after the summary is printed
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(_status)
