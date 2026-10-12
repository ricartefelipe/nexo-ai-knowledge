"""Local interface over the existing HTTP API."""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response

from nexo_ai.interface.assets import InterfaceAsset, read_interface_file

router = APIRouter(include_in_schema=False)

_PAGE_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self'; "
        "img-src 'self'; "
        "connect-src 'self'; "
        "base-uri 'none'; "
        "form-action 'self'; "
        "frame-ancestors 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-cache",
}
_ASSET_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-cache",
}


@router.get("/")
def read_interface() -> Response:
    """Return the local page. The browser calls the API on the same origin."""

    return Response(
        content=read_interface_file("index.html"),
        media_type="text/html; charset=utf-8",
        headers=_PAGE_HEADERS,
    )


@router.get("/assets/{asset_name}")
def read_asset(asset_name: str) -> Response:
    """Return one packaged stylesheet or script."""

    try:
        asset = InterfaceAsset(asset_name)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="O recurso não foi encontrado.",
        ) from None
    return Response(
        content=read_interface_file(asset.value),
        media_type=asset.media_type,
        headers=_ASSET_HEADERS,
    )
