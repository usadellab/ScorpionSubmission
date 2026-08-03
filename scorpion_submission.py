# -*- coding: utf-8 -*-
import json
import requests
import argparse
import os
import sys
import subprocess
from urllib.parse import quote
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta

__version__ = "1.0.2"

# --- Secure Configuration Loading ---
# Tokens are read from environment variables for security.
SCORPION_API_URL = "https://scorpion.bi.denbi.de"
SCORPION_API_KEY = os.getenv("SCORPION_API_KEY")
MATOMO_AUTH_TOKEN = os.getenv("MATOMO_AUTH_TOKEN")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") # Optional, for higher API rate limits
SITE_ID = '1'
MATOMO_BASE_URL = "https://www.plabipd.de/analytics/"
# Override DNS resolution for Matomo requests (e.g. after a server migration where DNS not yet updated).
# Format: "hostname:port:ip"  — maps directly to curl's --resolve flag.
# Set to None to disable and use normal DNS.
MATOMO_RESOLVE = None  # e.g. "www.plabipd.de:443:10.100.50.34"

# --- DEFINITIVE SERVICE CONFIGURATION ---
# The 'scorpion_service_name' values have been updated to exactly match the names in the ScorPIoN API.
SERVICES_CONFIG = [
    {
        "display_name": "Helixer",
        "scorpion_service_name": "Helixer",
        "publications": [
            {
                "title": "Helixer: cross-species gene annotation of large eukaryotic genomes using deep learning",
                "author_id": "fGsO4gYAAAAJ",
                "citation_id": "fGsO4gYAAAAJ:kkE12xK_jI8C"
            },
            {
                "title": "Helixer-de novo Prediction of Primary Eukaryotic Gene Models Combining Deep Learning and a Hidden Markov Model",
                "author_id": "RjKYuDIAAAAJ",
                "citation_id": "RjKYuDIAAAAJ:q3CdL3IzO_QC"
            },
            {
                "title": "Helixer: ab initio prediction of primary eukaryotic gene models combining deep learning and a hidden Markov model",
                "author_id": "RjKYuDIAAAAJ",
                "citation_id": "RjKYuDIAAAAJ:-FonjvnnhkoC"
            }
        ],
        "source_type": "matomo_page_title",
        "source_details": {"label": " Helixer structural gene annotation"},
        "executions_local_sources": [
            {"path": "/mnt/webdata/plabipd/projects/Helixer/download", "type": "file", "pattern": ".zip"}
        ]
    },
    {
        "display_name": "Mercator4",
        "scorpion_service_name": "Mercator4 - Protein Function Mapping",
        "publications": [
            {
                "title": "Mercator: a fast and simple web server for genome scale functional annotation of plant sequence data",
                "author_id": "RjKYuDIAAAAJ",
                "citation_id": "RjKYuDIAAAAJ:g5m5HwL7SMYC"
            }
        ],
        "source_type": "matomo_page_title",
        "source_details": {"label": " Mercator4 - plant protein functional annotation"},
        "executions_local_sources": [
            {"path": "/mnt/webdata/plabipd/projects/MercatorLegacy/work", "type": "directory", "pattern": ""},
            {"path": "/mnt/webdata/plabipd/projects/Mercator/download", "type": "file", "pattern": "_fasta.zip"}
        ]
    },
    {
        "display_name": "Trimmomatic",
        "scorpion_service_name": "Trimmomatic - NGS Read Trimmer",  # Corrected name
        "publications": [
            {
                "title": "Trimmomatic: a flexible trimmer for Illumina sequence data",
                "author_id": "RjKYuDIAAAAJ",
                "citation_id": "RjKYuDIAAAAJ:SeFeTyx0c_EC"
            },
            {
                "title": "Trimmomatic: A decade of feature-rich, high-performance NGS read preprocessing",
                "author_id": "RjKYuDIAAAAJ",
                "citation_id": "RjKYuDIAAAAJ:hCrLmN-GePgC"
            }
        ],
        "source_type": "github_release_downloads",
        "source_details": {
            "repo": "usadellab/Trimmomatic",
            "tags": ["v0.39", "v0.40", "v0.41"]
        }
    },
    {
        "display_name": "MapMan",
        "scorpion_service_name": "MapMan - Map Gene / Protein / Metabolite Data on biological Pathways",  # Corrected name
        "publications": [
            {
                "title": "A guide to using MapMan to visualize and compare Omics data in plants: a case study in the crop species, Maize",
                "author_id": "RjKYuDIAAAAJ",
                "citation_id": "RjKYuDIAAAAJ:kNdYIx-mwKoC"
            }
        ],
        "source_type": "matomo_download",
        "source_details": {"download_url": "https://www.plabipd.de/data/MapMan-3.7.1-jar-with-dependencies.jar"}
    },
    {
        "display_name": "PlabiPD",
        "scorpion_service_name": "PlabiPD - Functional annotation of plant genomes",  # Corrected name
        "publications": [
            {
                "title": "PubPlant – a continuously updated online resource for sequenced and published plant genomes",
                "author_id": "RjKYuDIAAAAJ",
                "citation_id": "RjKYuDIAAAAJ:LI9QrySNdTsC"
            }
        ],
        "source_type": "matomo_page_url_list",
        "source_details": {
            "url_paths": [
                "/pubplant_main.html",
                "/pubplant_cladogram1.html",
                "/pubplant_cladogram2.html",
                "/pubplant_overview.html",
                "/pubplant_timeline.html",
                "/pubplant_timeline1.html",
                "/plant_genomes_pa.ep",
                "/plant_genomes_pn.ep",
                "/timeline_view.ep"
            ]
        }
    }
]

# --- KPI MAPPINGS ---
# Map raw keys from different Matomo APIs to a common intermediate name
MATOMO_PAGE_TITLE_TO_INTERMEDIATE = {
    'avg_time_on_page': 'Visits Duration', 'nb_hits': 'Actions',
    'nb_actions_per_visit': 'Actions per Visit',
    'sum_daily_nb_uniq_visitors': 'Visitors', 'nb_visits': 'Visits'
}
MATOMO_SUMMARY_TO_INTERMEDIATE = {
    'avg_time_on_site': 'Visits Duration', 'nb_actions': 'Actions',
    'nb_actions_per_visit': 'Actions per Visit',
    'nb_uniq_visitors': 'Visitors', 'nb_visits': 'Visits'
}
# Map intermediate names to the official KPI names in ScorPIoN
INTERMEDIATE_NAME_TO_SCORPION_KPI = {
    'Visits Duration': 'Visit Duration', 'Actions': 'Actions',
    'Actions per Visit': 'Actions per Visit', 'Visitors': 'Unique Users',
    'Visits': 'Visits', 'Citations': 'Citations', 'Downloads': 'Downloads',
    'Executions': 'Executions'
}

def _execute_matomo_curl(api_method: str, report_date: str, extra_params_str: str = "", as_list: bool = False):
    """Generic function to execute a Matomo API curl command."""
    url = (f"{MATOMO_BASE_URL}?module=API&method={api_method}"
           f"&idSite={SITE_ID}&period=month&date={report_date}&format=JSON{extra_params_str}")
    resolve_flag = f"--resolve {MATOMO_RESOLVE} " if MATOMO_RESOLVE else ""
    command = f'curl -s {resolve_flag}-X POST "{url}" -d "token_auth={MATOMO_AUTH_TOKEN}"'
    print(f"INFO: Executing curl for Matomo method: '{api_method}' for date {report_date}")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        if not result.stdout:
            print(f"WARNING: Matomo API returned empty response for method {api_method}")
            return [] if as_list else None
        data = json.loads(result.stdout)
        if as_list:
            return data if isinstance(data, list) else []
        # Handle cases where Matomo returns a list (e.g., for page titles) vs. a direct dictionary (e.g., for summaries)
        return data[0] if isinstance(data, list) and data else data
    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        print(f"ERROR during Matomo fetch for {api_method}: {e}")
        return [] if as_list else None

def get_matomo_page_title_data(label: str, report_date: str) -> dict | None:
    """Fetches analytics data for a specific page title using curl."""
    encoded_label = quote(label)
    return _execute_matomo_curl("Actions.getPageTitles", report_date, extra_params_str=f"&label={encoded_label}")

def get_matomo_download_data(download_url: str, report_date: str) -> dict | None:
    """Fetches analytics data for a specific download URL using curl."""
    encoded_url = quote(download_url)
    return _execute_matomo_curl("Actions.getDownload", report_date, extra_params_str=f"&downloadUrl={encoded_url}")

def get_matomo_summary_data(report_date: str) -> dict | None:
    """Fetches overall site summary analytics using curl."""
    return _execute_matomo_curl("VisitsSummary.get", report_date)

def get_matomo_page_url_list_data(url_paths: list, report_date: str) -> dict | None:
    """
    Fetches Actions.getPageUrls (flattened) and sums metrics across a fixed list of
    page paths. Used for services whose usage spans several page URLs that do not
    share a common folder or filename pattern Matomo could group by (e.g. PubPlant's
    pages use unrelated legacy names like plant_genomes_pa.ep alongside pubplant_*.html),
    so the pages have to be enumerated explicitly rather than matched by prefix.
    """
    rows = _execute_matomo_curl("Actions.getPageUrls", report_date, extra_params_str="&flat=1", as_list=True)
    if not rows:
        return None
    wanted = set(url_paths)

    def row_path(row: dict) -> str:
        # Matomo's flat page-URL report has been observed to return either the bare
        # path or the full URL including domain, depending on instance/version.
        url = row.get("url") or ""
        for path in wanted:
            if url == path or url.endswith(path):
                return path
        return f"/{row.get('label', '')}"

    matches = [r for r in rows if row_path(r) in wanted]
    if not matches:
        print(f"WARNING: None of the configured page URLs were found in Matomo's report for {report_date}: {url_paths}")
        return None
    found_paths = {row_path(r) for r in matches}
    missing = wanted - found_paths
    if missing:
        print(f"WARNING: {len(missing)} configured page URL(s) had no data for {report_date}: {sorted(missing)}")
    total_hits = sum(r.get("nb_hits", 0) for r in matches)
    total_visits = sum(r.get("nb_visits", 0) for r in matches)
    total_uniq = sum(r.get("sum_daily_nb_uniq_visitors", 0) for r in matches)
    weighted_time = sum(r.get("avg_time_on_page", 0) * r.get("nb_visits", 0) for r in matches)
    print(f"INFO:   -> matched {len(matches)}/{len(url_paths)} configured page URLs.")
    return {
        "nb_hits": total_hits,
        "nb_visits": total_visits,
        "sum_daily_nb_uniq_visitors": total_uniq,
        "avg_time_on_page": (weighted_time / total_visits) if total_visits else 0,
    }

def get_github_release_downloads(repo: str, tags: str | None = None) -> int:
    """
    Fetches download count from a GitHub repository.
    If tags are specified, it sums downloads for these releases only.
    Otherwise, it sums downloads for all assets in all releases.
    """
    total_downloads = 0
    url = f"https://api.github.com/repos/{repo}/releases"
    headers = {}
    if GITHUB_TOKEN:
        headers['Authorization'] = f"token {GITHUB_TOKEN}"

    print(f"INFO: Querying GitHub API for releases of: '{repo}'")
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        releases = response.json()

        if tags:
            print(f"INFO: Searching for release with specific tags '{tags}'.")
            tags_to_find = set(tags)
            for release in releases:
                if release.get("tag_name") in tags_to_find:
                    print(f"INFO: Found release with tag '{release.get('tag_name')}'. Summing asset downloads.")
                    for asset in release.get("assets", []):
                        total_downloads += asset.get("download_count", 0)
                    tags_to_find.remove(release.get("tag_name"))
             
            if tags_to_find:
                print(f"WARNING: Could not find releases for tags: {list(tags_to_find)} in repo '{repo}'.")
        else:
            print(f"INFO: No specific tags provided. Summing downloads for all releases.")
            for release in releases:
                for asset in release.get("assets", []):
                    total_downloads += asset.get("download_count", 0)
        
        return total_downloads

    except requests.RequestException as e:
        print(f"ERROR during GitHub fetch for {repo}: {e}")
        return 0

def get_local_executions_count(sources: list, report_date: str) -> int:
    """
    Counts the number of files or directories in local directories that were modified within a specific month.
    """
    try:
        start_dt = datetime.strptime(report_date, '%Y-%m').replace(tzinfo=timezone.utc)
        end_dt = start_dt + relativedelta(months=1)
        start_ts = start_dt.timestamp()
        end_ts = end_dt.timestamp()
        print(f"INFO: Local execution time range filter: {start_dt.strftime('%Y-%m-%d %H:%M:%S')} to {end_dt.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    except ValueError:
        return 0

    total_count = 0
    
    for source in sources:
        directory_path = source.get("path")
        entry_type = source.get("type", "file")
        pattern = source.get("pattern", "")
        
        if not directory_path or not os.path.isdir(directory_path):
            print(f"WARNING: Executions directory not found or is not a directory: {directory_path}")
            continue
            
        source_count = 0
        total_scanned = 0
        matched_type = 0
        matched_pattern = 0
        
        print(f"INFO: Scanning '{directory_path}' (type={entry_type}, pattern='{pattern}')")
        
        try:
            with os.scandir(directory_path) as entries:
                for entry in entries:
                    total_scanned += 1
                    is_match = (entry_type == "file" and entry.is_file()) or (entry_type == "directory" and entry.is_dir())
                    if is_match:
                        matched_type += 1
                        if entry.name.endswith(pattern):
                            matched_pattern += 1
                            if start_ts <= entry.stat().st_mtime < end_ts:
                                source_count += 1
                                    
            print(f"INFO:   -> Scanned {total_scanned} items, {matched_type} matched type, {matched_pattern} matched pattern.")
            print(f"INFO:   -> {source_count} matches fell within the time range.")
            total_count += source_count
        except Exception as e:
            print(f"ERROR reading executions directory {directory_path}: {e}")
            
    return total_count

def get_scholar_citations(publications: list) -> int:
    """
    Fetches citation counts for a list of publications via SerpApi's Google Scholar
    author engine. Each publication must provide "author_id" and "citation_id" -
    the pinned identifiers of the paper on one of its authors' Scholar profiles.
    See README.md ("Resolving author_id and citation_id") for how these are obtained.

    Free-text title search against Google Scholar is not used here: search ranking is
    non-deterministic and can return an unrelated paper as the top hit, and for
    heavily-cited papers Scholar's own index fragments the citation graph across many
    duplicate entries with no reliable way to pick the canonical one from a text query.
    Querying "cites=<cluster_id>" directly is also not used: its total_results count
    does not match the paper's actual citation count (verified to undercount by 5-10x).
    The author-profile "view_citation" record is the only field found to return the
    correct, stable count.
    """
    if not SERPAPI_KEY: return 0
    total_citations = 0
    for pub in publications:
        title = pub.get("title", "")
        author_id = pub.get("author_id")
        citation_id = pub.get("citation_id")
        if not author_id or not citation_id:
            print(f"WARNING: No author_id/citation_id for '{title[:50]}...'. Skipping citation count.")
            continue
        print(f"INFO: Querying SerpApi for citations of: '{title[:40]}...'")
        params = {
            "engine": "google_scholar_author",
            "view_op": "view_citation",
            "author_id": author_id,
            "citation_id": citation_id,
            "api_key": SERPAPI_KEY,
        }
        try:
            response = requests.get("https://serpapi.com/search.json", params=params)
            response.raise_for_status()
            data = response.json()
            total_citations += data.get("citation", {}).get("total_citations", {}).get("cited_by", {}).get("total", 0)
        except Exception as e:
            print(f"ERROR: Could not fetch citations for '{title[:40]}...': {e}")
            continue
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

def main(user_date: str, is_live_run: bool, selected_services: list | None):
    """Main function to orchestrate the entire ETL process."""
    now = datetime.now(timezone.utc)
    last_month = now - relativedelta(months=1)
    is_historical_mode = (user_date != last_month.strftime('%Y-%m'))
    
    run_mode_info = "HISTORICAL mode (no citation/download scraping)" if is_historical_mode else "CURRENT mode (with citation/download scraping)"
    print(f"INFO: Running in {run_mode_info} for {user_date}.")

    services_to_run = SERVICES_CONFIG
    if selected_services:
        services_to_run = [s for s in SERVICES_CONFIG if s['display_name'] in selected_services]
        print(f"INFO: Running for specified services: {[s['display_name'] for s in services_to_run]}")
    else:
        print("INFO: No services specified, running for all configured services.")
    
    service_map = get_service_abbreviations()
    if not service_map: return

    matomo_report_date = f"{user_date}-01"
    
    for service_info in services_to_run:
        scorpion_name = service_info["scorpion_service_name"]
        service_abbreviation = service_map.get(scorpion_name)
        display_name = service_info["display_name"]
        
        print(f"\n--- Processing service: {display_name} ---")

        if not service_abbreviation:
            print(f"WARNING: Could not find abbreviation for service '{scorpion_name}'. Skipping.")
            continue

        intermediate_metrics = {}
        source_type = service_info['source_type']
        source_details = service_info['source_details']
        raw_data = None

        # Step 1: Fetch primary data based on source_type
        if source_type == 'matomo_page_title':
            raw_data = get_matomo_page_title_data(source_details['label'], matomo_report_date)
            if raw_data:
                for api_key, im_name in MATOMO_PAGE_TITLE_TO_INTERMEDIATE.items():
                    value = raw_data.get(api_key, 0) if api_key != 'nb_actions_per_visit' else raw_data.get('nb_hits', 0) / raw_data.get('nb_visits', 1)
                    intermediate_metrics[im_name] = value
        
        elif source_type == 'matomo_site_summary':
            raw_data = get_matomo_summary_data(matomo_report_date)
            if raw_data:
                for api_key, im_name in MATOMO_SUMMARY_TO_INTERMEDIATE.items():
                    intermediate_metrics[im_name] = raw_data.get(api_key, 0)
        
        elif source_type == 'matomo_page_url_list':
            raw_data = get_matomo_page_url_list_data(source_details['url_paths'], matomo_report_date)
            if raw_data:
                for api_key, im_name in MATOMO_PAGE_TITLE_TO_INTERMEDIATE.items():
                    value = raw_data.get(api_key, 0) if api_key != 'nb_actions_per_visit' else (raw_data.get('nb_hits', 0) / raw_data.get('nb_visits', 1) if raw_data.get('nb_visits') else 0)
                    intermediate_metrics[im_name] = value

        elif source_type == 'matomo_download':
            raw_data = get_matomo_download_data(source_details['download_url'], matomo_report_date)
            if raw_data:
                intermediate_metrics['Downloads'] = raw_data.get('nb_hits', 0)
        
        elif source_type == 'github_release_downloads':
            if not is_historical_mode:
                repo = source_details['repo']
                tags = source_details.get('tags')  # Safely get the tag, will be None if not present
                intermediate_metrics['Downloads'] = get_github_release_downloads(repo, tags)
            else:
                print("INFO: Skipping GitHub downloads fetch in historical mode.")

        # Step 2: Fetch citation data (common to most services)
        if not is_historical_mode and "publications" in service_info and service_info["publications"]:
            intermediate_metrics['Citations'] = get_scholar_citations(service_info["publications"])

        # Step 2.5: Add optional Executions KPI
        if "executions" in service_info:
            intermediate_metrics['Executions'] = service_info["executions"]
        elif "executions_local_sources" in service_info:
            intermediate_metrics['Executions'] = get_local_executions_count(service_info["executions_local_sources"], user_date)

        # Step 3: Map intermediate metrics to ScorPIoN payload
        measurements_payload = []
        for intermediate_name, value in intermediate_metrics.items():
            scorpion_kpi = INTERMEDIATE_NAME_TO_SCORPION_KPI.get(intermediate_name)
            if scorpion_kpi:
                measurements_payload.append(create_measurement(scorpion_kpi, value, user_date))
                # Special case: 'Actions' KPI is also submitted as 'Pageviews' for some services
                if intermediate_name == 'Actions' and source_type in ['matomo_page_title', 'matomo_site_summary']:
                    measurements_payload.append(create_measurement('Pageviews', value, user_date))

        valid_measurements = [m for m in measurements_payload if m is not None]
        submit_measurements_to_scorpion(service_abbreviation, valid_measurements, is_live_run)

def check_env_vars():
    """Checks for required environment variables and exits if any are missing."""
    # SERPAPI_KEY is not strictly required if no publications are scraped
    required_vars = ["SCORPION_API_KEY", "MATOMO_AUTH_TOKEN"]
    missing_vars = [v for v in required_vars if not os.getenv(v)]
    if missing_vars:
        print("CRITICAL ERROR: The following required environment variables are not set:")
        for var in missing_vars: print(f"  - {var}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch service KPIs and submit them to the ScorPIoN API.")
    default_date = (datetime.now(timezone.utc) - relativedelta(months=1)).strftime('%Y-%m')
    
    parser.add_argument("--date", type=str, default=default_date, help=f"The date for the report in YYYY-MM format. Defaults to last month ({default_date}).")
    parser.add_argument("--live", action='store_true', help="Run in live submission mode. If not set, the script will perform a dry run and print curl commands.")
    parser.add_argument("--services", nargs='*', help="Specify one or more services to run by their display_name (e.g., 'Helixer' 'Trimmomatic'). If not provided, all services will be processed.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    
    args = parser.parse_args()
    
    check_env_vars()
    
    try:
        datetime.strptime(args.date, '%Y-%m')
        main(args.date, args.live, args.services)
    except ValueError:
        print("ERROR: Date format is incorrect. Please use YYYY-MM.")
