import sys
import os
import requests
import collections
import json
from datetime import date
from typing import Counter, Dict, Any

# read the configuration from .env file
from dotenv import load_dotenv
load_dotenv()

# --- Configuration ---
# Your GitHub username
USERNAME = os.getenv("GITHUB_USER")

# The script will look for your GitHub token in an environment variable
# named GITHUB_TOKEN for security.
GITHUB_TOKEN = os.getenv("GITHUB_PAT")

# --- Constants ---
API_URL = "https://api.github.com"
CACHE_FILE = "repos_cache.json"

def get_top_languages(top_n: int = 10, with_forks: bool = False) -> None:
    """
    Fetches all repositories for a user, aggregates language data,
    and prints the top N languages by percentage. It caches the repository
    list for the current day to avoid redundant API calls.

    Args:
        top_n: The number of top languages to display. Defaults to 10.
        with_forks: If True, include forked repositories in the analysis. Defaults to False.
    """
    if not GITHUB_TOKEN:
        print("❌ Error: GITHUB_TOKEN environment variable not set.")
        print("Please create a token and set the environment variable.")
        return

    if USERNAME == "YOUR_GITHUB_USERNAME":
        print("✋ Please update the USERNAME variable in the script with your GitHub username.")
        return

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }

    repos: List[Dict[str, Any]] = []
    today_str = date.today().isoformat()

    # Step 1: Check for a valid cache first
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r') as f:
                cache_data = json.load(f)
                if cache_data.get("date") == today_str:
                    print(f"✅ Loading repositories from today's cache ({CACHE_FILE}).")
                    repos = cache_data["repos"]
    except (json.JSONDecodeError, KeyError):
        print("⚠️ Cache file is corrupted. Fetching from API.")
        repos = []


    # Step 2: If cache is invalid or missing, fetch from API
    if not repos:
        page = 1
        while True:
            print(f"Fetching repositories page {page} from GitHub API...")
            repos_url = f"{API_URL}/users/{USERNAME}/repos?per_page=100&page={page}"
            response = requests.get(repos_url, headers=headers)
            response.raise_for_status()

            current_page_repos = response.json()
            if not current_page_repos:
                break

            repos.extend(current_page_repos)
            page += 1

        # Save the freshly fetched data to the cache
        print(f"💾 Saving repository list to cache for today.")
        with open(CACHE_FILE, 'w') as f:
            cache_content = {"date": today_str, "repos": repos}
            json.dump(cache_content, f, indent=4)

    fork_status = "including forks" if with_forks else "excluding forks"
    print(f"\nFound {len(repos)} repositories. Analyzing languages {fork_status}...")

    # Step 3: Aggregate language bytes from all repos
    total_language_bytes: Counter[str] = collections.Counter()
    for repo in repos:
        if not with_forks and repo["fork"]:
            continue

        languages_url = repo["languages_url"]
        try:
            lang_response = requests.get(languages_url, headers=headers)
            lang_response.raise_for_status()
            languages_data: Dict[str, int] = lang_response.json()
            total_language_bytes.update(languages_data)
            print(f"  - Analyzed: {repo['name']}")
        except requests.exceptions.HTTPError as e:
            print(f"  - Could not fetch languages for {repo['name']}: {e}")

    if not total_language_bytes:
        print("\nNo language data found in your repositories.")
        return

    # Step 4: Calculate percentages and display the top N
    total_bytes = sum(total_language_bytes.values())

    print(f"\n--- Top {top_n} Languages Across All Repositories {fork_status.title()} ---")

    sorted_languages = total_language_bytes.most_common(top_n)

    for i, (language, byte_count) in enumerate(sorted_languages):
        percentage = (byte_count / total_bytes) * 100
        print(f"{i+1: >2}. {language: <15} {percentage: >6.2f}%")


def version():
    usage = """
    get_top_languages top_n: int = 10, with_forks: bool = False
    description:
    Fetches all github repositories for a user, aggregates language data,
    and prints the top N languages by percentage. It caches the repository
    list for the current day to avoid redundant API calls.
    """
    print(f"{usage}\n# using python version {sys.version_info.major}.{sys.version_info.minor}")


if __name__ == "__main__":
    version()
    # Example 1: Get top 10 languages, excluding forks (default behavior)
    print("--- Running with default settings (top 10, no forks) ---")
    get_top_languages()

    print("\n" + "="*60 + "\n")

    # Example 2: Get top 5 languages, including forked repos
    print("--- Running with custom settings (top 5, with forks) ---")
    get_top_languages(top_n=5, with_forks=True)
