from datetime import date
from pathlib import Path

from app.data_service import DashboardDataService

DATA = Path(__file__).resolve().parents[1] / "data" / "dataset.csv"
service = DashboardDataService(DATA)
FROM = TO = date(2025, 5, 27)


def test_purchase_filtering_and_overview():
    result = service.overview(FROM, TO)
    assert result["transactionCount"] == 24
    assert result["investorCount"] == 15
    assert result["mutualFundCount"] == 4
    assert result["totalInvestedAmount"] == 87822.65
    assert result["totalUnitsPurchased"] == 2428.25


def test_mutual_fund_summary():
    result = service.mutual_funds(FROM, TO, None, None, None, 1, 50, None, "desc")
    assert result["pagination"]["totalRecords"] == 4
    by_code = {r["fundCode"]: r for r in result["data"]}
    assert by_code["K46"]["totalInvestedAmount"] == 24420.79
    assert by_code["K46"]["totalUnitsPurchased"] == 661.8
    assert by_code["K46"]["averageNav"] == 36.9006


def test_pan_filter():
    result = service.investor_fund_summary(FROM, TO, "AAEPN3766A", 1, 50, None, "desc")
    assert result["pagination"]["totalRecords"] == 3
    assert sum(x["totalPurchaseAmount"] for x in result["data"]) == 16399.19
