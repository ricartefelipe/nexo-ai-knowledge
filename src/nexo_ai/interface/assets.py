"""Packaged page, stylesheet, and script."""

from enum import StrEnum
from importlib.resources import files

_PACKAGE = "nexo_ai.interface"


class InterfaceAsset(StrEnum):
    """Files the browser may request under `/assets`."""

    STYLESHEET = "app.css"
    SCRIPT = "app.js"

    @property
    def media_type(self) -> str:
        if self is InterfaceAsset.STYLESHEET:
            return "text/css; charset=utf-8"
        return "text/javascript; charset=utf-8"


_ALLOWED_FILES = frozenset({"index.html", *(asset.value for asset in InterfaceAsset)})


def read_interface_file(name: str) -> bytes:
    """Return one packaged interface file. Unknown names are refused."""

    if name not in _ALLOWED_FILES:
        raise FileNotFoundError(name)
    resource = files(_PACKAGE).joinpath("assets", name)
    if not resource.is_file():
        raise FileNotFoundError(name)
    return resource.read_bytes()
