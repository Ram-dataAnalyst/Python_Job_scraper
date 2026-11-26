"""Fetch Chennai job listings from Youth4work's public India jobs API."""
from __future__ import annotations

import argparse
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

API_URL = "https://mcp.youth4work.com/api/v1/public/tools/search_jobs"
ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT = ROOT / "data" / "jobs.csv"
CITY = "Chennai"
TARGET_KEYWORDS = {
    "Python": ("python",),
    "Data Engineering": ("data engineering", "data engineer", "data-engineer"),
    "Tableau": ("tableau",),
    "Power BI": ("power bi", "powerbi"),
    "Databricks": ("databricks",),
}


def filter_target_jobs(frame: pd.DataFrame, keywords=None) -> pd.DataFrame:
    """Keep Chennai jobs matching any selected keyword; retain all experience levels."""
    if frame.empty:
        return frame.copy()
    selected = list(keywords if keywords is not None else TARGET_KEYWORDS)
    selected = [key for key in selected if key in TARGET_KEYWORDS]
    if not selected:
        return frame.iloc[0:0].copy()

    city_column = frame.get("location", pd.Series("", index=frame.index))
    city_mask = city_column.fillna("").astype(str).str.contains(CITY, case=False, regex=False)
    searchable_columns = [column for column in ("title", "tags", "description") if column in frame]
    searchable = frame[searchable_columns].fillna("").astype(str).agg(" ".join, axis=1).str.lower()
    matched = {
        key: searchable.apply(lambda text: any(term in text for term in TARGET_KEYWORDS[key]))
        for key in selected
    }
    keyword_mask = pd.concat(matched, axis=1).any(axis=1)
    result = frame.loc[city_mask & keyword_mask].copy()
    result["matched_keywords"] = [
        ", ".join(key for key in selected if matched[key].loc[index])
        for index in result.index
    ]
    return result


def fetch_jobs(pages: int = 2, pause: float = 0.25) -> pd.DataFrame:
    """Search each target term in Chennai, fetching up to `pages` pages per term."""
    if not 1 <= pages <= 50:
        raise ValueError("pages must be between 1 and 50")

    session = requests.Session()
    session.headers.update({"User-Agent": "JobMarketDashboard/1.0", "Accept": "application/json"})
    records: list[dict] = []
    for keyword in TARGET_KEYWORDS:
        for page in range(1, pages + 1):
            response = session.post(
                API_URL,
                json={"query": keyword, "city": CITY, "page": page},
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            results = payload.get("results", [])
            if not isinstance(results, list):
                raise ValueError("Unexpected Youth4work response: 'results' is not a list")
            for job in results:
                records.append({
                    "id": job.get("id", ""),
                    "title": job.get("title", ""),
                    "company_name": job.get("company", ""),
                    "location": job.get("city", ""),
                    "tags": job.get("skills", ""),
                    "job_types": job.get("type", ""),
                    "experience": job.get("experienceYears", "Not specified"),
                    "salary_lpa": job.get("salaryLakhsPerYear", ""),
                    "government": job.get("government", False),
                    "posted_at": job.get("posted", ""),
                    "url": job.get("url", ""),
                    "description": "",
                    "source": "Youth4work",
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                })
            if not payload.get("hasMore", False):
                break
            if pause:
                time.sleep(pause)

    if not records:
        return pd.DataFrame()
    frame = pd.DataFrame(records)
    frame = frame.drop_duplicates(subset="url", keep="last")
    return filter_target_jobs(frame)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", type=int, default=2, help="Maximum pages per keyword (default: 2)")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="CSV destination")
    args = parser.parse_args()

    jobs = fetch_jobs(args.pages)
    if jobs.empty:
        print("No matching Chennai listings returned by Youth4work.")
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        old = pd.read_csv(args.output)
        # Keep only rows matching the current city and keyword scope before combining.
        old = filter_target_jobs(old)
        jobs = pd.concat([old, jobs], ignore_index=True)
    if "url" in jobs:
        jobs = jobs.drop_duplicates(subset="url", keep="last")
    jobs.to_csv(args.output, index=False)
    print(f"Saved {len(jobs):,} unique Chennai listings to {args.output}")


if __name__ == "__main__":
    main()
