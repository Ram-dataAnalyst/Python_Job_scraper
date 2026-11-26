# Job Market Explorer

A Python and Streamlit dashboard for Chennai job listings matching Python, Data Engineering, Tableau, Power BI, and Databricks.

## Data source

This project uses Youth4work's documented, read-only public jobs API. It searches the Indian city of Chennai separately for each selected keyword, requires no API key or sign-in, and returns public listing fields including job title, company, skills, experience range, salary range, posting date, and job link. See the [Youth4work API documentation](https://mcp.youth4work.com/docs).

The project does not filter by experience level. Listings with unspecified experience are retained as well.

## Setup

Use Python 3.10 or later. From this folder:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Collect and view jobs

```powershell
python scraper.py --pages 2
streamlit run app.py
```

`--pages` controls the maximum number of pages fetched per keyword (20 results per page, up to 50 pages per keyword). The scraper observes the API's pagination and stops early when there are no more results. Collected listings are saved to `data/jobs.csv` and deduplicated by URL.

The dashboard also has a fetch button, keyword filters, and CSV download. Charts summarize keyword matches, locations, job types, experience ranges, and companies. The API's public rate limit is 60 requests per minute per IP; requests are made sequentially with a pause between pages.
