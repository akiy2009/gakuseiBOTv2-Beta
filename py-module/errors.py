__all__ = ["HSSException", "HTTPException", "NotFound", "Forbidden", "BadRequest"]


def handle_http_error(status: int, reason: str):
    if status == 404:
        raise NotFound(reason)
    elif status == 403:
        raise Forbidden(reason)
    elif status == 401:
        raise MissingPermissions(reason)
    elif status == 400:
        raise BadRequest(reason)
    else:
        raise HTTPException("Unknown API Error has occurred: ", status, reason)


class HSSException(Exception):
    pass

class NotSupported(HSSException):
    pass

class HTTPException(HSSException):
    pass

class NotFound(HTTPException):
    pass

class Forbidden(HTTPException):
    pass

class BadRequest(HTTPException):
    pass

class MissingPermissions(HTTPException):
    pass