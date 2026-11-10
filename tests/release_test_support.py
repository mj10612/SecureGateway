"""Bounded loopback port-readiness checks for isolated daemon tests."""
import errno
import os
import socket
import time


def wait_for_bindable_port(port, timeout=10):
    """Wait until a new server can bind the same loopback port."""
    deadline = time.monotonic() + timeout
    while True:
        with socket.socket() as probe:
            # Match HTTPServer's POSIX bind behavior without Windows' less
            # exclusive SO_REUSEADDR semantics.
            if os.name != 'nt':
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind(('127.0.0.1', port))
                return
            except OSError as exc:
                if exc.errno != errno.EADDRINUSE:
                    raise OSError('Loopback bind check failed') from None
        if time.monotonic() >= deadline:
            raise TimeoutError('Loopback port did not become bindable')
        time.sleep(.05)


def startup_failure_category(content):
    """Classify startup errors without exposing captured diagnostic content."""
    captured = content.lower()
    if b'address already in use' in captured:
        return 'address_in_use'
    if b'permission denied' in captured:
        return 'permission_denied'
    if b'modulenotfounderror' in captured or b'importerror' in captured:
        return 'import_failure'
    return 'other_or_unavailable'
