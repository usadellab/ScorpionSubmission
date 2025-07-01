# ScorpionSubmission
Using APIs to get KPIs from Matomo and Google Scholar and submit them to Scorpion (de.NBI)

## Configuration and Requirements

This script relies on several external services to function. You must obtain your own API keys and set them as environment variables **before** running the script.

1.  **Matomo**
    * You need a valid `token_auth` from your Matomo instance. Set it as the `MATOMO_AUTH_TOKEN` environment variable.
    ```bash
    export MATOMO_AUTH_TOKEN="your_matomo_token_here"
    ```

2.  **ScorPIoN API**
    * You need a valid API key for the ScorPIoN instance you are submitting data to. Set it as the `SCORPION_API_KEY` environment variable.
    ```bash
    export SCORPION_API_KEY="your_scorpion_key_here"
    ```

3.  **SerpApi**
    * This script uses the SerpApi service to gather publication citation counts from Google Scholar.
    * You must register for an account (a free plan is available) at [serpapi.com](https://serpapi.com) to get your own API key. Set it as the `SERPAPI_KEY` environment variable.
    ```bash
    export SERPAPI_KEY="your_serpapi_key_here"
    ```

# Analytics Exporter for ScorPIoN API

This script automates the process of collecting and reporting key performance indicators (KPIs) for research software services. It functions as an ETL (Extract, Transform, Load) pipeline:

* **Extract:** It fetches web analytics data (visits, actions, etc.) from a Matomo instance and retrieves live publication citation counts from Google Scholar (via the SerpApi service).
* **Transform:** It processes this raw data into a standardized set of measurements.
* **Load:** It submits the final measurements to a ScorPIoN reporting API instance.

The script is designed to be secure and flexible, reading all secret keys from environment variables and providing command-line flags to control its behavior.

## Usage

The script defaults to a safe **dry run** mode, which prints the `curl` commands that would be used for submission without actually sending any data. To perform a live submission, you must explicitly use the `--live` flag.

### Example Commands

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
## Adding a New Service

To collect and report metrics for a new service, you only need to add a new entry to the `SERVICES_CONFIG` list at the top of the `your_script_name.py` script.

The script will automatically include any service defined in this list during its run.

### Service Configuration Structure

Each service is represented by a Python dictionary with four key-value pairs. You must provide the correct information for each key.

Here is the template to copy and paste into the `SERVICES_CONFIG` list:

```python
{
    "display_name": "Your Service's Common Name",
    "matomo_label": " The Exact Page Title from Matomo",
    "scorpion_service_name": "The Official Service Name in ScorPIoN",
    "publications": [
        "Full title of the first publication",
        "Full title of the second publication"
    ]
}
```
**How to Find the Correct Values**

* `display_name`: A simple, human-readable name for your service (e.g., `"My New Tool"`).

* `matomo_label`: The exact "Page Title" as it appears in your Matomo instance.

1. Log in to Matomo.

2. Go to the "Actions" > "Page Titles" report.

3. Find the entry for your service and copy the label exactly as it is written, including any leading or trailing spaces.

* `scorpion_service_name`: The official `name` of the service registered in the ScorPIoN database. You can find this by logging into the ScorPIoN UI or by querying its API. This name must be an exact match for the script to find the correct service abbreviation.

* `publications`: A list of the full, exact titles of the academic publications associated with your service. The script will search for each of these titles on Google Scholar to get citation counts.

**Complete Example**

Here is an example of adding a hypothetical service called "Bio-Analyzer":
```python
# In scorpion_submission.py

SERVICES_CONFIG = [
    {
        "display_name": "Helixer",
        "matomo_label": " Helixer structural gene annotation",
        "scorpion_service_name": "Helixer",
        "publications": [
            "Helixer: cross-species gene annotation of large eukaryotic genomes using deep learning",
            "Helixer-de novo Prediction of Primary Eukaryotic Gene Models Combining Deep Learning and a Hidden Markov Model"
        ]
    },
    {
        "display_name": "Mercator4",
        "matomo_label": " Mercator4 - plant protein functional annotation",
        "scorpion_service_name": "Mercator4 - Protein Function Mapping",
        "publications": [
            "Mercator: a fast and simple web server for genome scale functional annotation of plant sequence data"
        ]
    },
    # --- ADD YOUR NEW SERVICE HERE ---
    {
        "display_name": "Bio-Analyzer",
        "matomo_label": " Bio-Analyzer - Sequence Analysis Tool",
        "scorpion_service_name": "Bio-Analyzer",
        "publications": [
            "The Bio-Analyzer Toolkit: a novel method for sequence interpretation"
        ]
    }
    # ---------------------------------
]
```
Once you have added the new dictionary to the list and saved the file, the script will automatically include "Bio-Analyzer" on its next run.

## Disclaimer

This software is provided under the MIT License.

The use of third-party services, including but not limited to SerpApi, is governed by their respective Terms of Service. The author of this script is not responsible for how you use these services, and you are responsible for ensuring your use complies with their terms and any applicable laws.
