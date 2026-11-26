"""Streamlit dashboard for exploring scraped job listings."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from scraper import CITY, DEFAULT_OUTPUT, TARGET_KEYWORDS, fetch_jobs, filter_target_jobs

st.set_page_config(page_title="Job Market Explorer", page_icon="💼", layout="wide")
ROOT = Path(__file__).resolve().parent


def load_jobs(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    frame = pd.read_csv(path)
    for column in ("title", "company_name", "location", "tags", "job_types", "url", "description"):
        if column not in frame:
            frame[column] = ""
    if "posted_at" in frame:
        frame["posted_at"] = pd.to_datetime(frame["posted_at"], utc=True, errors="coerce")
    return frame


def split_values(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.split(r"[,|]").explode().str.strip().replace("", pd.NA).dropna()


st.title("💼 Job Market Explorer")
st.caption("Chennai listings matching Python, Data Engineering, Tableau, Power BI, or Databricks. All experience levels are included.")

with st.sidebar:
    st.header("Data")
    pages = st.number_input("Pages per keyword", min_value=1, max_value=50, value=2)
    if st.button("Fetch latest listings", type="primary", use_container_width=True):
        try:
            with st.spinner("Fetching job listings…"):
                fresh = fetch_jobs(int(pages))
                if fresh.empty:
                    st.warning(f"Youth4work returned no matching {CITY} jobs in the pages searched.")
                else:
                    ROOT.joinpath("data").mkdir(exist_ok=True)
                    if DEFAULT_OUTPUT.exists():
                        previous = filter_target_jobs(pd.read_csv(DEFAULT_OUTPUT))
                        fresh = pd.concat([previous, fresh], ignore_index=True)
                    fresh = fresh.drop_duplicates(subset="url", keep="last")
                    fresh.to_csv(DEFAULT_OUTPUT, index=False)
                    st.success(f"Saved {len(fresh):,} unique Chennai keyword matches.")
        except Exception as exc:
            st.error(f"Could not fetch listings: {exc}")
    st.caption("Source: [Youth4work public jobs API](https://mcp.youth4work.com/docs). Search calls are read-only and do not require sign-in.")

jobs = filter_target_jobs(load_jobs(DEFAULT_OUTPUT))
if jobs.empty:
    st.info(f"No {CITY} listings matching the target keywords are saved yet. Use **Fetch latest listings** to search Youth4work.")
    st.stop()

# Interactive filters
with st.sidebar:
    st.header("Filters")
    query = st.text_input("Search within matching jobs")
    selected_keywords = st.multiselect("Target keywords", list(TARGET_KEYWORDS), default=list(TARGET_KEYWORDS))
    types = split_values(jobs["job_types"]).unique().tolist()
    selected_types = st.multiselect("Job type", sorted(types))

filtered = filter_target_jobs(jobs, selected_keywords)
if query:
    mask = filtered[["title", "company_name", "tags", "description"]].fillna("").astype(str).agg(" ".join, axis=1).str.contains(query, case=False, regex=False)
    filtered = filtered[mask]
if selected_types:
    filtered = filtered[filtered["job_types"].fillna("").apply(lambda x: any(t in str(x).split(", ") for t in selected_types))]

companies = filtered["company_name"].replace("", pd.NA).nunique()
experience_levels = filtered["experience"].replace("", pd.NA).dropna().nunique() if "experience" in filtered else 0
keywords_found = filtered["matched_keywords"].replace("", pd.NA).dropna().nunique()
col1, col2, col3, col4 = st.columns(4)
col1.metric("Listings", f"{len(filtered):,}")
col2.metric("Companies", f"{companies:,}")
col3.metric("Experience ranges", f"{experience_levels:,}")
col4.metric("Keyword categories", f"{keywords_found:,}")

left, right = st.columns(2)
with left:
    st.subheader("Most common listed skills")
    skill_counts = split_values(filtered["tags"]).value_counts().head(15).rename_axis("Skill").reset_index(name="Listings")
    if skill_counts.empty:
        st.info("No skill data available.")
    else:
        st.plotly_chart(px.bar(skill_counts, x="Listings", y="Skill", orientation="h"), use_container_width=True)
with right:
    st.subheader("Listings by requested keyword")
    keyword_counts = split_values(filtered["matched_keywords"]).value_counts().rename_axis("Keyword").reset_index(name="Listings")
    if keyword_counts.empty:
        st.info("No keyword matches available for this filter.")
    else:
        st.plotly_chart(px.bar(keyword_counts, x="Listings", y="Keyword", orientation="h"), use_container_width=True)

left, right = st.columns(2)
with left:
    st.subheader("Job type mix")
    type_counts = split_values(filtered["job_types"]).value_counts().rename_axis("Job type").reset_index(name="Listings")
    if type_counts.empty:
        st.info("No job type data available.")
    else:
        st.plotly_chart(px.pie(type_counts, names="Job type", values="Listings", hole=0.45), use_container_width=True)
with right:
    st.subheader("Experience range (all levels included)")
    if "experience" in filtered and filtered["experience"].notna().any():
        experience_counts = filtered["experience"].fillna("Not specified").value_counts().rename_axis("Experience").reset_index(name="Listings")
        st.plotly_chart(px.bar(experience_counts, x="Experience", y="Listings"), use_container_width=True)
    else:
        st.info("Experience data is not available.")

st.subheader("Company activity")
company_counts = filtered["company_name"].replace("", "Unspecified").value_counts().head(10).rename_axis("Company").reset_index(name="Listings")
st.dataframe(company_counts, use_container_width=True, hide_index=True)

st.subheader("Listings (all experience levels)")
columns = [c for c in ["title", "matched_keywords", "company_name", "location", "job_types", "experience", "salary_lpa", "posted_at", "url"] if c in filtered]
st.dataframe(filtered[columns].sort_values("posted_at", ascending=False, na_position="last") if "posted_at" in columns else filtered[columns], use_container_width=True, hide_index=True, column_config={"url": st.column_config.LinkColumn("Apply / listing", display_text="Open listing")})
st.download_button("Download filtered CSV", filtered.to_csv(index=False).encode("utf-8"), "filtered_jobs.csv", "text/csv")
