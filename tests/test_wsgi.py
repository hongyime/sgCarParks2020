"""Exercise the production WSGI worker on Linux; loopback requests only."""

import os
import socket
import subprocess
import time
import unittest
from pathlib import Path
from urllib.request import urlopen


@unittest.skipIf(os.name == 'nt', 'Gunicorn runs on Unix; covered by Linux CI')
class WsgiTests(unittest.TestCase):
    def test_gunicorn_threaded_worker_serves_home_and_search(self):
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            port = probe.getsockname()[1]
        base = f'http://127.0.0.1:{port}/'
        process = subprocess.Popen(
            ['gunicorn', '--workers', '1', '--threads', '2', '--timeout', '30', '--bind', f'127.0.0.1:{port}', 'main:app'],
            cwd=Path(__file__).resolve().parents[1], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        try:
            deadline = time.monotonic() + 15
            while True:
                try:
                    with urlopen(base, timeout=1) as response:
                        self.assertEqual(response.status, 200)
                    break
                except OSError:
                    if process.poll() is not None or time.monotonic() > deadline:
                        self.fail('Gunicorn failed to serve the application')
                    time.sleep(.1)
            with urlopen(base + 'search?xcoords=28000&ycoords=38000', timeout=3) as response:
                self.assertEqual(response.status, 200)
                self.assertIn(b'NEAREST IN THE SAVED DATASET', response.read(100000))
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
