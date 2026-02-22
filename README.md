# NYC Yellow Taxi Trip Dashboard 🚕

An interactive two-page Streamlit dashboard that loads, validates, cleans, and visualises NYC Yellow Taxi trip data from January 2024.

## Live Dashboard

> **Deployed URL:** [https://myappappcopy-to9rrpvlwqnrudeuaa4qxl.streamlit.app](https://myappappcopy-to9rrpvlwqnrudeuaa4qxl.streamlit.app)

## Project Structure

```
my_app/
├── app.py                  # Main page — load, validate, clean, summarise
├── pages/
│   └── Dashboard.py        # Page 2 — Altair visualisations with interpretations
├── requirements.txt        # Pinned Python dependencies
├── .gitignore              # Excludes data files from version control
└── README.md               # This file
```

## Features

| Page | Description |
|------|-------------|
| **Main (app.py)** | Downloads trip data & taxi zone lookup, runs Pydantic validation, applies cleaning filters (nulls, invalid distances/times/fares), engineers features, executes DuckDB summary queries, and displays key metrics. |
| **Dashboard** | Renders 5 Altair charts (top pickup zones, avg fare by hour, distance distribution, payment types, day × hour heatmap) each with a refined statistical interpretation. |

## Setup Instructions

### Prerequisites

- Python 3.10 or higher

### Local Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/your-repo-name.git
   cd your-repo-name
   ```

2. **Create a virtual environment** (recommended)
   ```bash
   python -m venv venv
   source venv/bin/activate        # macOS / Linux
   venv\Scripts\activate           # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the app**
   ```bash
   streamlit run app.py
   ```
   The app will open at `http://localhost:8501`. Use the sidebar to navigate to the Dashboard page.

### Deploying to Streamlit Community Cloud

1. Push your repo to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io) and connect your repository.
3. Set the main file path to `app.py`.
4. Deploy — Streamlit will install packages from `requirements.txt` automatically.

## Data Sources

| Dataset | Source |
|---------|--------|
| Yellow Taxi Trip Records (Jan 2024) | [NYC TLC](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page) |
| Taxi Zone Lookup | [NYC TLC](https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv) |

Both datasets are downloaded at runtime — no local data files are required.

## Tech Stack

- **Streamlit** — web app framework
- **Polars** — high-performance DataFrame operations
- **DuckDB** — in-process SQL analytics
- **Altair** — declarative statistical visualisation
- **Pydantic** — data validation
- **Pandas / NumPy** — Streamlit widget compatibility
