<div><img src="ScorpionSubmissionLogo.png" alt="ScorpionSubmission" width="300"></div>

This script provides an automated Extract, Transform, Load (ETL) pipeline to gather Key Performance Indicators (KPIs) for various de.NBI / GHGA services and submit them to the ScorPIoN monitoring API.
It is designed to be flexible, fetching data from multiple sources to provide a holistic view of service performance.

# Features

* **Multi-Source Data Aggregation**: Collects metrics from various APIs:
   * **Matomo**: Fetches user engagement metrics and specific download counts.
   * **Google Scholar**: Tracks academic impact by fetching publication citation counts.
   * **GitHub API**: Measures software adaptation by countil downloads for software releases.
* **Handles Different Service Types**: The script can process services with full web analytics, entire websites, or standalone tools that only have download and citation metrics.
* **Configurable & Extensible**: Services are defined in a central `SERVICES_CONFIG` list, making it easy to add new services or modify existing ones.
* **Flexible Execution**:
   * Run the script for all services or specify a subset via the command line.
   * Supports both "dry run" mode (prints the API commands without executing them) and "live" mode (submits data to ScorPIoN).
   * Can backfill data for historical months.
* **Secure**: All API keys and authentication tokens are loaded from environment variables.

# Understanding Service Categories

The script is designed to handle three distinct categories of services, each with a different data source for its primary metrics.

**1. Web Applications (Page-Specific Analytics)**

These are services that exist as specific pages or sections within a larger Matomo-tracked website. Their usage is measured by filtering Matomo analytics for a specific page title or label.

* **KPIs**: `Unique Users`, `Visits`, `Pageviews`, `Visit Duration`, `Citations`.
* **Date Source**: Matomo (`Actions.getPageTitles`).
* **Example Services**: Helixer, Mercator4.
* **Script** `source_type`: `matomo_page_title`

**2. Full-Site Services (Site-Wide Analytics)**

These are services that constitute an entire website. Instead of tracking a single page, the script gathers the overall analytics for the entire Matomo Site ID.

* **KPIs**: `Unique Users`, `Visits`, `Pageviews`, `Visit Duration`, `Citations`.
* **Data Source**: Matomo (`VisitsSummary.get`).
* **Example Services**: PlabiPD.
* **Script** `source_type`:`matomo_site_summary`

**3. Standalone Tools (API-driven KPIs)**

These are typically downloadable tools where usage is not measured by web traffic but by other means. The script measures their impact through publication citations and download counts retrieved from an external API.

* **KPIs**: `Downloads`, `Citations`.
* **Data Source**: An external API for downloads (e.g., GitHub, a specific Matomo download link, etc).
* **Example Services**: Trimmomatic (downloads from GitHub API), MapMan (downloads from a tracked Matomo URL).
* **Script** `source_type`:`github_release_downloads`,`matomo_download`.

# Setup

**1. Requirements**

The script is written in Python 3. You will need to install the following libraries. It is recommended to use a virtual environment.

```bash
pip install requests python-dateutil
```

**2. Environment Variables**

This script requires several API tokens to function. Create a file named `.env` in the project root or export these variables into your shell environment. For cron jobs, creating a `.env` file and sourcing it via a wrapper script is the recommended approach.

**Required:**

* `SCORPION_API_KEY`: Your API key for the ScorPIoN service. *Note*: Make sure that you register your services in your ScorPIoN instance prior to submission of KPIs using this script!
* `MATOMO_AUTH_TOKEN`: Your authentication token for the Matomo API.

**Optional (but needed for certain KPIs):**

* `SERPAPI_KEY`: An API key from https://serpapi.com/ to enable scraping of Google Scholar for citation counts.
* `GITHUB_TOKEN`: A GitHub Personal Access Token. Recommended to avoid hitting the GitHub API's anonymous access rate limits.

# Usage

The script is controlled via command-line arguments.

**Arguments**

* `--date YYYY-MM`: (Optional) The month to fetch data for. **Defaults to the previous month.**
* `--live`: (Optional) If present, the script will submit data to the ScorPIoN API. **If omitted, it runs in "dry run" mode.**
* `services <name1> <name2> ... <nameN>`: (Optional) A space-separated list of service "display names" to process. **If omitted, the script processes all services. *Note* The "display names" need to be the same as given as "abbreviation" in the registration process of the service.**

## Example Commands

**1. Perform a Dry Run for Last Month (Default Behavior)**

This is the safest command to run. It will fetch data for the most recently completed month and print the `curl` commands that would be used to submit it.

```bash
python scorpion_submission.py
```
**2. Perform a Dry Run for a Specific Historical Month**

This will activate Historical Mode. It will fetch usage data for October 2024 but will not scrape for live citation data.
```bash
python scorpion_submission.py --date 2024-10
```

**3. Perform a LIVE Submission for Last Month**

The --live flag enables submission mode. This command will fetch data for the most recently completed month and immediately attempt to post it to the ScorPIoN API.
```bash
python scorpion_submission.py --live
```

**4. Perform a LIVE Submission for a Specific Historical Month**

This combines both flags to submit historical data (without citations) to the ScorPIoN API.
```bash
python scorpion_submission.py --date 2024-10 --live
```

**5. Historical Dry Run for a Single Service**

```bash
python scorpion_submission.py --date 2024-05 --services Helixer
```

## Adding a New Service

To collect and report metrics for a new service, you only need to add a new entry to the `SERVICES_CONFIG` list at the top of the `your_script_name.py` script.

The script will automatically include any service defined in this list during its run.

### Service Configuration Structure

Adding a new service is a straightforward process of updating the `SERVICES_CONFIG` list in the script.

**Step 1:Determine the Service Category**

First, decide which of the three categories your new service falls into (see "Understanding Service Categories" above). This will determine the `source_type` and `source_details` you need to provide.

**Step 2: Update `SERVICES_CONFIG`**

Open the script and add a new dictionary entry to the `SERVICES_CONFIG` list using the appropriate template below.

**Template for Web Application**
```python
{
    "display_name": "MyWebService",
    "scorpion_service_name": "MyWebService - The Full Name in ScorPIoN",
    "publications": ["Title of the primary publication"],
    "source_type": "matomo_page_title",
    "source_details": {"label": " Matomo Label for this Page"}
},
```

**Template for Full-Site Service**
```python
{
    "display_name": "MyWebsite",
    "scorpion_service_name": "MyWebsite - The Full Name in ScorPIoN",
    "publications": ["Title of the primary publication"],
    "source_type": "matomo_site_summary",
    "source_details": {}
},
```

**Template for Standalone-Tool**
*For GitHub downloads:*
```python
{
    "display_name": "MyGitHubTool",
    "scorpion_service_name": "MyGitHubTool - The Full Name in ScorPIoN",
    "publications": ["Title of the primary publication"],
    "source_type": "github_release_downloads",
    "source_details": {
        "repo": "owner/repository_name",
        "tags": ["v1.2.3", "v4.5.6"]  # Optional: specify tags to count downloads for specific releases only
    }
},
```

*For a specific download URL tracked in Matomo*
```python
{
    "display_name": "MyDownloadedTool",
    "scorpion_service_name": "MyDownloadedTool - The Full Name in ScorPIoN",
    "publications": ["Title of the primary publication"],
    "source_type": "matomo_download",
    "source_details": {"download_url": "https://example.com/path/to/tool.zip"}
},
```

**Step 3: Confirm the ScorPIoN Service Name**

Ensure the value for `"scorpion_service_name"` is an **exact match** for the service's `name` field in the ScorPIoN API. An incorrect name will cause the script to skip the service.

## Disclaimer

This software is provided under the MIT License.

The use of third-party services, including but not limited to SerpApi, is governed by their respective Terms of Service. The author of this script is not responsible for how you use these services, and you are responsible for ensuring your use complies with their terms and any applicable laws.
