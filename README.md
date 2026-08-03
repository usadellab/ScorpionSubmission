<div><img src="ScorpionSubmissionLogo.png" alt="ScorpionSubmission" width="300"></div>

This script provides an automated Extract, Transform, Load (ETL) pipeline to gather Key Performance Indicators (KPIs) for various de.NBI / GHGA services and submit them to the ScorPIoN monitoring API.
It is designed to be flexible, fetching data from multiple sources to provide a holistic view of service performance.

# Features

* **Multi-Source Data Aggregation**: Collects metrics from various APIs and local files:
   * **Matomo**: Fetches user engagement metrics and specific download counts.
   * **Google Scholar**: Tracks academic impact by fetching publication citation counts.
   * **GitHub API**: Measures software adaptation by countil downloads for software releases.
   * **Local Filesystem**: Scans specified local directories to count tool executions (e.g., matching specific file extensions or directories) within the reporting month.
* **Handles Different Service Types**: The script can process services with full web analytics, entire websites, or standalone tools that only have download and citation metrics.
* **Configurable & Extensible**: Services are defined in a central `SERVICES_CONFIG` list, making it easy to add new services or modify existing ones.
* **Flexible Execution**:
   * Run the script for all services or specify a subset via the command line.
   * Supports both "dry run" mode (prints the API commands without executing them) and "live" mode (submits data to ScorPIoN).
   * Can backfill data for historical months.
* **Secure**: All API keys and authentication tokens are loaded from environment variables.

# Understanding Service Categories

The script is designed to handle four distinct categories of services, each with a different data source for its primary metrics.

**1. Web Applications (Page-Specific Analytics)**

These are services that exist as specific pages or sections within a larger Matomo-tracked website. Their usage is measured by filtering Matomo analytics for a specific page title or label.

* **KPIs**: `Unique Users`, `Visits`, `Pageviews`, `Visit Duration`, `Citations`.
* **Date Source**: Matomo (`Actions.getPageTitles`).
* **Example Services**: Helixer, Mercator4.
* **Script** `source_type`: `matomo_page_title`

**2. Multi-Page Services (Explicit URL List)**

These are services whose usage spans several distinct page URLs that do not share a common Matomo page title, folder, or filename pattern the script could group by automatically. The pages are listed explicitly in the config and their metrics are summed.

* **KPIs**: `Unique Users`, `Visits`, `Pageviews`, `Visit Duration`, `Citations`.
* **Data Source**: Matomo (`Actions.getPageUrl`, one request per configured page).
* **Example Services**: PlabiPD (PubPlant's pages use unrelated legacy names such as `pubplant_main.html` and `plant_genomes_pa.ep`, so they cannot be matched by a single title or prefix).
* **Script** `source_type`: `matomo_page_url_list`

**3. Full-Site Services (Site-Wide Analytics)**

These are services that constitute an entire website. Instead of tracking a single page, the script gathers the overall analytics for the entire Matomo Site ID.

* **KPIs**: `Unique Users`, `Visits`, `Pageviews`, `Visit Duration`, `Citations`.
* **Data Source**: Matomo (`VisitsSummary.get`).
* **Script** `source_type`:`matomo_site_summary`

**4. Standalone Tools (API-driven KPIs)**

These are typically downloadable tools where usage is not measured by web traffic but by other means. The script measures their impact through publication citations and download counts retrieved from an external API.

* **KPIs**: `Downloads`, `Citations`.
* **Data Source**: An external API for downloads (e.g., GitHub, a specific Matomo download link, etc).
* **Example Services**: Trimmomatic (downloads from GitHub API), MapMan (downloads from a tracked Matomo URL).
* **Script** `source_type`:`github_release_downloads`,`matomo_download`.

**5. Optional KPIs (Executions)**

Any of the above service categories can additionally report an `Executions` KPI. This is useful for backend tools that generate output files or directories on a local server. The script can scan configured absolute paths to count these matching files/directories modified during the reporting month.

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

**Script-level configuration (top of `scorpion_submission.py`):**

* `MATOMO_BASE_URL`: The base URL of your Matomo installation. Defaults to `https://www.plabipd.de/analytics/`.
* `MATOMO_RESOLVE`: Optional DNS override for Matomo curl requests. Useful after a server migration where the public DNS record has not yet been updated to point to the new server. Set to a string in the format `"hostname:port:ip"` (passed directly to curl's `--resolve` flag), or `None` to use normal DNS resolution.

  Example (override DNS to reach the new server at `10.100.50.34` while DNS still points to the old IP):
  ```python
  MATOMO_RESOLVE = "www.plabipd.de:443:10.100.50.34"
  ```
  Once the DNS record is updated, set this back to `None`.

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

First, decide which of the four categories your new service falls into (see "Understanding Service Categories" above). This will determine the `source_type` and `source_details` you need to provide.

**Step 2: Update `SERVICES_CONFIG`**

Open the script and add a new dictionary entry to the `SERVICES_CONFIG` list using the appropriate template below.

**Template for Web Application**
```python
{
    "display_name": "MyWebService",
    "scorpion_service_name": "MyWebService - The Full Name in ScorPIoN",
    "publications": [
        {"title": "Title of the primary publication", "author_id": "...", "citation_id": "..."}
    ],
    "source_type": "matomo_page_title",
    "source_details": {"label": " Matomo Label for this Page"}
},
```

**Template for Multi-Page Service (Explicit URL List)**
```python
{
    "display_name": "MyMultiPageService",
    "scorpion_service_name": "MyMultiPageService - The Full Name in ScorPIoN",
    "publications": [
        {"title": "Title of the primary publication", "author_id": "...", "citation_id": "..."}
    ],
    "source_type": "matomo_page_url_list",
    "source_details": {
        "url_paths": [
            "/my_page_one.html",
            "/my_page_two.html"
        ]
    }
},
```
`url_paths` are the page paths as shown in Matomo's "Pages" report (Page URL column), including the leading slash. List every page belonging to the service; metrics are summed across all of them. Pages with no data for the reporting month are skipped with a warning rather than failing the whole service.

**Template for Full-Site Service**
```python
{
    "display_name": "MyWebsite",
    "scorpion_service_name": "MyWebsite - The Full Name in ScorPIoN",
    "publications": [
        {"title": "Title of the primary publication", "author_id": "...", "citation_id": "..."}
    ],
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
    "publications": [
        {"title": "Title of the primary publication", "author_id": "...", "citation_id": "..."}
    ],
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
    "publications": [
        {"title": "Title of the primary publication", "author_id": "...", "citation_id": "..."}
    ],
    "source_type": "matomo_download",
    "source_details": {"download_url": "https://example.com/path/to/tool.zip"}
},
```

A publication with no `author_id`/`citation_id` set is skipped for citation counting (a warning is printed), so a service can be added before its citation IDs are resolved.

**Step 2.5: Resolving `author_id` and `citation_id`**

Think of a Google Scholar author profile as that person's personal list of their papers.

* `author_id`: identifies the profile itself, i.e. which person's list. It is the `user=` value in a profile URL, e.g. `https://scholar.google.com/citations?user=RjKYuDIAAAAJ` has `author_id` `RjKYuDIAAAAJ`.
* `citation_id`: identifies one paper's position on that specific list. It is not an ID of the paper itself, so the same paper looked up via a different co-author's profile would have a different `citation_id`. Format is `<author_id>:<paper_hash>`, e.g. `RjKYuDIAAAAJ:g5m5HwL7SMYC`.

Both are needed together because the only reliable citation-count source found (`view_citation`, see below) requires "which list" and "which entry on that list".

Google Scholar has no official API and its free-text search is not reliable enough to identify a specific paper automatically: search ranking can return an unrelated paper as the top hit, and for heavily-cited papers Scholar's own index splits the citation graph across many duplicate entries. A paper's listing on its own author's profile page does not have this problem.

**How to find them, step by step (worked example: the Mercator publication)**

1. Search the web (a normal web search, not Google Scholar itself, so it isn't affected by Scholar's bot detection) for `"<Author Name>" google scholar profile`, using one of the publication's authors. For Mercator's author Björn Usadel, this finds `https://scholar.google.com/citations?user=RjKYuDIAAAAJ`. The `author_id` is `RjKYuDIAAAAJ`.

2. Fetch that author's publication list from SerpApi:
   ```
   https://serpapi.com/search.json?engine=google_scholar_author&author_id=RjKYuDIAAAAJ&api_key=<SERPAPI_KEY>
   ```
   The response has an `articles` list. If the author has more than 100 publications, repeat with `&start=100`, `&start=200`, etc. to page through all of them.

3. Find the target paper in `articles` by matching its title, and read its `citation_id` field:
   ```json
   {
     "title": "Mercator: a fast and simple web server for genome scale functional annotation of plant sequence data",
     "citation_id": "RjKYuDIAAAAJ:g5m5HwL7SMYC",
     ...
   }
   ```

4. Add both values to the publication entry in `SERVICES_CONFIG`:
   ```python
   {"title": "Mercator: a fast and simple web server for genome scale functional annotation of plant sequence data",
    "author_id": "RjKYuDIAAAAJ", "citation_id": "RjKYuDIAAAAJ:g5m5HwL7SMYC"}
   ```

5. Optional sanity check: query the identifiers directly and confirm the returned title matches the paper before trusting the count:
   ```
   https://serpapi.com/search.json?engine=google_scholar_author&view_op=view_citation&author_id=RjKYuDIAAAAJ&citation_id=RjKYuDIAAAAJ:g5m5HwL7SMYC&api_key=<SERPAPI_KEY>
   ```
   The response's `citation.title` should match, and `citation.total_citations.cited_by.total` is the count `get_scholar_citations()` will use.

If none of the paper's authors have a Google Scholar profile, citation tracking for that publication is not possible through this script.

**Step 3: Confirm the ScorPIoN Service Name**

Ensure the value for `"scorpion_service_name"` is an **exact match** for the service's `name` field in the ScorPIoN API. An incorrect name will cause the script to skip the service.

**Step 4: Adding Local Executions (Optional)**

If your service generates local files or directories per execution, you can configure the script to count them and submit them as an `Executions` KPI. Add the `executions_local_sources` list to your service configuration:

```python
{
    # ... other service configurations ...
    "executions_local_sources": [
        {"path": "/absolute/path/to/jobs", "type": "directory", "pattern": ""},
        {"path": "/absolute/path/to/outputs", "type": "file", "pattern": ".zip"}
    ]
}
```
* `path`: The absolute path to the directory containing execution outputs.
* `type`: Either `"file"` or `"directory"`.
* `pattern`: A string the file/directory name must end with (e.g., `".zip"`, `"_fasta.zip"`). Leave empty (`""`) to match all.

## Disclaimer

This software is provided under the MIT License.

The use of third-party services, including but not limited to SerpApi, is governed by their respective Terms of Service. The author of this script is not responsible for how you use these services, and you are responsible for ensuring your use complies with their terms and any applicable laws.
