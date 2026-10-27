import os
import requests
import pandas as pd
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

mcp = FastMCP("LinkPlus-MCP")

CSV_PATH = os.getenv("CONNECTIONS_CSV_PATH", "./data/Connections.csv")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST", "fresh-linkedin-profile-data.p.rapidapi.com")

def _load_connections_df() -> pd.DataFrame:
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"Connections.csv not found at {CSV_PATH}")
    try:
        df = pd.read_csv(CSV_PATH, skiprows=3).fillna("")
        if "First Name" not in df.columns:
            df = pd.read_csv(CSV_PATH).fillna("")
    except Exception:
        df = pd.read_csv(CSV_PATH).fillna("")
    return df

@mcp.tool()
def search_connections(query: str = "", company: str = "", position: str = "", limit: int = 20) -> list:
    """Search exported Connections.csv by name, company, or job title."""
    df = _load_connections_df()
    if query:
        mask = (
            df["First Name"].str.contains(query, case=False, na=False) |
            df["Last Name"].str.contains(query, case=False, na=False) |
            df["Company"].str.contains(query, case=False, na=False) |
            df["Position"].str.contains(query, case=False, na=False)
        )
        df = df[mask]
    if company:
        df = df[df["Company"].str.contains(company, case=False, na=False)]
    if position:
        df = df[df["Position"].str.contains(position, case=False, na=False)]
    cols = [c for c in ["First Name", "Last Name", "URL", "Company", "Position", "Connected On"] if c in df.columns]
    return df[cols].head(limit).to_dict(orient="records")

@mcp.tool()
def get_network_stats() -> dict:
    """Get summary statistics of your Connections.csv network."""
    df = _load_connections_df()
    return {
        "total_connections": len(df),
        "top_companies": df[df["Company"] != ""]["Company"].value_counts().head(10).to_dict(),
        "top_positions": df[df["Position"] != ""]["Position"].value_counts().head(10).to_dict(),
    }

@mcp.tool()
def get_profile_details(linkedin_url: str) -> dict:
    """Fetch full profile details (bio, skills, experience, education) for a given profile URL."""
    if not RAPIDAPI_KEY:
        return {"error": "RAPIDAPI_KEY is missing in .env"}
    url = f"https://{RAPIDAPI_HOST}/get-linkedin-profile"
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST,
    }
    response = requests.get(url, headers=headers, params={"linkedin_url": linkedin_url, "include_skills": "true"}, timeout=20)
    if response.status_code != 200:
        return {"error": f"Status {response.status_code}: {response.text}"}
    data = response.json().get("data", {})
    return {
        "full_name": data.get("full_name"),
        "headline": data.get("headline"),
        "about": data.get("about"),
        "location": data.get("location"),
        "experiences": data.get("experiences", [])[:5],
        "educations": data.get("educations", []),
        "skills": data.get("skills", []),
        "profile_url": linkedin_url
    }

if __name__ == "__main__":
    mcp.run()
