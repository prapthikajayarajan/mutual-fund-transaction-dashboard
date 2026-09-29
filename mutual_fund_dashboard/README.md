# Mutual Fund Transaction Dashboard

A runnable FastAPI dashboard implementing the four requested dashboard contracts against the supplied transaction CSV.

## Features

1. **Investor-wise Purchase Summary per Mutual Fund**
   - Purchase amount, units and transaction count grouped by investor + mutual fund.
   - Investor filter and global date range.

2. **Mutual Fund-wise Summary per Investor**
   - Purchase amount, units and transaction count grouped by mutual fund + investor.
   - Mutual-fund filter and global date range.

3. **Investor List with Purchase Details**
   - PAN, investor name, total investment, units, fund count and transaction count.
   - Name/PAN search and global date range.

4. **Mutual Fund Summary**
   - Total purchase amount, units, weighted/effective average NAV, investor count and transaction count.
   - Fund search and global date range.

The dashboard also includes KPI cards, CSV export of each visible table, and interactive API documentation at `/docs`.

## Purchase business rule

Only rows satisfying both rules are included:

- `TRXNSTAT == "Y"`
- `TRXN_TYPE_FLAG` is either `Switch In` or `Additional Purchase Systematic`

`Partial Switch Out` rows are excluded.

Average NAV is calculated as:

`SUM(AMOUNT) / SUM(UNITS)`

## Run locally

Requires Python 3.10+.

### Windows PowerShell

```powershell
cd mutual_fund_dashboard
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

### macOS / Linux

```bash
cd mutual_fund_dashboard
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

Open:

- Dashboard: `http://127.0.0.1:8000`
- Swagger API docs: `http://127.0.0.1:8000/docs`

## Use a different dataset

By default the project reads `data/dataset.csv`. You can point it to another CSV:

### PowerShell

```powershell
$env:DATASET_PATH="C:\path\to\dataset.csv"
python -m uvicorn app.main:app --reload --port 8000
```

### macOS / Linux

```bash
DATASET_PATH=/path/to/dataset.csv python -m uvicorn app.main:app --reload --port 8000
```

The loader normalizes source exports whose column names and values are wrapped in quotes, as in the supplied file.

## APIs

- `GET /api/v1/dashboard/investor-fund-summary`
- `GET /api/v1/dashboard/fund-investor-summary`
- `GET /api/v1/dashboard/investors`
- `GET /api/v1/dashboard/mutual-funds`

Supporting endpoints:

- `GET /api/v1/dashboard/overview`
- `GET /api/v1/dashboard/metadata`
- `GET /health`

All four main endpoints accept inclusive `fromDate` and `toDate` values in `YYYY-MM-DD` format.

## Tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

## Production notes

The included CSV contains personal data (PAN and investor names). In production, add authentication/authorization and consider PAN masking for roles that do not need full PAN visibility. For larger datasets, replace the CSV-backed service with database queries while keeping the same API response contracts.
