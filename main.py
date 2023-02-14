from server_base import ServerThread
from server_ftp import AnonymusFtpServerThread

BASE_CONFIG = {
    "host": "127.0.0.1",
    "port": 8001,
    "server_type": AnonymusFtpServerThread,
}

FTP_CONFIG = {"root_dir": "test_root"}


def run():
    ftp = ServerThread(
        host=BASE_CONFIG.get("host"),
        port=BASE_CONFIG.get("port"),
        server_type=BASE_CONFIG.get("server_type"),
        server_config=FTP_CONFIG,
    )
    print(f"Server is listening on {ftp.host}:{ftp.port}")
    ftp.daemon = True
    ftp.start()
    input("Press enter to stop ...")
    ftp.stop()


if __name__ == "__main__":
    run()
