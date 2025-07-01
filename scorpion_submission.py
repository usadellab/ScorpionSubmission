# -*- coding: utf-8 -*-
import json
import subprocess
import requests
import argparse
import os
import sys
from urllib.parse import quote
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta

# --- Secure Configuration Loading ---
# Tokens are now read from environment variables for security.
SCORPION_API_URL = "https://scorpion.bi.denbi.de"
SCORPION_API_KEY = os.getenv("SCORPION_API_KEY")
MATOMO_AUTH_TOKEN = os.getenv("MATOMO_AUTH_TOKEN")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
SITE_ID = '1'

# --- DEFINITIVE SERVICE CONFIGURATION ---
SERVICES_CONFIG = [
    {"display_name": "Helixer", "matomo_label": " Helixer structural gene annotation", "scorpion_service_name": "Helixer", "publications": ["Helixer: cross-species gene annotation of large eukaryotic genomes using deep learning", "Helixer-de novo Prediction of Primary Eukaryotic Gene Models Combining Deep Learning and a Hidden Markov Model"]},
    {"display_name": "Mercator4", "matomo_label": " Mercator4 - plant protein functional annotation", "scorpion_service_name": "Mercator4 - Protein Function Mapping", "publications": ["Mercator: a fast and simple web server for genome scale functional annotation of plant sequence data"]}
]

# --- KPI MAPPING ---
MATOMO_KEY_TO_INTERMEDIATE_NAME = {
    'avg_time_on_page': 'Visits Duration', 'nb_hits': 'Actions',
    'nb_actions_per_visit': 'Actions per Visit',
    'sum_daily_nb_uniq_visitors': 'Visitors', 'nb_visits': 'Visits'
}
INTERMEDIATE_NAME_TO_SCORPION_KPI = {
    'Visits Duration': 'Visit Duration', 'Actions': 'Actions',
    'Actions per Visit': 'Actions per Visit', 'Visitors': 'Unique Users',
    'Visits': 'Visits', 'Citations': 'Citations'
}

def get_matomo_data(label: str, report_date: str) -> dict | None:
    """ Fetches analytics data by executing a correctly formatted curl command. """
    encoded_label = quote(label)
    url = (f"'https://www.plabipd.de/analytics/?module=API&method=Actions.getPageTitles"
           f"&idSite={SITE_ID}&period=month&date={report_date}&format=JSON&label={encoded_label}'")
    command = f"curl -s -X POST {url} -d 'token_auth={MATOMO_AUTH_TOKEN}'"
    print(f"INFO: Executing curl for Matomo label: '{label}' for date {report_date}")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)[0] if result.stdout else None
    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        print(f"ERROR during Matomo fetch: {e}")
        return None

def get_scholar_citations(publication_titles: list) -> int:
    """ Scrapes Google Scholar for citation counts for a list of publications. """
    if not SERPAPI_KEY: return 0
    total_citations = 0
    for title in publication_titles:
        print(f"INFO: Querying SerpApi for citations of: '{title[:40]}...'")
        params = {"engine": "google_scholar", "q": title, "api_key": SERPAPI_KEY}
        try:
            response = requests.get("https://serpapi.com/search.json", params=params)
            response.raise_for_status()
            data = response.json()
            total_citations += data.get("organic_results", [{}])[0].get("inline_links", {}).get("cited_by", {}).get("total", 0)
        except Exception: continue
    return total_citations

def get_service_abbreviations() -> dict:
    """Gets all service names and their abbreviations from the ScorPIoN API."""
    print("INFO: Fetching service abbreviations from ScorPIoN API...")
    url = f"{SCORPION_API_URL}/denbi/api/v1/services"
    headers = {"X-API-Key": SCORPION_API_KEY}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return {service['name']: service['abbreviation'] for service in response.json().get("result", [])}
    except requests.RequestException as e:
        print(f"ERROR: Could not fetch service list from ScorPIoN: {e}")
        return {}

def submit_measurements_to_scorpion(service_abbreviation: str, measurements: list, is_live_run: bool):
    """Submits measurements to ScorPIoN or prints a curl command if not in live mode."""
    if not measurements:
        print(f"INFO: No valid measurements to submit for {service_abbreviation}.")
        return

    if not is_live_run:
        print(f"\n--- [DRY RUN] Submission command for service '{service_abbreviation}' ---")
        json_payload = json.dumps(measurements)
        url = f"'{SCORPION_API_URL}/denbi/api/v1/measurements?service={service_abbreviation}'"
        header_api_key = f"-H 'X-API-Key: {SCORPION_API_KEY}'"
        header_content_type = "-H 'Content-Type: application/json'"
        data_payload = f"-d '{json_payload}'"
        full_command = f"curl -X POST {url} {header_api_key} {header_content_type} {data_payload}"
        print(full_command)
        print("-" * 70)
        return

    print(f"INFO: LIVE MODE: Submitting {len(measurements)} measurements for service '{service_abbreviation}'...")
    url = f"{SCORPION_API_URL}/denbi/api/v1/measurements"
    params = {"service": service_abbreviation}
    headers = {"X-API-Key": SCORPION_API_KEY, "Content-Type": "application/json"}
    try:
        response = requests.post(url, params=params, headers=headers, data=json.dumps(measurements))
        response.raise_for_status()
        print(f"SUCCESS: Successfully submitted data for {service_abbreviation}.")
    except requests.RequestException as e:
        print(f"ERROR: Failed to submit data for {service_abbreviation}: {e}")
        print(f"Response Body: {e.response.text if e.response else 'No response'}")

def create_measurement(kpi: str, value: any, date: str) -> dict | None:
    """Creates a formatted measurement dictionary, ensuring value is an integer."""
    try:
        if value is None: return None
        return {"kpi": kpi, "date": date, "value": int(round(float(value)))}
    except (ValueError, TypeError):
        print(f"WARNING: Could not convert value '{value}' for KPI '{kpi}' to integer. Skipping.")
        return None

def main(user_date: str, is_live_run: bool):
    """ Main function to orchestrate the entire ETL process. """
    now = datetime.now(timezone.utc)
    last_month = now - relativedelta(months=1)
    is_historical_mode = (user_date != last_month.strftime('%Y-%m'))
    
    run_mode_info = "HISTORICAL mode (no citation scraping)" if is_historical_mode else "CURRENT mode (with citation scraping)"
    print(f"INFO: Running in {run_mode_info} for {user_date}.")
    
    service_map = get_service_abbreviations()
    if not service_map: return

    matomo_report_date = f"{user_date}-01"
    
    for service_info in SERVICES_CONFIG:
        scorpion_name = service_info["scorpion_service_name"]
        service_abbreviation = service_map.get(scorpion_name)
        if not service_abbreviation:
            print(f"WARNING: Could not find abbreviation for service '{scorpion_name}'. Skipping.")
            continue

        raw_matomo_data = get_matomo_data(service_info["matomo_label"], matomo_report_date)
        if raw_matomo_data:
            intermediate_metrics = {}
            for api_key, intermediate_name in MATOMO_KEY_TO_INTERMEDIATE_NAME.items():
                value = raw_matomo_data.get(api_key, 0) if api_key != 'nb_actions_per_visit' else raw_matomo_data.get('nb_hits', 0) / raw_matomo_data.get('nb_visits', 1)
                intermediate_metrics[intermediate_name] = value
            
            if not is_historical_mode:
                intermediate_metrics['Citations'] = get_scholar_citations(service_info["publications"])

            measurements_payload = []
            for intermediate_name, value in intermediate_metrics.items():
                scorpion_kpi = INTERMEDIATE_NAME_TO_SCORPION_KPI.get(intermediate_name)
                if scorpion_kpi:
                    measurements_payload.append(create_measurement(scorpion_kpi, value, user_date))
                if intermediate_name == 'Actions':
                    measurements_payload.append(create_measurement('Pageviews', value, user_date))

            valid_measurements = [m for m in measurements_payload if m is not None]
            submit_measurements_to_scorpion(service_abbreviation, valid_measurements, is_live_run)

def check_env_vars():
    """Checks for required environment variables and exits if any are missing."""
    required_vars = ["SCORPION_API_KEY", "MATOMO_AUTH_TOKEN", "SERPAPI_KEY"]
    missing_vars = [v for v in required_vars if not os.getenv(v)]
    if missing_vars:
        print("CRITICAL ERROR: The following required environment variables are not set:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nPlease set them before running the script.")
        sys.exit(1)

if __name__ == "__main__":
    check_env_vars() # Check for tokens first
    
    parser = argparse.ArgumentParser(description="Fetch analytics and submit them to the ScorPIoN API.")
    default_date = (datetime.now(timezone.utc) - relativedelta(months=1)).strftime('%Y-%m')
    
    parser.add_argument(
        "--date", type=str, default=default_date,
        help=f"The date for the report in YYYY-MM format. Defaults to last month ({default_date})."
    )
    parser.add_argument(
        "--live", action='store_true',
        help="Run in live submission mode. If not set, the script will perform a dry run."
    )
    args = parser.parse_args()
    
    try:
        datetime.strptime(args.date, '%Y-%m')
        main(args.date, args.live)
    except ValueError:
        print("ERROR: Date format is incorrect. Please use YYYY-MM.")