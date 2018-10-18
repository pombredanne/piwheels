#!/usr/bin/env python

# The piwheels project
#   Copyright (c) 2017 Ben Nuttall <https://github.com/bennuttall>
#   Copyright (c) 2017 Dave Jones <dave@waveform.org.uk>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the copyright holder nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.


import os
import socket
import importlib
from unittest import mock

import pytest

import piwheels.systemd


@pytest.fixture()
def mock_sock(request, tmpdir):
    save_addr = os.environ.get('NOTIFY_SOCKET')
    save_sock = piwheels.systemd._notify_socket
    addr = tmpdir.join('notify')
    os.environ['NOTIFY_SOCKET'] = str(addr)
    s = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM | socket.SOCK_CLOEXEC)
    s.bind(str(addr))
    yield s
    s.close()
    piwheels.systemd._notify_socket = save_sock
    if save_addr is None:
        os.environ.pop('NOTIFY_SOCKET', None)
    else:
        os.environ['NOTIFY_SOCKET'] = save_addr


def test_available_undefined():
    importlib.reload(piwheels.systemd)
    with pytest.raises(RuntimeError):
        piwheels.systemd.available()


def test_available_invalid():
    with mock.patch.dict('os.environ'):
        os.environ['NOTIFY_SOCKET'] = 'FOO'
        importlib.reload(piwheels.systemd)
        with pytest.raises(RuntimeError):
            piwheels.systemd.available()


def test_available_ioerror(tmpdir):
    with mock.patch.dict('os.environ'):
        os.environ['NOTIFY_SOCKET'] = str(tmpdir.join('FOO'))
        importlib.reload(piwheels.systemd)
        with pytest.raises(RuntimeError):
            piwheels.systemd.available()


def test_notify_not():
    importlib.reload(piwheels.systemd)
    piwheels.systemd.notify('foo')
    piwheels.systemd.notify(b'foo')


def test_available(mock_sock):
    importlib.reload(piwheels.systemd)
    piwheels.systemd.available()


def test_available(mock_sock):
    importlib.reload(piwheels.systemd)
    piwheels.systemd.notify('foo')
    assert mock_sock.recv(64) == b'foo'
    piwheels.systemd.notify(b'bar')
    assert mock_sock.recv(64) == b'bar'


def test_ready(mock_sock):
    importlib.reload(piwheels.systemd)
    piwheels.systemd.ready()
    assert mock_sock.recv(64) == b'READY=1'


def test_reloading(mock_sock):
    importlib.reload(piwheels.systemd)
    piwheels.systemd.reloading()
    assert mock_sock.recv(64) == b'RELOADING=1'


def test_stopping(mock_sock):
    importlib.reload(piwheels.systemd)
    piwheels.systemd.stopping()
    assert mock_sock.recv(64) == b'STOPPING=1'


def test_extend_timeout(mock_sock):
    importlib.reload(piwheels.systemd)
    piwheels.systemd.extend_timeout(5)
    assert mock_sock.recv(64) == b'EXTEND_TIMEOUT_USEC=5000000'


def test_watchdog_ping(mock_sock):
    importlib.reload(piwheels.systemd)
    piwheels.systemd.watchdog_ping()
    assert mock_sock.recv(64) == b'WATCHDOG=1'


def test_watchdog_reset(mock_sock):
    importlib.reload(piwheels.systemd)
    piwheels.systemd.watchdog_reset(3)
    assert mock_sock.recv(64) == b'WATCHDOG_USEC=3000000'


def test_watchdog_period():
    with mock.patch.dict('os.environ'):
        os.environ.pop('WATCHDOG_USEC', None)
        assert piwheels.systemd.watchdog_period() is None
        os.environ['WATCHDOG_USEC'] = '5000000'
        assert piwheels.systemd.watchdog_period() == 5
        os.environ['WATCHDOG_PID'] = '1'
        assert piwheels.systemd.watchdog_period() is None


def test_watchdog_clean():
    with mock.patch.dict('os.environ'):
        os.environ['WATCHDOG_USEC'] = '5000000'
        os.environ['WATCHDOG_PID'] = str(os.getpid())
        piwheels.systemd.watchdog_clean()
        assert 'WATCHDOG_USEC' not in os.environ
        assert 'WATCHDOG_PID' not in os.environ


def test_main_pid(mock_sock):
    importlib.reload(piwheels.systemd)
    piwheels.systemd.main_pid(10)
    assert mock_sock.recv(64) == b'MAINPID=10'
    piwheels.systemd.main_pid()
    assert mock_sock.recv(64) == ('MAINPID=%d' % os.getpid()).encode('ascii')
