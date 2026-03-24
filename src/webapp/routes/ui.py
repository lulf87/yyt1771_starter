"""Minimal HTML shell routes for the web application."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.storage.sqlite_repo import SqliteSessionRepo
from src.webapp.deps import get_session_repo

router = APIRouter(tags=["ui"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))
static_dir = Path(__file__).resolve().parents[1] / "static"


def _asset_version() -> str:
    css_mtime = (static_dir / "app.css").stat().st_mtime_ns
    js_mtime = (static_dir / "app.js").stat().st_mtime_ns
    return str(max(int(css_mtime), int(js_mtime)))


@router.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "app_title": "YYT1771 Web Console",
            "asset_version": _asset_version(),
        },
    )


@router.get("/workspace/{session_id}", response_class=HTMLResponse)
def workspace(
    request: Request,
    session_id: str,
    repo: SqliteSessionRepo = Depends(get_session_repo),
) -> HTMLResponse:
    summary = repo.get_summary(session_id)
    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        )

    return templates.TemplateResponse(
        request=request,
        name="workspace.html",
        context={
            "app_title": "YYT1771 Workspace",
            "asset_version": _asset_version(),
            "session_id": session_id,
            "summary": summary,
            "steps": ["准备", "采集", "处理", "计算", "调整", "存储"],
        },
    )
