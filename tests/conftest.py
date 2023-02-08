import os
import pytest
from ftplib import FTP


test_dirs = {"root": "test_root", "nested": "dir1", "test_rm": "test_rm"}
test_files = {"root": "file1.txt", "nested": "file2.txt"}


if not os.path.exists(test_dirs.get("root")):
    os.mkdir(test_dirs.get("root"))
    os.mkdir(os.path.join(test_dirs.get("root"), test_dirs.get("nested")))
    os.mkdir(os.path.join(test_dirs.get("root"), test_dirs.get("test_rm")))
    with open(os.path.join(test_dirs.get("root"), test_files.get("root")), "w") as f:
        f.write("testing " * 10)
    with open(
        os.path.join(
            test_dirs.get("root"), test_dirs.get("nested"), test_files.get("nested")
        ),
        "w",
    ) as f:
        f.write("testing nested file " * 10)


@pytest.fixture()
def ftp_client():
    ftp = FTP()
    ftp.connect("127.0.0.1", 8000)
    ftp.login(user="test_user")
    with ftp as ftp:
        yield ftp


@pytest.fixture
def get_test_dirs():
    return test_dirs


@pytest.fixture
def escape_path():
    return "/../../../etc"


@pytest.fixture
def files():
    return test_files

@pytest.fixture
def dirs():
    return test_dirs
