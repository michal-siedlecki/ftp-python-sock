import os
import time
import socket
from pathlib import Path
from datetime import date
from server_base import ServerThread

ALLOWED_COMMANDS = ['ABOR', 'ACCT', 'ALLO', 'APPE', 'CWD', 'DELE', 'HELP', 'LIST', 'MODE', 'NLST', 'NOOP',
                    'PASS', 'PASV', 'PORT', 'QUIT', 'REIN', 'REST', 'RETR', 'RNFR', 'RNTO', 'SITE', 'STAT',
                    'STOR', 'STRU', 'TYPE', 'USER', 'CDUP', 'MKD', 'PWD', 'RMD', 'SMNT', 'STOU', 'SYST', 'FEAT']


class AnonymusFtpServerThread(ServerThread):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.root = os.path.abspath(kwargs.get('root_dir'))
        self.cwd = self.root
        self.pasv_mode = False
        self.type = "A"
        self.crlf = "\r\n"
        self.bcrlf = b"\r\n"

    def run(self):
        self._ftp_response(220, "Welcome!")
        while True:
            msg = self._recvuntil(self.bcrlf)
            cmd, arg = msg[:4].strip(), msg[4:].strip()

            now = time.strftime("%H:%M:%S")
            print(f"[{now}]\tcmd: \t<{cmd}> \targ: <{arg}>")
            if not cmd:
                break
            if cmd not in ALLOWED_COMMANDS:
                self._ftp_response(500, "Bad command or not implemented")
                continue
            try:
                method = getattr(self, cmd)
                status, message = method(arg)
                self._ftp_response(status, message)
            except Exception as e:
                print(f"Got exception {e}")
                self._ftp_response(500, "Bad command or not implemented")

    def _ftp_response(self, status, message):
        """
        Format FTP server response
        :param status:
        :param message:
        :return:
        """
        msg = f"{status} {message} {self.crlf}"
        self.sock.sendall(msg.encode())

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

    def _trim_anchor(self, path):
        anchor = Path(path).anchor
        return path.lstrip(anchor)

    def _is_name_valid(self, name):
        trimmed = self._trim_anchor(name)
        result = os.path.realpath(os.path.join(self.root, trimmed))
        common = os.path.commonpath([self.root, result])
        return self.root in common

    def _get_entry_info(self, entry):
        stats = entry.stat()
        type = "d" if entry.is_dir() else "-"
        base = "rwxrwxrwx"
        links = stats.st_nlink
        owner = "anonymus"
        group = "anonymus"
        size = stats.st_size
        modified_date = date.fromtimestamp(stats.st_mtime)
        date_format = "%b %d %H:%m"
        modified = modified_date.strftime(date_format)
        name = entry.name
        return f"{type}{base} {links} {owner} {group} {size} {modified}\t{name}"

    def _create_or_append(self, mode, filename):
        if not self._is_name_valid(filename):
            return False
        self._ftp_response(150, "Opening data connection")
        self._start_datasock()
        new_file = self._recvuntil(self.bcrlf, self.datasocket)
        if self.type == "I":
            new_file = new_file.encode()
        self.datasocket.close()
        path = os.path.join(self.cwd, filename)
        try:
            with open(path, mode) as f:
                f.write(new_file)
        except Exception as e:
            print(e)
            return False
        return True

    # FTP API Commands

    def ABOR(self, arg=None):
        """
        The ABOR command can be issued by the client to abort the previous FTP command.
        If the previous FTP command is still in progress or has already completed, the server will terminate its
        execution and close any associated data connection. This command does not cause the connection to close.
        :param arg:
        :return:
        """
        try:
            self.datasocket.close()
        except Exception as e:
            print(e)
        self._stop_datasock()
        return 226, "Closing data connection."

    def ACCT(self, arg=None):
        """
        The ACCT command is used to provide an account name to the server.
        The account is not necessarily related to the USER .
        A client may log in using their username and password, however, an account may be required for
        specific access to server resources.
        :param arg:
        :return:
        """
        return 401, "Unauthorized, you are not logged in"

    def RNFR(self, arg=None):
        """
        The RNFR command is issued when an FTP client wants to rename a file on the server.
        The client specifies the name of the file to be renamed along with the command.
        After issuing an RNFR command, an RNTO command must immediately follow.
        :param arg:
        :return:
        """
        if not self._is_name_valid(arg):
            return 553, f"File name not allowed"
        file_path = os.path.abspath(os.path.join(self.cwd, arg))
        if not Path(file_path).exists():
            return 553, f"File not exists {arg}"
        self.filename_cache = arg
        return 350, "File ready to rename"

    def RNTO(self, arg=None):
        """
        The RNTO command is used to specify the new name of a file specified in a preceding RNFR (Rename From) command.

        :param arg:
        :return:
        """
        if not self._is_name_valid(arg):
            return 553, f"File name not allowed"
        old_filename_path = os.path.abspath(os.path.join(self.cwd, self.filename_cache))
        new_filename_path = os.path.abspath(os.path.join(self.cwd, arg))
        try:
            os.rename(old_filename_path, new_filename_path)
        except Exception as e:
            print(e)
            return 553, f"Failed to rename {arg}"
        return 250, f"File renamed to {arg}"

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
            return 553, f"File name not allowed"
        file_path = os.path.abspath(os.path.join(self.cwd, arg))
        if not Path(file_path).exists():
            return 553, f"File not exists {arg}"
        self._ftp_response(150, "Sending file")
        self._start_datasock()
        with open(file_path, "r") as f:
            data = f.read()
        self.datasocket.send(f"{data}{self.crlf}".encode())
        self._stop_datasock()
        return 250, "OK."

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
        if arg == "F":
            return 200, "OK."
        return 500, "Bad command or not implemented"

    def DELE(self, arg=None):
        """
        Delete file
        :param arg:
        :return:
        """
        if not self._is_name_valid(arg):
            return 553, f"Wrong file name {arg}"

        if not Path(os.path.join(self.cwd, arg)).exists():
            return 553, f"File not exists {arg}"

        os.remove(os.path.join(self.cwd, arg))
        return 250, "Deleted"

    def NOOP(self, arg=None):
        """
        The NOOP command does not cause the server to perform any action
        beyond acknowledging the receipt of the command.
        :param arg:
        :return:
        """
        return 200, "OK."

    def TYPE(self, arg=None):
        """
        The TYPE command is issued to inform the server of the type of data that is being transferred by the client.
        Most modern Windows FTP clients deal only with type A (ASCII) and type I (image/binary).
        :param arg:
        :return:
        """
        if arg == "A":
            self.type = arg
            return 200, "OK."
        if arg == "I":
            self.type = arg
            return 200, "OK."
        return 500, "Bad command or not implemented"

    def PORT(self, arg=None):
        host_port = arg.split(",")
        self.data_addr = ".".join(host_port[:4])
        self.data_port = (int(host_port[4]) << 8) + int(host_port[5])
        return 200, "Get port."

    def SYST(self, arg=None):
        return 215, "UNIX Type: L8"

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
        if self.type == "A":
            mode = "w"
        else:
            mode = "wb"
        if self._create_or_append(mode=mode, filename=arg):
            return 226, "Closing data connection"
        return 501, "Failed to create file"

    def APPE(self, arg=None):
        """
        A client issue the APPE command after successfully establishing a data connection
        when it wishes to upload data to the server. The client provides the file name it wishes to use for the upload.
        If the file already exists on the server, the data is appended to the existing file.
        If the file does not exist, it is created.
        :param arg:
        :return:
        """
        if self._create_or_append(mode="a", filename=arg):
            return 226, "Closing data connection"
        return 501, "Failed to append file"

    def FEAT(self, arg=None):
        """
        The FEAT command provides FTP clients with a mechanism of quickly determining
        what extended features the FTP server supports. If this command is supported, the server
        will reply with a multi-line response where each line of the response contains an extended feature command
        supported by the server.
        :param arg:
        :return:
        """
        return 500, "No extended features."

    def USER(self, arg=None):
        return 230, "OK."

    def PASS(self, arg=None):
        return 230, "OK."

    def QUIT(self, arg=None):
        return 221, "Goodbye"

    def CDUP(self, arg=None):
        if self.cwd == self.root:
            return 553, "Can't leave root directory"
        self.cwd = os.path.abspath(os.path.join(self.cwd, ".."))
        return 230, "OK."

    def PWD(self, arg=None):
        cwd = os.path.relpath(self.cwd, self.root)
        return 257, f'"/{cwd}"'

    def MKD(self, arg=None):
        if not self._is_name_valid(arg):
            return 553, f"Wrong directory name {arg}"
        try:
            os.mkdir(os.path.join(self.cwd, arg))
        except FileExistsError:
            return 553, f"Directory exists {arg}"
        return 250, "Created"

    def RMD(self, arg=None):
        """
        This command causes the directory specified in the path name to be removed.
        If a relative path is provided, the server assumes the specified directory to be a subdirectory of the
        client's current working directory. To delete a file, the DELE command is used.
        :param arg:
        :return:
        """
        if not self._is_name_valid(arg):
            return 553, f"Wrong directory name {arg}"
        if not os.path.exists(os.path.join(self.cwd, arg)):
            return 553, f"Directory not exists {arg}"
        if len(os.listdir(os.path.join(self.cwd, arg))):
            return 553, f"Directory {arg} is not empty."
        try:
            os.rmdir(os.path.join(self.cwd, arg))
        except Exception:
            return 553, f"Failed to remove directory {arg}"

        return 250, "Removed"

    def CWD(self, arg=None):
        if not self._is_name_valid(arg):
            print('the path is not valid')
            return 553, f"Wrong path {arg}"
        arg_tr = self._trim_anchor(arg)
        location = Path.joinpath(Path(self.root), Path(arg_tr))
        if not location.exists():
            return 553, f"Directory {arg} not exists "
        self.cwd = location.absolute()
        return 250, "OK."

    def LIST(self, arg=None):
        self._ftp_response(150, "Directory listing")
        self._start_datasock()
        entries = Path(self.cwd)
        for entry in entries.iterdir():
            info = self._get_entry_info(entry)
            data = f"{info}"
            self.datasocket.send(f"{data}{self.crlf}".encode())
        self._stop_datasock()
        return 226, "Directory send OK."

    def NLST(self, arg=None):
        return self.LIST(arg)

    def PASV(self, arg=None):
        self.pasv_mode = True
        self.serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serversocket.bind((self.host, 0))
        self.serversocket.listen(1)
        self.data_addr, self.data_port = self.serversocket.getsockname()
        host_ip = self.data_addr.replace(".", ",")
        port = f"{self.data_port >> 8 & 0xFF},{self.data_port & 0xFF}"
        return 227, f"Entering Passive Mode ({host_ip},{port})"
