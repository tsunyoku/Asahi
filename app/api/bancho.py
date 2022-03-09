from fastapi.responses import HTMLResponse
from fastapi import APIRouter

router = APIRouter(tags=["osu! Bancho API"])


@router.get("/")
async def bancho_index() -> HTMLResponse:
    return HTMLResponse("asahi bancho w")
