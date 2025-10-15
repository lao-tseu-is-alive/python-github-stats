import sys
import os
import requests
import collections
import json
from datetime import date
from typing import Counter, Dict, Any, List

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
REPOS_CACHE_FILE = "repos_cache.json"
LANGUAGES_CACHE_FILE = "languages_cache.json"

def get_top_languages(top_n: int = 10, with_forks: bool = False, verbose: bool = False) -> None:
    """
    Fetches all repositories for a user, aggregates language data,
    and prints the top N languages by percentage. It caches both the
    repository list and the language data for the current day.

    Args:
        :param top_n: The number of top languages to display. Defaults to 10.
        :param with_forks: If True, include forked repositories in the analysis. Defaults to False.
        :param verbose: display more information
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

    # Step 1: Check for a valid repository cache
    try:
        if os.path.exists(REPOS_CACHE_FILE):
            with open(REPOS_CACHE_FILE, 'r') as f:
                cache_data = json.load(f)
                if cache_data.get("date") == today_str:
                    print(f"✅ Loading repositories from today's cache ({REPOS_CACHE_FILE}).")
                    repos = cache_data["repos"]
    except (json.JSONDecodeError, KeyError):
        print(f"⚠️ Repository cache file is corrupted. Fetching from API.")
        repos = []

    # Step 2: If repo cache is invalid or missing, fetch from API
    if not repos:
        page = 1
        while True:
            print(f"Fetching repositories page {page} from GitHub API...")
            repos_url = f"{API_URL}/users/{USERNAME}/repos?per_page=100&page={page}"
            response = requests.get(repos_url, headers=headers)
            response.raise_for_status()
            current_page_repos = response.json()
            if not current_page_repos: break
            repos.extend(current_page_repos)
            page += 1
        print(f"💾 Saving repository list to cache for today.")
        with open(REPOS_CACHE_FILE, 'w') as f:
            json.dump({"date": today_str, "repos": repos}, f, indent=4)

    # Step 3: Load language cache or initialize a new one
    languages_cache: Dict[str, Any] = {"date": today_str, "languages": {}}
    try:
        if os.path.exists(LANGUAGES_CACHE_FILE):
            with open(LANGUAGES_CACHE_FILE, 'r') as f:
                loaded_cache = json.load(f)
                if loaded_cache.get("date") == today_str:
                    print(f"✅ Loading languages from today's cache ({LANGUAGES_CACHE_FILE}).")
                    languages_cache = loaded_cache
    except (json.JSONDecodeError, KeyError):
        print(f"⚠️ Language cache file is corrupted. Rebuilding cache.")

    fork_status = "including forks" if with_forks else "excluding forks"
    print(f"\nFound {len(repos)} repositories. Analyzing languages {fork_status}...")

    # Step 4: Aggregate language bytes, using the cache
    total_language_bytes: Counter[str] = collections.Counter()
    cache_updated = False
    for repo in repos:
        if not with_forks and repo["fork"]:
            continue

        repo_full_name = repo["full_name"]

        # Check if language data for this repo is in the cache
        if repo_full_name in languages_cache["languages"]:
            languages_data = languages_cache["languages"][repo_full_name]
            if verbose:
                print(f"  - Loaded from cache: {repo['name']}")
        else:
            # Not in cache, fetch from API
            try:
                if verbose:
                    print(f"  - Fetching from API: {repo['name']}")
                lang_response = requests.get(repo["languages_url"], headers=headers)
                lang_response.raise_for_status()
                languages_data = lang_response.json()

                # Update the in-memory cache and mark it for saving
                languages_cache["languages"][repo_full_name] = languages_data
                cache_updated = True
            except requests.exceptions.HTTPError as e:
                print(f"  - Could not fetch languages for {repo['name']}: {e}")
                languages_data = {}

        total_language_bytes.update(languages_data)

    # Save the language cache back to file if it was updated
    if cache_updated:
        print(f"\n💾 Saving updated language data to cache.")
        with open(LANGUAGES_CACHE_FILE, 'w') as f:
            json.dump(languages_cache, f, indent=4)

    if not total_language_bytes:
        print("\nNo language data found in your repositories.")
        return

    # Step 5: Calculate percentages and display the top N
    total_bytes = sum(total_language_bytes.values())
    print(f"\n--- Top {top_n} Languages Across All Repositories {fork_status.title()} ---")

    sorted_languages = total_language_bytes.most_common(top_n)
    for i, (language, byte_count) in enumerate(sorted_languages):
        percentage = (byte_count / total_bytes) * 100
        print(f"{i+1: >2}. {language: <15} {percentage: >6.2f}%")

    # Step 5: Build and display the detailed table
    top_language_names = [lang for lang, count in sorted_languages]
    table_string = build_language_table(repos, languages_cache, top_language_names, with_forks)
    print("\n\n--- Detailed Language Breakdown (Bytes) ---")
    print(table_string)

def build_language_table(
        repos: List[Dict[str, Any]],
        languages_cache: Dict[str, Any],
        top_language_names: List[str],
        with_forks: bool
) -> str:
    """
    Builds a formatted string table of language usage per repository for the top languages.

    Args:
        repos: The list of repository dictionaries.
        languages_cache: The cache containing language data for each repo.
        top_language_names: A list of the names of the top N languages.
        with_forks: Boolean to correctly filter repositories.

    Returns:
        A formatted string representing the table.
    """
    header = ["Repository"] + top_language_names

    # Collect rows of data
    rows = []
    for repo in repos:
        if not with_forks and repo["fork"]:
            continue

        repo_name = repo["name"]
        repo_full_name = repo["full_name"]

        repo_langs = languages_cache["languages"].get(repo_full_name, {})

        row_data = [repo_name]
        for lang in top_language_names:
            bytes_count = repo_langs.get(lang, 0)
            row_data.append(str(bytes_count))

        rows.append(row_data)

    # Calculate column widths for alignment
    if not (rows and header):
        return "No data to display in table."

    col_widths = [len(h) for h in header]
    for row in rows:
        for i, cell in enumerate(row):
            if len(cell) > col_widths[i]:
                col_widths[i] = len(cell)

    # Build the formatted output string
    output_lines = []

    # Header
    header_line = " | ".join(header[i].ljust(col_widths[i]) for i in range(len(header)))
    output_lines.append(header_line)

    # Separator
    separator = "-+-".join("-" * width for width in col_widths)
    output_lines.append(separator)

    # Data rows
    for row in rows:
        data_line = " | ".join(row[i].ljust(col_widths[i]) for i in range(len(row)))
        output_lines.append(data_line)

    return "\n".join(output_lines)




def usage():
    usage_msg = """
    usage get_top_languages top_n: int = 5, with_forks: bool = False
        top_n: The number of top languages to display. Defaults to 5.
        with_forks: If True, include forked repositories in the analysis. Defaults to False.

    description:
    Fetches all github repositories for a user, aggregates language data,
    and prints the top N languages by percentage. It caches the repository
    list for the current day to avoid redundant API calls.
    """
    print(f"{usage_msg}\n# using python version {sys.version_info.major}.{sys.version_info.minor}")


if __name__ == "__main__":
    # retrieve first argument if any and store it in top_n
    if len(sys.argv) > 1:
        try:
            get_top_n = int(sys.argv[1])
        except ValueError:
            print(f"💥 expecting first argument to be an integer representing top_n, got {sys.argv[1]}")
            usage()
            sys.exit(1)
    else:
        get_top_n = 5
    # retrieve second argument if any and store it in with_forks
    if len(sys.argv) > 2:
        use_forks = sys.argv[2].lower() == "true"
    else:
        use_forks = False

    # Get top n languages, including forked repos if asked
    print("--- Running with custom settings (top 5, with forks) ---")
    get_top_languages(top_n=get_top_n, with_forks=use_forks)
