"""HTTP API + the web page."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import notation, solver
from . import tables as T

STATIC = Path(__file__).parent / "static"


class SolveIn(BaseModel):
    size: Literal[2, 3]
    scramble: str = Field(max_length=2000)
    algorithm: str
    seconds: float = Field(default=10, gt=0, le=60)


def create_app() -> FastAPI:
    app = FastAPI(title="Cube solver", version="1.0")
    # Build/load lookup tables in the background so the page opens instantly
    threading.Thread(target=T.load, daemon=True).start()

    @app.get("/", include_in_schema=False)
    def page():
        return FileResponse(STATIC / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC), name="static")

    @app.get("/api/status")
    def status():
        return {"tables_ready": T.ready()}

    @app.get("/api/algorithms")
    def algorithms(size: int = Query(3, ge=2, le=3)):
        return solver.algorithms(size)

    @app.get("/api/scramble")
    def scramble(size: int = Query(3, ge=2, le=3), length: int = 20):
        return {"scramble": solver.scramble(size, max(1, min(length, 60)))}

    @app.get("/api/preview")
    def preview(size: int = Query(3, ge=2, le=3), scramble: str = ""):
        """Stickers of the scrambled cube, so the page can draw it before solving."""
        try:
            return {"state": solver.sticker_states(size, notation.parse(scramble), [])[0]}
        except ValueError as e:
            raise HTTPException(422, str(e)) from e

    @app.post("/api/solve")
    def solve(body: SolveIn):
        try:
            notation.parse(body.scramble)
            return solver.solve(body.size, body.scramble, body.algorithm, seconds=body.seconds)
        except ValueError as e:
            raise HTTPException(422, str(e)) from e

    return app


