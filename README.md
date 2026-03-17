# MCO Flight Operations Dashboard

An 8-day trend dashboard for Orlando International Airport (MCO) showing arrival/departure delays and cancellations by route. Runs on GitHub Pages with data fetched nightly via GitHub Actions.

## Live Demo
Once deployed: `https://[your-username].github.io/mco-flight-dashboard/`

## Architecture

```
mco-flight-dashboard/
├── index.html                        # Dashboard (reads local JSON, no CORS issues)
├── data/
│   └── mco_flights.json              # Generated nightly by GitHub Actions
├── scripts/
│   └── fetch_mco.py                  # Python script that calls FlightAware AeroAPI
└── .github/workflows/
    └── fetch-mco-data.yml            # Scheduled workflow (runs 11:59 PM ET daily)
```

**Why this approach?** FlightAware's AeroAPI blocks direct browser requests (CORS). By fetching server-side via GitHub Actions and writing to a static JSON file, the dashboard reads local data with zero CORS issues.

---

## Setup Instructions

### 1. Create the GitHub repo

```bash
git init mco-flight-dashboard
cd mco-flight-dashboard
# copy all files here
git add .
git commit -m "Initial dashboard"
git remote add origin https://github.com/YOUR_USERNAME/mco-flight-dashboard.git
git push -u origin main
```

### 2. Add your FlightAware AeroAPI key as a secret

1. Get a free API key at [flightaware.com/commercial/aeroapi](https://flightaware.com/commercial/aeroapi/) — free tier includes 10,000 queries/month
2. In your GitHub repo: **Settings → Secrets and variables → Actions → New repository secret**
3. Name: `AEROAPI_KEY`
4. Value: your API key

### 3. Enable GitHub Pages

1. Repo **Settings → Pages**
2. Source: **Deploy from a branch**
3. Branch: `main` / `/ (root)`
4. Save

### 4. Run the workflow manually first

1. Go to **Actions tab** in your repo
2. Click **Fetch MCO Flight Data**
3. Click **Run workflow**

This populates `data/mco_flights.json` with real data immediately. After that it runs automatically every night.

### 5. Visit your dashboard

`https://[your-username].github.io/mco-flight-dashboard/`

---

## Dashboard Features

- **8-day cancellation trend** — stacked bar (arrivals + departures) with cancel rate % line
- **8-day delay trend** — stacked bar with average minutes late line
- **Combined overview** — all four metrics side by side across 8 days
- **Live ticker** — today's most disrupted routes scrolling across the top
- **Route breakdown tables** — arrivals into MCO by origin city / departures by destination
- **Filters** — switch between any of the 8 days, sort by delays/cancels/total, filter by minimum disruption count
- **Tabs** — view arrivals only, departures only, or combined

---

## Customization

**Change the airport:** Edit `AIRPORT = "KMCO"` in `scripts/fetch_mco.py`

**Change refresh schedule:** Edit the cron in `.github/workflows/fetch-mco-data.yml`
- Current: `'59 3 * * *'` = 11:59 PM ET daily
- More frequent: `'0 */6 * * *'` = every 6 hours (watch API quota)

**Add more city names:** Extend the `CITY_NAMES` dict in `fetch_mco.py`

---

## API Quota

FlightAware AeroAPI free tier: **10,000 queries/month**

This dashboard uses ~2 queries/day (arrivals + departures per day × 8 days on first run, then 2/day ongoing). Well within free tier limits.
