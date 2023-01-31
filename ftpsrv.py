"""
https://www.rfc-editor.org/rfc/rfc5797#section-2.4
(...)
2.4.  Base FTP Commands

   The following commands are part of the base FTP specification
   [RFC0959] and are listed in the registry with the immutable pseudo
   FEAT code "base".

Mandatory commands:

      ABOR, ACCT, ALLO, APPE*, CWD*, DELE*, HELP, LIST*, MODE*, NLST, NOOP*,
      PASS*, PASV*, PORT*, QUIT*, REIN, REST, RETR*, RNFR, RNTO, SITE, STAT,
      STOR*, STRU*, TYPE*, USER*

      Optional commands:

      CDUP, MKD, PWD, RMD, SMNT, STOU, SYST
"""

import os
import time
import socket
import threading
from pathlib import Path

# Config
HOST = '127.0.0.1'
ROOT_DIR = 'root_dir'
PORT = 8000
IS_ANON = True

# Const

CRLF = '\r\n'
B_CRLF = b'\r\n'

COMMANDS = ['ABOR', 'ACCT', 'ALLO', 'APPE', 'CWD', 'DELE', 'HELP', 'LIST', 'MODE', 'NLST', 'NOOP',
            'PASS', 'PASV', 'PORT', 'QUIT', 'REIN', 'REST', 'RETR', 'RNFR', 'RNTO', 'SITE', 'STAT',
            'STOR', 'STRU', 'TYPE', 'USER', 'CDUP', 'MKD', 'PWD', 'RMD', 'SMNT', 'STOU', 'SYST', 'FEAT']


class ServerThread(threading.Thread):
    def __init__(self, host, conn, addr, is_anon, root_dir):
        super().__init__()
        self.host = host
        self.conn = conn
        self.addr = addr
        self.root = os.path.abspath(root_dir)
        self.cwd = self.root
        self.is_anon = is_anon
        self.type = 'A'  # ASCII mode default
        # Passive mode fields
        self.pasv_mode = False
        self.serversocket = None
        # Active mode fields
        self.datasocket = None
        self.data_addr = None
        self.data_port = None

    def run(self):
        self._sendall(220, 'Welcome!')

        while True:
            cmd = self._recvuntil(self.conn, B_CRLF)
            cmd, arg = cmd[:4].strip(), cmd[4:].strip()

            now = time.strftime('%H:%M:%S')
            print(f'[{now}]\tcmd: \t<{cmd}> \targ: <{arg}>')

            if not cmd:
                break
            try:
                method = getattr(self, cmd)
                status, message = method(arg)
                self._sendall(status, message)
            except Exception as e:
                print(f'Got exception {e}')
                self._sendall(500, 'Bad command or not implemented')

    # Private methods

    def _sendall(self, status, data):
        msg = f'{status} {data} {CRLF}'
        self.conn.sendall(msg.encode())

    def _recvall(self, amount):
        data_raw = self.conn.recv(amount)
        return data_raw.decode()

    def _recvuntil(self, sock, end):
        out_b = b''
        out_b = sock.recv(1024)
        # while True:
        #     out_b += sock.recv(1)
        #     print(out_b)
        #     if end in out_b:
        #         break
        return out_b.decode()

    def _start_datasock(self):
        if self.pasv_mode:
            self.datasocket, _ = self.serversocket.accept()
        else:
            self.datasocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.datasocket.connect((self.data_addr, self.data_port))

    def _stop_datasock(self):
        self.datasocket.close()
        if self.pasv_mode:
            self.serversocket.close()

    def _is_name_valid(self, name):
        test_path = (Path(self.cwd) / name).resolve()
        if test_path.parent != Path(self.cwd).resolve():
            return False
        return True

    def _get_entry_info(self, entry):
        info = entry.stat()
        size = info.st_size
        modified = info.st_mtime
        return f'{size} {modified}'

    def _create_or_append(self, mode, filename):
        if not self._is_name_valid(filename):
            return 553, f'File name not allowed'
        self._sendall(150, 'Opening data connection')
        self._start_datasock()
        new_file = self._recvuntil(self.datasocket, B_CRLF)
        self.datasocket.close()
        path = os.path.join(self.cwd, filename)
        try:
            with open(path, mode) as f:
                f.write(new_file)
        except Exception:
            return False
        return True

    # FTP API Commands

    def RNFR(self, arg=None):
        """
        The RNFR command is issued when an FTP client wants to rename a file on the server.
        The client specifies the name of the file to be renamed along with the command.
        After issuing an RNFR command, an RNTO command must immediately follow.
        :param arg:
        :return:
        """
        if not self._is_name_valid(arg):
            return 553, f'File name not allowed'
        file_path = os.path.abspath(os.path.join(self.cwd, arg))
        if not Path(file_path).exists():
            return 553, f'File not exists {arg}'
        self.filename_cache = arg
        return 350, 'File ready to rename'
    def RNTO(self, arg=None):
        """
        The RNTO command is used to specify the new name of a file specified in a preceding RNFR (Rename From) command.

        :param arg:
        :return:
        """
        if not self._is_name_valid(arg):
            return 553, f'File name not allowed'
        old_filename_path = os.path.abspath(os.path.join(self.cwd, self.filename_cache))
        new_filename_path = os.path.abspath(os.path.join(self.cwd, arg))
        try:
            os.rename(old_filename_path, new_filename_path)
        except Exception as e:
            print(e)
            return 553, f'Failed to rename {arg}'
        return 250, f'File renamed to {arg}'

    def RETR(self, arg=None):
        """
        A client issues the RETR command after successfully establishing a data connection
        when it wishes to download a copy of a file on the server. The client provides the file name
        it wishes to download along with the RETR command. The server will send a copy of the file to the client.
        This command does not affect the contents of the server’s copy of the file.
        :param arg:
        :return:
        """
        if not self._is_name_valid(arg):
            return 553, f'File name not allowed'
        file_path = os.path.abspath(os.path.join(self.cwd, arg))
        if not Path(file_path).exists():
            return 553, f'File not exists {arg}'
        self._sendall(150, 'Sending file')
        self._start_datasock()
        with open(file_path, 'r') as f:
            data = f.read()
        self.datasocket.send(f'{data}\r\n'.encode())
        self._stop_datasock()
        return 250, 'OK.'

    def STRU(self, arg=None):
        """
        The STRU command is issued with a single Telnet character parameter that specifies a file structure
        for the server to use for file transfers.
        The following codes are assigned for structure:
        F - File (no record structure)
        R - Record structure (Not implemented)
        P - Page structure (Not implemented)
        :param arg:
        :return:
        """
        if arg == 'F':
            return 200, 'OK.'
        return 500, 'Bad command or not implemented'

    def DELE(self, arg=None):
        """
        Delete file
        :param arg:
        :return:
        """
        if not self._is_name_valid(arg):
            return 553, f'Wrong file name {arg}'

        if not Path(os.path.join(self.cwd, arg)).exists():
            return 553, f'File not exists {arg}'

        os.remove(os.path.join(self.cwd, arg))
        return 250, 'Deleted'

    def NOOP(self, arg=None):
        """
        The NOOP command does not cause the server to perform any action
        beyond acknowledging the receipt of the command.
        :param arg:
        :return:
        """
        return 200, 'OK.'

    def TYPE(self, arg=None):
        """
        The TYPE command is issued to inform the server of the type of data that is being transferred by the client.
        Most modern Windows FTP clients deal only with type A (ASCII) and type I (image/binary).
        :param arg:
        :return:
        """
        if arg == 'A':
            self.type = arg
            return 200, 'OK.'
        if arg == 'I':
            self.type = arg
            return 200, 'OK.'
        return 500, 'Bad command or not implemented'

    def PORT(self, arg=None):
        host_port = arg.split(',')
        self.data_addr = '.'.join(host_port[:4])
        self.data_port = (int(host_port[4]) << 8) + int(host_port[5])
        return 200, 'Get port.'

    def SYST(self, arg=None):
        return 215, 'UNIX Type: L8'

    def STOR(self, arg=None):
        """
        A client issues the STOR command after successfully establishing a data connection when it wishes to upload
        a copy of a local file to the server. The client provides the file name it wishes to use for the upload.
        If the file already exists on the server, it is replaced by the uploaded file.
        If the file does not exist, it is created.
        This command does not affect the contents of the client's local copy of the file.
        :param arg:
        :return:
        """
        if self.type == 'A':
            mode = 'w'
        else:
            mode = 'wb'
        if self._create_or_append(mode=mode, filename=arg):
            return 226, 'Closing data connection'
        return 501, 'Failed to create file'

    def APPE(self, arg=None):
        """
        A client issue the APPE command after successfully establishing a data connection
        when it wishes to upload data to the server. The client provides the file name it wishes to use for the upload.
        If the file already exists on the server, the data is appended to the existing file.
        If the file does not exist, it is created.
        :param arg:
        :return:
        """
        if self._create_or_append(mode='a', filename=arg):
            return 226, 'Closing data connection'
        return 501, 'Failed to append file'

    def FEAT(self, arg=None):
        """
        The FEAT command provides FTP clients with a mechanism of quickly determining
        what extended features the FTP server supports. If this command is supported, the server
        will reply with a multi-line response where each line of the response contains an extended feature command
        supported by the server.
        :param arg:
        :return:
        """
        return 500, 'No extended features.'

    def USER(self, arg=None):
        if self.is_anon:
            return 230, 'OK.'
        else:
            return 530, 'Incorrect'

    def PASS(self, arg=None):
        if self.is_anon:
            return 230, 'OK.'
        else:
            return 530, 'Incorrect'

    def QUIT(self, arg=None):
        return 221, 'Goodbye'

    def CDUP(self, arg=None):
        if self.cwd == self.root:
            return 230, 'OK.'
        self.cwd = os.path.abspath(os.path.join(self.cwd, '..'))
        return 230, 'OK.'

    def PWD(self, arg=None):
        cwd = os.path.relpath(self.cwd, self.root)
        return 257, f'"/{cwd}"'

    def MKD(self, arg=None):
        if not self._is_name_valid(arg):
            return 553, f'Wrong directory name {arg}'
        try:
            os.mkdir(os.path.join(self.cwd, arg))
        except FileExistsError:
            return 553, f'Directory exists {arg}'
        return 250, 'Created'

    def CWD(self, arg=None):
        if not self._is_name_valid(arg):
            return 553, f'Wrong path {arg}'
        cwd = os.path.abspath(os.path.join(self.cwd, arg))
        if not os.path.exists(cwd):
            return 553, f'Directory {arg} not exists '
        self.cwd = cwd
        return 250, 'OK.'

    def LIST(self, arg):
        self._sendall(150, 'Directory listing')
        self._start_datasock()
        entries = Path(self.cwd)
        for entry in entries.iterdir():
            is_dir = '-'
            if entry.is_dir():
                is_dir = 'd'
            info = self._get_entry_info(entry)
            data = f'{is_dir}\t{info}\t{entry.name}'
            self.datasocket.send(f'{data}\r\n'.encode())
        self._stop_datasock()
        return 226, 'Directory send OK.'

    def PASV(self, arg):
        self.pasv_mode = True
        self.serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serversocket.bind((self.host, 0))
        self.serversocket.listen(1)
        self.data_addr, self.data_port = self.serversocket.getsockname()
        host_ip = self.data_addr.replace('.', ',')
        port = f'{self.data_port >> 8 & 0xFF},{self.data_port & 0xFF}'
        return 227, f'Entering Passive Mode ({host_ip},{port})'


class Server(threading.Thread):
    def __init__(self, host, port, is_anon, root_dir):
        super().__init__()
        self.host = host
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((host, port))
        self.is_anon = is_anon
        self.root_dir = root_dir

    def run(self):
        self.sock.listen(3)
        while True:
            conn, addr = self.sock.accept()
            th = ServerThread(self.host, conn, addr, self.is_anon, self.root_dir)
            th.daemon = True
            th.start()

    def stop(self):
        self.sock.close()


if __name__ == '__main__':
    ftp = Server(HOST, PORT, IS_ANON, ROOT_DIR)
    print(f'Server is listening on {HOST}:{PORT}')
    ftp.daemon = True
    ftp.start()
    stop_server = input('Press enter to stop ...')
    ftp.stop()
