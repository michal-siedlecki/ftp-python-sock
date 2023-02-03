from server import ServerThread
from ftp_server import FTPServerThread

FTP_CONFIG = {
    'root_dir': 'root_dir',
    'is_anon': True,
    'owner': 'admin'
    }

if __name__ == '__main__':
    ftp = ServerThread(host='127.0.0.1', port=8000, server_type=FTPServerThread, server_config=FTP_CONFIG)
    print(f'Server is listening on {ftp.host}:{ftp.port}')
    ftp.daemon = True
    ftp.start()
    stop_server = input('Press enter to stop ...')
    ftp.stop()
