# fetch_mco.py - Fetches 8 days of MCO data from FlightAware AeroAPI

import os
import json
import time
import requests
from datetime import datetime, timedelta, timezone
from collections import defaultdict

API_KEY = os.environ.get('AEROAPI_KEY', '')
BASE_URL = 'https://aeroapi.flightaware.com/aeroapi'
AIRPORT = 'KMCO'
HEADERS = {'x-apikey': API_KEY}
RATE_LIMIT_DELAY = 5
DELAY_THRESHOLD_SEC = 900

CITY_NAMES = {
    'ATL': 'Atlanta',
    'ORD': 'Chicago OHare',
    'EWR': 'Newark',
    'BOS': 'Boston',
    'LGA': 'New York LaGuardia',
    'PHL': 'Philadelphia',
    'SJU': 'San Juan',
    'BWI': 'Baltimore',
    'DTW': 'Detroit',
    'JFK': 'New York JFK',
    'DFW': 'Dallas Fort Worth',
    'LAX': 'Los Angeles',
    'DEN': 'Denver',
    'MIA': 'Miami',
    'TPA': 'Tampa',
    'CLT': 'Charlotte',
    'MSP': 'Minneapolis',
    'SEA': 'Seattle',
    'SFO': 'San Francisco',
    'IAD': 'Washington Dulles',
    'BNA': 'Nashville',
    'AUS': 'Austin',
    'LAS': 'Las Vegas',
    'MDW': 'Chicago Midway',
    'BDL': 'Hartford',
    'RDU': 'Raleigh',
    'PIT': 'Pittsburgh',
    'CMH': 'Columbus',
    'CLE': 'Cleveland',
    'IND': 'Indianapolis',
    'STL': 'St Louis',
    'MKE': 'Milwaukee',
    'MCI': 'Kansas City',
    'SNA': 'Orange County',
    'SAN': 'San Diego',
    'PDX': 'Portland',
    'MSY': 'New Orleans',
    'JAX': 'Jacksonville',
    'RSW': 'Fort Myers',
    'GSP': 'Greenville',
    'CVG': 'Cincinnati',
    'SRQ': 'Sarasota',
    'DAB': 'Daytona Beach',
    'ORF': 'Norfolk',
    'RIC': 'Richmond',
    'BUF': 'Buffalo',
}


def safe_code(airport_dict):
    if not airport_dict or not isinstance(airport_dict, dict):
        return 'UNK'
    code = airport_dict.get('code_iata') or airport_dict.get('code_icao')
    if not code or not isinstance(code, str):
        return 'UNK'
    code = code.strip()
    if len(code) == 4 and code.startswith('K'):
        code = code[1:]
    return code if code else 'UNK'


def fetch_flights(endpoint, date_str, retries=3):
    url = BASE_URL + '/airports/' + AIRPORT + '/flights/' + endpoint
    params = {
        'start': date_str + 'T00:00:00Z',
        'end': date_str + 'T23:59:59Z',
        'max_pages': 3,
    }
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
            if resp.status_code == 429:
                wait = 15 * (attempt + 1)
                print('  Rate limited - waiting ' + str(wait) + 's...')
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json().get(endpoint, [])
        except Exception as e:
            print('  Warning: ' + endpoint + ' ' + date_str + ' - ' + str(e))
            if attempt < retries - 1:
                time.sleep(5)
    return []


def process_day(date_str, label):
    print('  Fetching ' + label + ' (' + date_str + ')...')

    arrivals = fetch_flights('arrivals', date_str)
    time.sleep(RATE_LIMIT_DELAY)
    departures = fetch_flights('departures', date_str)
    time.sleep(RATE_LIMIT_DELAY)

    arr_delays = 0
    arr_cancels = 0
    total_delay_sec = 0
    delayed_count = 0
    arr_by_route = defaultdict(lambda: {'delays': 0, 'cancels': 0})

    for f in arrivals:
        code = safe_code(f.get('origin'))
        if code == 'UNK':
            continue
        if f.get('cancelled'):
            arr_cancels += 1
            arr_by_route[code]['cancels'] += 1
        else:
            delay = f.get('arrival_delay') or 0
            if isinstance(delay, (int, float)) and delay > DELAY_THRESHOLD_SEC:
                arr_delays += 1
                arr_by_route[code]['delays'] += 1
                total_delay_sec += delay
                delayed_count += 1

    dep_delays = 0
    dep_cancels = 0
    dep_by_route = defaultdict(lambda: {'delays': 0, 'cancels': 0})

    for f in departures:
        code = safe_code(f.get('destination'))
        if code == 'UNK':
            continue
        if f.get('cancelled'):
            dep_cancels += 1
            dep_by_route[code]['cancels'] += 1
        else:
            delay = f.get('departure_delay') or 0
            if isinstance(delay, (int, float)) and delay > DELAY_THRESHOLD_SEC:
                dep_delays += 1
                dep_by_route[code]['delays'] += 1

    all_codes = set(list(arr_by_route.keys()) + list(dep_by_route.keys()))
    routes = []
    for code in sorted(all_codes):
        if code in ('UNK', '', 'ZZZ'):
            continue
        a = arr_by_route.get(code, {})
        d = dep_by_route.get(code, {})
        routes.append({
            'code': code,
            'name': CITY_NAMES.get(code, code),
            'arr_delays': a.get('delays', 0),
            'arr_cancels': a.get('cancels', 0),
            'dep_delays': d.get('delays', 0),
            'dep_cancels': d.get('cancels', 0),
        })

    avg_delay = round(total_delay_sec / delayed_count / 60) if delayed_count else 0

    return {
        'label': label,
        'date': date_str,
        'scheduled': len(arrivals) + len(departures),
        'arr_delays': arr_delays,
        'arr_cancels': arr_cancels,
        'dep_delays': dep_delays,
        'dep_cancels': dep_cancels,
        'avg_delay_min': avg_delay,
        'routes': routes,
    }


def main():
    if not API_KEY:
        print('ERROR: AEROAPI_KEY secret is not set in GitHub repo settings.')
        exit(1)

    print('Fetching 8 days of MCO data...')
    now_et = datetime.now(timezone.utc) - timedelta(hours=5)

    days = []
    for i in range(8):
        d = now_et - timedelta(days=i)
        date_str = d.strftime('%Y-%m-%d')
        if i == 0:
            label = 'Today'
        elif i == 1:
            label = 'Yesterday'
        else:
            label = d.strftime('%a %-m/%-d')
        days.append(process_day(date_str, label))

    output = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'airport': 'MCO',
        'days': days,
    }

    os.makedirs('data', exist_ok=True)
    with open('data/mco_flights.json', 'w') as f:
        json.dump(output, f, indent=2)

    print('Done. Wrote data/mco_flights.json')
    print('Today: ' + str(days[0]['arr_delays'] + days[0]['dep_delays']) + ' delays, ' +
          str(days[0]['arr_cancels'] + days[0]['dep_cancels']) + ' cancels')


if __name__ == '__main__':
    main()
