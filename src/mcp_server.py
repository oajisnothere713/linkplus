"""LinkPlus: search a local LinkedIn connections export and enrich selected records.

Profile enrichment is limited to entries already present in the local CSV.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from dotenv import load_dotenv
from duckduckgo_search import DDGS
from mcp.server.mcpserver import MCPServer as FastMCP


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

mcp = FastMCP("LinkPlus-MCP")

CSV_PATH = Path(os.getenv("CONNECTIONS_CSV_PATH", "data/Connections.csv"))
if not CSV_PATH.is_absolute():
    CSV_PATH = PROJECT_ROOT / CSV_PATH

CACHE_PATH = Path(os.getenv("ENRICHMENT_CACHE_PATH", "data/enriched_cache.json"))
if not CACHE_PATH.is_absolute():
    CACHE_PATH = PROJECT_ROOT / CACHE_PATH

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "").strip()
RAPIDAPI_HOST = os.getenv(
    "RAPIDAPI_HOST", "fresh-linkedin-profile-data.p.rapidapi.com"
).strip()

_REQUIRED_COLUMNS = ("First Name", "Last Name")
_OPTIONAL_COLUMNS = ("URL", "Company", "Position", "Connected On")


def _load_connections_df() -> pd.DataFrame:
    """Read a standard LinkedIn connections export with or without note rows."""
    if not CSV_PATH.is_file():
        raise FileNotFoundError(f"Connections.csv not found at {CSV_PATH}")

    try:
        dataframe = pd.read_csv(CSV_PATH, skiprows=3).fillna("")
        if not set(_REQUIRED_COLUMNS).issubset(dataframe.columns):
            dataframe = pd.read_csv(CSV_PATH).fillna("")
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError):
        dataframe = pd.read_csv(CSV_PATH).fillna("")

    missing = [column for column in _REQUIRED_COLUMNS if column not in dataframe.columns]
    if missing:
        raise ValueError(
            "Connections.csv is missing required columns: " + ", ".join(missing)
        )
    for column in _OPTIONAL_COLUMNS:
        if column not in dataframe.columns:
            dataframe[column] = ""
    return dataframe


def _filter_connections(
    dataframe: pd.DataFrame, *, query: str = "", company: str = "", position: str = ""
) -> pd.DataFrame:
    """Filter with literal, case-insensitive matching rather than regex syntax."""
    if query:
        mask = (
            dataframe["First Name"].str.contains(query, case=False, na=False, regex=False)
            | dataframe["Last Name"].str.contains(query, case=False, na=False, regex=False)
            | dataframe["Company"].str.contains(query, case=False, na=False, regex=False)
            | dataframe["Position"].str.contains(query, case=False, na=False, regex=False)
        )
        dataframe = dataframe[mask]
    if company:
        dataframe = dataframe[
            dataframe["Company"].str.contains(company, case=False, na=False, regex=False)
        ]
    if position:
        dataframe = dataframe[
            dataframe["Position"].str.contains(position, case=False, na=False, regex=False)
        ]
    return dataframe


def _normalise_url(value: str) -> str:
    return value.strip().rstrip("/").casefold()


def _connection_for_url(linkedin_url: str) -> dict[str, str] | None:
    requested_url = _normalise_url(linkedin_url)
    if not requested_url:
        return None
    for record in _load_connections_df().to_dict(orient="records"):
        if _normalise_url(str(record.get("URL", ""))) == requested_url:
            return {
                column: str(record.get(column, ""))
                for column in _OPTIONAL_COLUMNS + _REQUIRED_COLUMNS
            }
    return None


def _load_cache() -> dict[str, dict[str, Any]]:
    if not CACHE_PATH.is_file():
        return {}
    try:
        with CACHE_PATH.open("r", encoding="utf-8") as source:
            cache = json.load(source)
        return cache if isinstance(cache, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_cache(cache: dict[str, dict[str, Any]]) -> None:
    """Atomically replace the local cache so interrupted writes do not corrupt it."""
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = CACHE_PATH.with_suffix(".tmp")
    with temporary_path.open("w", encoding="utf-8") as destination:
        json.dump(cache, destination, indent=2, ensure_ascii=False)
    temporary_path.replace(CACHE_PATH)


def _base_profile(record: dict[str, str]) -> dict[str, Any]:
    full_name = " ".join(
        part for part in (record.get("First Name", ""), record.get("Last Name", "")) if part
    )
    return {
        "full_name": full_name,
        "csv_company": record.get("Company", ""),
        "csv_position": record.get("Position", ""),
        "profile_url": record.get("URL", ""),
    }


def _as_list(value: Any) -> list[Any]:
    """Normalise optional provider fields before slicing or returning them."""
    return value if isinstance(value, list) else []


def _fetch_single_profile(
    record: dict[str, str], *, allow_web_search: bool = True
) -> dict[str, Any]:
    """Retrieve enrichment for one exported connection, returning useful errors."""
    profile = _base_profile(record)
    cache_key = _normalise_url(profile["profile_url"])
    if not cache_key:
        return {**profile, "error": "This connection has no profile URL in the CSV."}

    cache = _load_cache()
    cached_profile = cache.get(cache_key)
    if isinstance(cached_profile, dict):
        return {**cached_profile, "cached": True}

    if RAPIDAPI_KEY and RAPIDAPI_KEY != "your_rapidapi_key_here":
        try:
            response = requests.get(
                f"https://{RAPIDAPI_HOST}/get-linkedin-profile",
                headers={
                    "x-rapidapi-key": RAPIDAPI_KEY,
                    "x-rapidapi-host": RAPIDAPI_HOST,
                },
                params={"linkedin_url": profile["profile_url"], "include_skills": "true"},
                timeout=20,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as error:
            return {**profile, "source": "RapidAPI", "error": f"Profile lookup failed: {error}"}

        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        if not isinstance(data, dict):
            return {
                **profile,
                "source": "RapidAPI",
                "error": "Profile provider returned an unexpected response.",
            }

        result = {
            **profile,
            "source": "RapidAPI",
            "tagline": data.get("headline", ""),
            "bio": data.get("about", ""),
            "experiences": _as_list(data.get("experiences"))[:5],
            "educations": _as_list(data.get("educations")),
            "skills": _as_list(data.get("skills")),
        }
        cache[cache_key] = result
        _save_cache(cache)
        return result

    if not allow_web_search:
        return {
            **profile,
            "error": (
                "RAPIDAPI_KEY is not configured. Set allow_web_search=true to return "
                "public-web snippets instead, or configure an approved enrichment provider."
            ),
        }

    # This returns search-result snippets only; it does not visit or scrape profile pages.
    query = f'"{profile["full_name"]}" "{profile["csv_company"]}"'
    try:
        search_results = DDGS().text(query, max_results=4)
        snippets = [
            {
                "title": item.get("title", ""),
                "snippet": item.get("body", ""),
                "url": item.get("href", ""),
            }
            for item in search_results
        ]
    except Exception as error:  # The third-party client does not expose stable exception types.
        return {**profile, "source": "DuckDuckGo", "error": f"Web search failed: {error}"}

    result = {
        **profile,
        "source": "DuckDuckGo public search snippets",
        "web_enrichment_snippets": snippets,
    }
    cache[cache_key] = result
    _save_cache(cache)
    return result


@mcp.tool()
def search_connections(
    query: str = "", company: str = "", position: str = "", limit: int = 20
) -> list[dict[str, str]]:
    """Search the local Connections.csv by name, company, or job title."""
    limit = min(max(1, limit), 100)
    dataframe = _filter_connections(
        _load_connections_df(), query=query, company=company, position=position
    )
    columns = ["First Name", "Last Name", "URL", "Company", "Position", "Connected On"]
    return dataframe[columns].head(limit).to_dict(orient="records")


@mcp.tool()
def get_network_stats() -> dict[str, Any]:
    """Return basic statistics from the local Connections.csv export."""
    dataframe = _load_connections_df()
    return {
        "total_connections": len(dataframe),
        "top_companies": dataframe[dataframe["Company"] != ""]["Company"].value_counts().head(10).to_dict(),
        "top_positions": dataframe[dataframe["Position"] != ""]["Position"].value_counts().head(10).to_dict(),
    }


@mcp.tool()
def get_profile_details(linkedin_url: str, allow_web_search: bool = True) -> dict[str, Any]:
    """Enrich one URL that already exists in the local connections export."""
    record = _connection_for_url(linkedin_url)
    if record is None:
        return {"error": "The requested URL is not present in the local Connections.csv export."}
    return _fetch_single_profile(record, allow_web_search=allow_web_search)


@mcp.tool()
def compare_connections(
    company: str = "",
    position: str = "",
    query: str = "",
    limit: int = 5,
    allow_web_search: bool = True,
) -> list[dict[str, Any]]:
    """Enrich and compare up to 12 matching connections from the local CSV."""
    limit = min(max(1, limit), 12)
    dataframe = _filter_connections(
        _load_connections_df(), query=query, company=company, position=position
    )
    records = dataframe.head(limit).to_dict(orient="records")
    return [
        _fetch_single_profile(
            {
                column: str(record.get(column, ""))
                for column in _OPTIONAL_COLUMNS + _REQUIRED_COLUMNS
            },
            allow_web_search=allow_web_search,
        )
        for record in records
    ]


if __name__ == "__main__":
    mcp.run(transport="stdio")


