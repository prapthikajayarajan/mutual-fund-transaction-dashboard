from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .data_service import DashboardDataService

app = FastAPI(
    title="Mutual Fund Transaction Dashboard API",
    version="1.0.0",
    description="Dashboard APIs for purchase-side mutual fund transactions.",
)
service = DashboardDataService.from_environment()
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def validate_range(from_date: date, to_date: date) -> None:
    if from_date > to_date:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_DATE_RANGE", "message": "fromDate cannot be greater than toDate."},
        )


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/dashboard/metadata")
def metadata():
    return service.metadata()


@app.get("/api/v1/dashboard/overview")
def overview(
    fromDate: date = Query(...),
    toDate: date = Query(...),
):
    validate_range(fromDate, toDate)
    return service.overview(fromDate, toDate)


@app.get("/api/v1/dashboard/investor-fund-summary")
def investor_fund_summary(
    fromDate: date = Query(...),
    toDate: date = Query(...),
    pan: str | None = None,
    page: int = Query(1, ge=1),
    pageSize: int = Query(50, ge=1, le=500),
    sortBy: str | None = None,
    sortOrder: Literal["asc", "desc"] = "desc",
):
    validate_range(fromDate, toDate)
    return service.investor_fund_summary(fromDate, toDate, pan, page, pageSize, sortBy, sortOrder)


@app.get("/api/v1/dashboard/fund-investor-summary")
def fund_investor_summary(
    fromDate: date = Query(...),
    toDate: date = Query(...),
    amcCode: str | None = None,
    fundCode: str | None = None,
    pan: str | None = None,
    page: int = Query(1, ge=1),
    pageSize: int = Query(50, ge=1, le=500),
    sortBy: str | None = None,
    sortOrder: Literal["asc", "desc"] = "desc",
):
    validate_range(fromDate, toDate)
    return service.fund_investor_summary(
        fromDate, toDate, amcCode, fundCode, pan, page, pageSize, sortBy, sortOrder
    )


@app.get("/api/v1/dashboard/investors")
def investors(
    fromDate: date = Query(...),
    toDate: date = Query(...),
    search: str | None = None,
    page: int = Query(1, ge=1),
    pageSize: int = Query(50, ge=1, le=500),
    sortBy: str | None = None,
    sortOrder: Literal["asc", "desc"] = "desc",
):
    validate_range(fromDate, toDate)
    return service.investors(fromDate, toDate, search, page, pageSize, sortBy, sortOrder)


@app.get("/api/v1/dashboard/mutual-funds")
def mutual_funds(
    fromDate: date = Query(...),
    toDate: date = Query(...),
    amcCode: str | None = None,
    fundCode: str | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    pageSize: int = Query(50, ge=1, le=500),
    sortBy: str | None = None,
    sortOrder: Literal["asc", "desc"] = "desc",
):
    validate_range(fromDate, toDate)
    return service.mutual_funds(
        fromDate, toDate, amcCode, fundCode, search, page, pageSize, sortBy, sortOrder
    )
