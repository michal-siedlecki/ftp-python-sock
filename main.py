from server_base import ServerThread
from server_ftp import AnonymusFtpServerThread

FTP_CONFIG = {"root_dir": "test_root"}


def run():
    ftp = ServerThread(
        host="127.0.0.1",
        port=8000,
        server_type=AnonymusFtpServerThread,
        server_config=FTP_CONFIG,
    )
    print(f"Server is listening on {ftp.host}:{ftp.port}")
    ftp.daemon = True
    ftp.start()
    input("Press enter to stop ...")
    ftp.stop()


if __name__ == "__main__":
    run()
