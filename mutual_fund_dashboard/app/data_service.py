from __future__ import annotations

import math
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

PURCHASE_TYPES = {"Switch In", "Additional Purchase Systematic"}
REQUIRED_COLUMNS = {
    "PAN",
    "INV_NAME",
    "AMC_CODE",
    "PRODCODE",
    "SCHEME",
    "TRADDATE",
    "PURPRICE",
    "UNITS",
    "AMOUNT",
    "TRXNSTAT",
    "TRXN_TYPE_FLAG",
}


def _clean_text(value: Any) -> Any:
    if pd.isna(value):
        return value
    text = str(value).strip()
    # Some source exports wrap both headers and values in literal single/double quotes.
    for _ in range(2):
        if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
            text = text[1:-1].strip()
    return text.strip("'\"").strip()


def _json_number(value: Any, digits: int = 2) -> float:
    if value is None or pd.isna(value) or not math.isfinite(float(value)):
        return 0.0
    return round(float(value), digits)


def _paginate(records: list[dict[str, Any]], page: int, page_size: int) -> tuple[list[dict[str, Any]], dict[str, int]]:
    total_records = len(records)
    total_pages = max(1, math.ceil(total_records / page_size)) if total_records else 0
    start = (page - 1) * page_size
    end = start + page_size
    return records[start:end], {
        "page": page,
        "pageSize": page_size,
        "totalRecords": total_records,
        "totalPages": total_pages,
    }


def _sort_frame(df: pd.DataFrame, sort_by: str | None, sort_order: str, allowed: dict[str, str], default: str) -> pd.DataFrame:
    key = allowed.get(sort_by or "", allowed[default])
    ascending = sort_order.lower() == "asc"
    return df.sort_values(key, ascending=ascending, kind="stable")


@dataclass
class DashboardDataService:
    csv_path: Path

    @classmethod
    def from_environment(cls) -> "DashboardDataService":
        default = Path(__file__).resolve().parents[1] / "data" / "dataset.csv"
        return cls(Path(os.getenv("DATASET_PATH", str(default))))

    def __post_init__(self) -> None:
        self.reload()

    def reload(self) -> None:
        if not self.csv_path.exists():
            raise FileNotFoundError(f"Dataset not found: {self.csv_path}")

        df = pd.read_csv(self.csv_path)
        df.columns = [_clean_text(c) for c in df.columns]
        missing = REQUIRED_COLUMNS - set(df.columns)
        if missing:
            raise ValueError(f"Dataset is missing required columns: {', '.join(sorted(missing))}")

        for col in df.select_dtypes(include="object").columns:
            df[col] = df[col].map(_clean_text)

        for col in ["PURPRICE", "UNITS", "AMOUNT"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df["TRADDATE"] = pd.to_datetime(df["TRADDATE"], errors="coerce")
        df = df[df["TRADDATE"].notna()].copy()
        df["TRADE_DATE"] = df["TRADDATE"].dt.date

        self.raw_df = df
        self.purchase_df = df[
            (df["TRXNSTAT"].str.upper() == "Y")
            & (df["TRXN_TYPE_FLAG"].isin(PURCHASE_TYPES))
        ].copy()

    @property
    def min_date(self) -> date:
        return self.raw_df["TRADE_DATE"].min()

    @property
    def max_date(self) -> date:
        return self.raw_df["TRADE_DATE"].max()

    def _filtered(self, from_date: date, to_date: date) -> pd.DataFrame:
        return self.purchase_df[
            (self.purchase_df["TRADE_DATE"] >= from_date)
            & (self.purchase_df["TRADE_DATE"] <= to_date)
        ].copy()

    def metadata(self) -> dict[str, Any]:
        investors = (
            self.purchase_df[["PAN", "INV_NAME"]]
            .drop_duplicates()
            .sort_values(["INV_NAME", "PAN"])
            .rename(columns={"PAN": "pan", "INV_NAME": "investorName"})
            .to_dict("records")
        )
        funds = (
            self.purchase_df[["AMC_CODE", "PRODCODE", "SCHEME"]]
            .drop_duplicates()
            .sort_values(["SCHEME", "AMC_CODE", "PRODCODE"])
            .rename(columns={"AMC_CODE": "amcCode", "PRODCODE": "fundCode", "SCHEME": "fundName"})
            .to_dict("records")
        )
        return {
            "minDate": self.min_date.isoformat(),
            "maxDate": self.max_date.isoformat(),
            "purchaseTypes": sorted(PURCHASE_TYPES),
            "investors": investors,
            "funds": funds,
        }

    def overview(self, from_date: date, to_date: date) -> dict[str, Any]:
        df = self._filtered(from_date, to_date)
        return {
            "fromDate": from_date.isoformat(),
            "toDate": to_date.isoformat(),
            "currency": "INR",
            "totalInvestedAmount": _json_number(df["AMOUNT"].sum()),
            "totalUnitsPurchased": _json_number(df["UNITS"].sum()),
            "investorCount": int(df["PAN"].nunique()),
            "mutualFundCount": int(df[["AMC_CODE", "PRODCODE"]].drop_duplicates().shape[0]),
            "transactionCount": int(len(df)),
        }

    def investor_fund_summary(
        self,
        from_date: date,
        to_date: date,
        pan: str | None,
        page: int,
        page_size: int,
        sort_by: str | None,
        sort_order: str,
    ) -> dict[str, Any]:
        df = self._filtered(from_date, to_date)
        if pan:
            df = df[df["PAN"].str.upper() == pan.strip().upper()]

        grouped = (
            df.groupby(["PAN", "INV_NAME", "AMC_CODE", "PRODCODE", "SCHEME"], dropna=False)
            .agg(
                totalPurchaseAmount=("AMOUNT", "sum"),
                totalUnitsPurchased=("UNITS", "sum"),
                transactionCount=("PRODCODE", "size"),
            )
            .reset_index()
        )
        grouped = _sort_frame(
            grouped,
            sort_by,
            sort_order,
            {
                "pan": "PAN",
                "investorName": "INV_NAME",
                "fundName": "SCHEME",
                "totalPurchaseAmount": "totalPurchaseAmount",
                "totalUnitsPurchased": "totalUnitsPurchased",
                "transactionCount": "transactionCount",
            },
            "totalPurchaseAmount",
        )

        records: list[dict[str, Any]] = []
        for row in grouped.to_dict("records"):
            records.append(
                {
                    "pan": row["PAN"],
                    "investorName": row["INV_NAME"],
                    "amcCode": row["AMC_CODE"],
                    "fundCode": row["PRODCODE"],
                    "fundName": row["SCHEME"],
                    "totalPurchaseAmount": _json_number(row["totalPurchaseAmount"]),
                    "totalUnitsPurchased": _json_number(row["totalUnitsPurchased"]),
                    "transactionCount": int(row["transactionCount"]),
                }
            )
        data, pagination = _paginate(records, page, page_size)
        return {
            "fromDate": from_date.isoformat(),
            "toDate": to_date.isoformat(),
            "currency": "INR",
            "data": data,
            "pagination": pagination,
        }

    def fund_investor_summary(
        self,
        from_date: date,
        to_date: date,
        amc_code: str | None,
        fund_code: str | None,
        pan: str | None,
        page: int,
        page_size: int,
        sort_by: str | None,
        sort_order: str,
    ) -> dict[str, Any]:
        df = self._filtered(from_date, to_date)
        if amc_code:
            df = df[df["AMC_CODE"].str.upper() == amc_code.strip().upper()]
        if fund_code:
            df = df[df["PRODCODE"].str.upper() == fund_code.strip().upper()]
        if pan:
            df = df[df["PAN"].str.upper() == pan.strip().upper()]

        grouped = (
            df.groupby(["AMC_CODE", "PRODCODE", "SCHEME", "PAN", "INV_NAME"], dropna=False)
            .agg(
                totalPurchaseAmount=("AMOUNT", "sum"),
                totalUnitsPurchased=("UNITS", "sum"),
                transactionCount=("PRODCODE", "size"),
            )
            .reset_index()
        )
        grouped = _sort_frame(
            grouped,
            sort_by,
            sort_order,
            {
                "fundName": "SCHEME",
                "investorName": "INV_NAME",
                "pan": "PAN",
                "totalPurchaseAmount": "totalPurchaseAmount",
                "totalUnitsPurchased": "totalUnitsPurchased",
                "transactionCount": "transactionCount",
            },
            "totalPurchaseAmount",
        )

        records: list[dict[str, Any]] = []
        for row in grouped.to_dict("records"):
            records.append(
                {
                    "fund": {
                        "amcCode": row["AMC_CODE"],
                        "fundCode": row["PRODCODE"],
                        "fundName": row["SCHEME"],
                    },
                    "investor": {"pan": row["PAN"], "name": row["INV_NAME"]},
                    "totalPurchaseAmount": _json_number(row["totalPurchaseAmount"]),
                    "totalUnitsPurchased": _json_number(row["totalUnitsPurchased"]),
                    "transactionCount": int(row["transactionCount"]),
                }
            )
        data, pagination = _paginate(records, page, page_size)
        return {
            "fromDate": from_date.isoformat(),
            "toDate": to_date.isoformat(),
            "currency": "INR",
            "data": data,
            "pagination": pagination,
        }

    def investors(
        self,
        from_date: date,
        to_date: date,
        search: str | None,
        page: int,
        page_size: int,
        sort_by: str | None,
        sort_order: str,
    ) -> dict[str, Any]:
        df = self._filtered(from_date, to_date)
        if search:
            q = search.strip().lower()
            df = df[
                df["PAN"].str.lower().str.contains(q, na=False, regex=False)
                | df["INV_NAME"].str.lower().str.contains(q, na=False, regex=False)
            ]

        grouped = (
            df.groupby(["PAN", "INV_NAME"], dropna=False)
            .agg(
                totalInvestedAmount=("AMOUNT", "sum"),
                totalUnitsPurchased=("UNITS", "sum"),
                transactionCount=("PRODCODE", "size"),
            )
            .reset_index()
        )
        if not df.empty:
            fund_counts = (
                df[["PAN", "INV_NAME", "AMC_CODE", "PRODCODE"]]
                .drop_duplicates()
                .groupby(["PAN", "INV_NAME"])
                .size()
                .rename("mutualFundCount")
                .reset_index()
            )
            grouped = grouped.merge(fund_counts, on=["PAN", "INV_NAME"], how="left")
        else:
            grouped["mutualFundCount"] = pd.Series(dtype="int64")

        grouped = _sort_frame(
            grouped,
            sort_by,
            sort_order,
            {
                "pan": "PAN",
                "investorName": "INV_NAME",
                "totalInvestedAmount": "totalInvestedAmount",
                "totalUnitsPurchased": "totalUnitsPurchased",
                "mutualFundCount": "mutualFundCount",
                "transactionCount": "transactionCount",
            },
            "totalInvestedAmount",
        )

        records: list[dict[str, Any]] = []
        for row in grouped.to_dict("records"):
            records.append(
                {
                    "pan": row["PAN"],
                    "investorName": row["INV_NAME"],
                    "totalInvestedAmount": _json_number(row["totalInvestedAmount"]),
                    "totalUnitsPurchased": _json_number(row["totalUnitsPurchased"]),
                    "mutualFundCount": int(row.get("mutualFundCount", 0)),
                    "transactionCount": int(row["transactionCount"]),
                }
            )
        data, pagination = _paginate(records, page, page_size)
        return {
            "fromDate": from_date.isoformat(),
            "toDate": to_date.isoformat(),
            "currency": "INR",
            "data": data,
            "pagination": pagination,
        }

    def mutual_funds(
        self,
        from_date: date,
        to_date: date,
        amc_code: str | None,
        fund_code: str | None,
        search: str | None,
        page: int,
        page_size: int,
        sort_by: str | None,
        sort_order: str,
    ) -> dict[str, Any]:
        df = self._filtered(from_date, to_date)
        if amc_code:
            df = df[df["AMC_CODE"].str.upper() == amc_code.strip().upper()]
        if fund_code:
            df = df[df["PRODCODE"].str.upper() == fund_code.strip().upper()]
        if search:
            q = search.strip().lower()
            df = df[
                df["SCHEME"].str.lower().str.contains(q, na=False, regex=False)
                | df["PRODCODE"].str.lower().str.contains(q, na=False, regex=False)
                | df["AMC_CODE"].str.lower().str.contains(q, na=False, regex=False)
            ]

        grouped = (
            df.groupby(["AMC_CODE", "PRODCODE", "SCHEME"], dropna=False)
            .agg(
                totalInvestedAmount=("AMOUNT", "sum"),
                totalUnitsPurchased=("UNITS", "sum"),
                investorCount=("PAN", "nunique"),
                transactionCount=("PRODCODE", "size"),
            )
            .reset_index()
        )
        grouped["averageNav"] = grouped.apply(
            lambda r: r["totalInvestedAmount"] / r["totalUnitsPurchased"] if r["totalUnitsPurchased"] else 0,
            axis=1,
        )
        grouped = _sort_frame(
            grouped,
            sort_by,
            sort_order,
            {
                "fundName": "SCHEME",
                "totalInvestedAmount": "totalInvestedAmount",
                "totalUnitsPurchased": "totalUnitsPurchased",
                "averageNav": "averageNav",
                "investorCount": "investorCount",
                "transactionCount": "transactionCount",
            },
            "totalInvestedAmount",
        )

        records: list[dict[str, Any]] = []
        for row in grouped.to_dict("records"):
            records.append(
                {
                    "amcCode": row["AMC_CODE"],
                    "fundCode": row["PRODCODE"],
                    "fundName": row["SCHEME"],
                    "totalInvestedAmount": _json_number(row["totalInvestedAmount"]),
                    "totalUnitsPurchased": _json_number(row["totalUnitsPurchased"]),
                    "averageNav": _json_number(row["averageNav"], 4),
                    "investorCount": int(row["investorCount"]),
                    "transactionCount": int(row["transactionCount"]),
                }
            )
        data, pagination = _paginate(records, page, page_size)
        return {
            "fromDate": from_date.isoformat(),
            "toDate": to_date.isoformat(),
            "currency": "INR",
            "data": data,
            "pagination": pagination,
        }
