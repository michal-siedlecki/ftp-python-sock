"""
https://www.rfc-editor.org/rfc/rfc5797#section-2.4
(...)
2.4.  Base FTP Commands

   The following commands are part of the base FTP specification
   [RFC0959] and are listed in the registry with the immutable pseudo
   FEAT code "base".

Mandatory commands:

      ABOR, ACCT, ALLO, APPE, CWD, DELE, HELP, LIST, MODE, NLST, NOOP,
      PASS, PASV, PORT, QUIT, REIN, REST, RETR, RNFR, RNTO, SITE, STAT,
      STOR, STRU, TYPE, USER

      Optional commands:

      CDUP, MKD, PWD, RMD, SMNT, STOU, SYST
"""

import os
import socket
import threading
from pathlib import Path
import time

HOST = '127.0.0.1'
PORT = 8000
ROOT_DIR = 'root_dir'
ROOT_PATH = os.path.join('.', ROOT_DIR)
ANON = True

def get_os_path_separators():
    seps = []
    for sep in os.path.sep, os.path.altsep:
        if sep:
            seps.append(sep)
    return seps


class ServerThread(threading.Thread):
    def __init__(self, conn, addr):
        super().__init__()
        self.conn = conn
        self.addr = addr
        self.rootdir = ROOT_PATH
        self.cwd = self.rootdir
        self.anon = ANON
        self.datasocket = None
        self.data_addr = None
        self.data_port = None

    def run(self):
        self._sendall(220, 'Welcome!')

        while True:
            cmd = self._recvall(256)

            if not cmd:
                break
            cmd, arg = cmd[:4].strip(), cmd[4:].strip()

            now = time.strftime('%d-%m-%Y %H:%M:%S')
            print(f'[{now}]\tcmd: <{cmd}> arg: <{arg}> \t{len(cmd)}')

            try:
                method = getattr(self, cmd)
                s, m = method(arg)
                self._sendall(s,m)
            except Exception as e:
                print(f'Got exception {e}')
                self._sendall(500, 'Bad command or not implemented')

    def _sendall(self, status, data):

        print(f'cwd real: {self.cwd}')

        msg = f'{status} {data} \r\n'
        self.conn.sendall(msg.encode())

    def _recvall(self, amount):
        data_raw = self.conn.recv(amount)
        return data_raw.decode()

    def _is_name_valid(self, name):
        test_path = (Path(self.cwd) / name).resolve()
        if test_path.parent != Path(self.cwd).resolve():
            return False
        return True

    def PORT(self, cmd):
        host_port = cmd.split(',')
        self.data_addr = '.'.join(host_port[:4])
        self.data_port = (int(host_port[4]) << 8) + int(host_port[5])
        return 200, 'Get port.'

    def SYST(self, arg=None):
        return 215, 'UNIX Type: L8'

    def FEAT(self, arg=None):
        return 211, 'No features.'

    def USER(self, arg=None):
        if self.anon:
            return 230, 'OK.'
        else:
            return 530, 'Incorrect'

    def PASS(self, arg=None):
        if self.anon:
            return 230, 'OK.'
        else:
            return 530, 'Incorrect'

    def QUIT(self, arg=None):
        return 221, 'Goodbye'

    def CDUP(self, arg=None):
        if self.cwd == self.rootdir:
            return 230, 'OK.'
        self.cwd = os.path.abspath(os.path.join(self.cwd, '..'))
        return 230, 'OK.'

    def PWD(self, arg=None):
        cwd = os.path.relpath(self.cwd, self.rootdir)
        return 257, f'"{cwd}"'

    def MKD(self, arg):
        if not self._is_name_valid(arg):
            return 553, f'Wrong directory name {arg}'
        try:
            os.mkdir(os.path.join(self.cwd, arg))
        except FileExistsError:
            return 553, f'Directory exists {arg}'
        return 250, 'Created'

    def CWD(self, arg):
        if not self._is_name_valid(arg):
            return 553, f'Wrong path {arg}'
        cwd = os.path.abspath(os.path.join(self.cwd, arg))
        if not os.path.exists(cwd):
            return 553, f'Directory {arg} not exists '
        self.cwd = cwd
        return 250, 'OK.'

    def _start_datasock(self):
        self.datasock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.datasock.connect((self.data_addr, self.data_port))

    def _stop_datasock(self):
        self.datasock.close()

    def LIST(self, cmd):
        self._sendall(150, 'Directory listing')
        self._start_datasock()
        for t in os.listdir(self.cwd):
            print(t)
            k = os.path.join(self.cwd, t)
            self.datasock.send(f'{k}\r\n'.encode())
        self._stop_datasock()
        self._sendall(226, 'Directory send OK.')


class Server():
    def __init__(self, host, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((host, port))

    def run(self):
        self.sock.listen(3)
        while True:
            conn, addr = self.sock.accept()
            th = ServerThread(conn, addr)
            th.daemon = True
            th.start()

    def stop(self):
        self.sock.close()


if __name__ == '__main__':
    ftp = Server(HOST, PORT)
    print(f'Server is listening on {HOST}:{PORT} ...')
    ftp.daemon = True
    ftp.run()
    ftp.stop()

