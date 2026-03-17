#!/usr/bin/env python3
"""
fetch_mco.py
Fetches 8 days of MCO arrival/departure data from FlightAware AeroAPI
and writes structured JSON to data/mco_flights.json
"""

import os
import json
import requests
from datetime import datetime, timedelta, timezone
from collections import defaultdict

API_KEY = os.environ.get("AEROAPI_KEY", "")
BASE_URL = "https://aeroapi.flightaware.com/aeroapi"
AIRPORT = "KMCO"

HEADERS = {"x-apikey": API_KEY}

# Top MCO route city names
CITY_NAMES = {
    "ATL": "Atlanta", "ORD": "Chicago O'Hare", "EWR": "Newark",
    "BOS": "Boston", "LGA": "New York LaGuardia", "PHL": "Philadelphia",
    "SJU": "San Juan", "BWI": "Baltimore", "DTW": "Detroit",
    "JFK": "New York JFK", "DFW": "Dallas/Fort Worth", "LAX": "Los Angeles",
    "DEN": "Denver", "MIA": "Miami", "TPA": "Tampa", "CLT": "Charlotte",
    "MSP": "Minneapolis", "SEA": "Seattle", "SFO": "San Francisco",
    "IAD": "Washington Dulles", "BNA": "Nashville", "AUS": "Austin",
    "LAS": "Las Vegas", "MDW": "Chicago Midway", "BDL": "Hartford",
    "RDU": "Raleigh", "PIT": "Pittsburgh", "CMH": "Columbus",
    "CLE": "Cleveland", "IND": "Indianapolis", "STL": "St. Louis",
    "MKE": "Milwaukee", "MCI": "Kansas City", "SNA": "Orange County",
    "SAN": "San Diego", "PDX": "Portland", "MSY": "New Orleans",
    "JAX": "Jacksonville", "RSW": "Fort Myers", "GSP": "Greenville-Spartanburg",
    "CVG": "Cincinnati", "SRQ": "Sarasota", "PFN": "Panama City",
    "DAB": "Daytona Beach", "ACY": "Atlantic City", "ORF": "Norfolk",
    "RIC": "Richmond", "BUF": "Buffalo", "SYR": "Syracuse",
    "ALB": "Albany", "PWM": "Portland ME", "BTV": "Burlington",
    "MHT": "Manchester NH", "PVD": "Providence", "HPN": "White Plains",
    "ISP": "Long Island", "ABE": "Allentown", "AVP": "Scranton"
}

DELAY_THRESHOLD_SEC = 900  # 15 minutes


def fetch_flights(endpoint, date_str):
    """Fetch all pages for a given endpoint + date."""
    url = f"{BASE_URL}/airports/{AIRPORT}/flights/{endpoint}"
    params = {"start": f"{date_str}T00:00:00Z", "end": f"{date_str}T23:59:59Z", "max_pages": 3}
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data.get(endpoint, [])
    except Exception as e:
        print(f"  Warning: {endpoint} {date_str} â {e}")
        return []


def process_day(date_str, label):
    """Process one day of arrivals and departures."""
    print(f"  Fetching {label} ({date_str})...")

    arrivals = fetch_flights("arrivals", date_str)
    departures = fetch_flights("departures", date_str)

    # --- Arrivals ---
    arr_delays = 0
    arr_cancels = 0
    total_delay_sec = 0
    delayed_count = 0
    arr_by_route = defaultdict(lambda: {"delays": 0, "cancels": 0})

    for f in arrivals:
        origin = f.get("origin") or {}
        code = origin.get("code_iata") or origin.get("code_icao", "???")
        if len(code) == 4 and code.startswith("K"):
            code = code[1:]  # strip K prefix from ICAO

        if f.get("cancelled"):
            arr_cancels += 1
            arr_by_route[code]["cancels"] += 1
        else:
            delay = f.get("arrival_delay") or 0
            if delay > DELAY_THRESHOLD_SEC:
                arr_delays += 1
                arr_by_route[code]["delays"] += 1
                total_delay_sec += delay
                delayed_count += 1

    # --- Departures ---
    dep_delays = 0
    dep_cancels = 0
    dep_by_route = defaultdict(lambda: {"delays": 0, "cancels": 0})

    for f in departures:
        dest = f.get("destination") or {}
        code = dest.get("code_iata") or dest.get("code_icao", "???")
        if len(code) == 4 and code.startswith("K"):
            code = code[1:]

        if f.get("cancelled"):
            dep_cancels += 1
            dep_by_route[code]["cancels"] += 1
        else:
            delay = f.get("departure_delay") or 0
            if delay > DELAY_THRESHOLD_SEC:
                dep_delays += 1
                dep_by_route[code]["delays"] += 1

    # --- Merge routes ---
    all_codes = set(list(arr_by_route.keys()) + list(dep_by_route.keys()))
    routes = []
    for code in sorted(all_codes):
        if code in ("???", "", "ZZZ"):
            continue
        a = arr_by_route.get(code, {})
        d = dep_by_route.get(code, {})
        routes.append({
            "code": code,
            "name": CITY_NAMES.get(code, code),
            "arr_delays": a.get("delays", 0),
            "arr_cancels": a.get("cancels", 0),
            "dep_delays": d.get("delays", 0),
            "dep_cancels": d.get("cancels", 0),
        })

    avg_delay = round(total_delay_sec / delayed_count / 60) if delayed_count else 0

    return {
        "label": label,
        "date": date_str,
        "scheduled": len(arrivals) + len(departures),
        "arr_delays": arr_delays,
        "arr_cancels": arr_cancels,
        "dep_delays": dep_delays,
        "dep_cancels": dep_cancels,
        "avg_delay_min": avg_delay,
        "routes": routes,
    }


def main():
    if not API_KEY:
        print("ERROR: AEROAPI_KEY environment variable not set.")
        exit(1)

    print(f"Fetching 8 days of MCO data...")
    now_et = datetime.now(timezone.utc) - timedelta(hours=5)  # rough ET

    days = []
    for i in range(8):
        d = now_et - timedelta(days=i)
        date_str = d.strftime("%Y-%m-%d")
        label = "Today" if i == 0 else "Yesterday" if i == 1 else \
            d.strftime("%a %-m/%-d")
        day_data = process_day(date_str, label)
        days.append(day_data)

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "airport": "MCO",
        "days": days,
    }

    os.makedirs("data", exist_ok=True)
    with open("data/mco_flights.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nDone. Wrote data/mco_flights.json")
    print(f"  Today: {days[0]['arr_delays']+days[0]['dep_delays']} delays, "
          f"{days[0]['arr_cancels']+days[0]['dep_cancels']} cancels")


if __name__ == "__main__":
    main()
