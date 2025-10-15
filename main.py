import sys
import os
import requests
import collections
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

def get_top_languages(top_n: int = 10, with_forks: bool = False) -> None:
    """
    Fetches all repositories for a user, aggregates language data,
    and prints the top N languages by percentage.

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

    # Step 1: Get all repositories (handles pagination)
    repos = []
    page = 1
    while True:
        print(f"Fetching repositories page {page}...")
        repos_url = f"{API_URL}/users/{USERNAME}/repos?per_page=100&page={page}"
        response = requests.get(repos_url, headers=headers)
        response.raise_for_status()  # Raises an exception for bad responses (4xx or 5xx)

        current_page_repos = response.json()
        if not current_page_repos:
            break # No more repos

        repos.extend(current_page_repos)
        page += 1

    fork_status = "including forks" if with_forks else "excluding forks"
    print(f"\nFound {len(repos)} repositories. Analyzing languages {fork_status}...")

    # Step 2: Aggregate language bytes from all repos
    total_language_bytes: Counter[str] = collections.Counter()
    for repo in repos:
        # Skip forked repos unless `with_forks` is True
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

    # Step 3: Calculate percentages and display the top N
    total_bytes = sum(total_language_bytes.values())

    print(f"\n--- Top {top_n} Languages Across All Repositories {fork_status.title()} ---")

    # Sort languages by byte count in descending order
    sorted_languages = total_language_bytes.most_common(top_n)

    for i, (language, byte_count) in enumerate(sorted_languages):
        percentage = (byte_count / total_bytes) * 100
        print(f"{i+1: >2}. {language: <15} {percentage: >6.2f}%")


def main():
    print(f"Hello from python version {sys.version_info.major}.{sys.version_info.minor}")


if __name__ == "__main__":
    main()
    # Example 1: Get top 10 languages, excluding forks (default behavior)
    print("--- Running with default settings (top 10, no forks) ---")
    get_top_languages()

    print("\n" + "="*60 + "\n")

    # Example 2: Get top 5 languages, including forked repos
    print("--- Running with custom settings (top 5, with forks) ---")
    get_top_languages(top_n=5, with_forks=True)
