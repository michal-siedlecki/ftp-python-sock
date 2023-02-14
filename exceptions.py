class FTPException(Exception):
    response = None, None


class WrongFilename(FTPException):
    "Raised when a wrong filename is delivered"
    response = 533, "Wrong Filename"
