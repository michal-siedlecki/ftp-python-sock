import ftplib


def test_connect(ftp_client):
    response = ftp_client.getwelcome()
    assert response == "220 Welcome! "

def test_user(ftp_client):
    ftp_client.login(user='test_user')
    response = ftp_client.lastresp
    assert response == "230"

def test_cwd(ftp_client, get_test_dirs):
    dirs = get_test_dirs
    ftp_client.cwd(dirs.get('nested'))
    response = ftp_client.lastresp
    assert response == "250"

def test_cwd_pwd(ftp_client, get_test_dirs):
    dirs = get_test_dirs
    nested = dirs.get('nested')
    ftp_client.cwd(nested)
    pwd = ftp_client.pwd()
    response = ftp_client.lastresp
    assert response == "257"
    assert pwd == f"/{nested}"

def test_cwd_cant_escape(ftp_client, escape_path):
    try:
        ftp_client.cwd(escape_path)
    except ftplib.error_perm:
        assert ftp_client.lastresp == "553"

def test_cdup_cant_escape(ftp_client):
    try:
        ftp_client.cwd('..')
    except ftplib.error_perm:
        assert ftp_client.lastresp == "553"


def test_list(ftp_client, files_dirs):
    ls = ftp_client.nlst()
    assert len(ls) == 2



