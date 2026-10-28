# 🔗 LinkPlus

**LinkPlus** is an AI-powered LinkedIn Network Assistant built with the **Model Context Protocol (MCP)** and **Google Gemini / OpenAI**. It transforms your exported LinkedIn `Connections.csv` into an interactive, searchable intelligence tool—allowing you to query your network, analyze statistics, enrich profiles, and compare connections side-by-side.

---

## ✨ Key Features

- 🔍 **Smart Connection Search (`search_connections`)**: Filter your LinkedIn connections by name, company, or job title (automatically handles LinkedIn's 3-line CSV export header).
- 📊 **Network Analytics (`get_network_stats`)**: Instantly see your total connections, top 10 companies, and top 10 job positions.
- 🌐 **Free Profile Enrichment (`get_profile_details`)**: Enriches connection profiles using free public web search (`duckduckgo-search`) or optional live RapidAPI lookup, with atomic local caching (`data/enriched_cache.json`).
- ⚖️ **5-Category Connection Comparison (`compare_connections`)**: Compare groups of connections side-by-side across:
  1. **Tagline (Headline)**
  2. **Bio (About / Summary)**
  3. **Skills**
  4. **Education**
  5. **Experience (Current & Past Roles)**
- 🤖 **Flexible AI Agent (`src/agent.py`)**: Supports free **Google AI Studio (`AIza...`)** keys, **Google Cloud Vertex AI Express (`AQ...`)** keys, and **OpenAI**.

---

## 📁 Project Structure

```text
linkplus/
├── data/
│   ├── Connections.csv          # Your exported LinkedIn connections (git-ignored for privacy)
│   └── enriched_cache.json      # Local cache for enriched profile lookups
├── src/
│   ├── mcp_server.py            # MCP Server exposing LinkedIn network tools
│   └── agent.py                 # Interactive CLI AI Agent connected to the MCP tools
├── .env                         # Your private API keys (git-ignored)
├── .env.example                 # Template for environment variables
├── .gitignore                   # Ignores .env, .venv, and private CSV data
├── requirements.txt             # Python dependencies
└── README.md                    # Project documentation
```

---

## 🚀 Getting Started (Step-by-Step Setup)

### 1. Clone the Repository
```powershell
git clone https://github.com/oajisnothere713/linkplus.git
cd linkplus
```

### 2. Create & Activate a Virtual Environment
**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```powershell
python -m pip install -r requirements.txt
```

### 4. Configure Environment Variables (`.env`)
Copy `.env.example` to a new file named `.env`:
```powershell
Copy-Item .env.example .env
```

Open `.env` and add your **Gemini API Key** (from [Google AI Studio](https://aistudio.google.com/apikey) or Vertex AI Studio):
```env
GEMINI_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
RAPIDAPI_KEY=
RAPIDAPI_HOST=fresh-linkedin-profile-data.p.rapidapi.com
CONNECTIONS_CSV_PATH=./data/Connections.csv
```
> **Note:** `RAPIDAPI_KEY` is optional. When left blank, LinkPlus automatically uses free DuckDuckGo web search enrichment.

---

## 📂 Adding Your `Connections.csv` File

Place your exported LinkedIn connections file inside the `data/` folder:
```text
data/Connections.csv
```

### How to Export `Connections.csv` from LinkedIn:
1. Go to LinkedIn **Settings & Privacy** → **Data privacy**.
2. Click **Get a copy of your data**.
3. Select **Connections** and request the archive.
4. Once LinkedIn emails your download link, extract `Connections.csv` and place it inside `data/Connections.csv`.

### Sample `data/Connections.csv` Format (For Testing):
If you are waiting for LinkedIn's export email, you can create `data/Connections.csv` with this sample content:
```csv
Notes:
"When exporting your connection data, you may notice that some of the email addresses are missing."

First Name,Last Name,URL,Email Address,Company,Position,Connected On
Satya,Nadella,https://www.linkedin.com/in/satyanadella/,,Microsoft,Chairman and CEO,15 Jan 2026
Sundar,Pichai,https://www.linkedin.com/in/sundarpichai/,,Google,CEO,10 Feb 2026
Sam,Altman,https://www.linkedin.com/in/sam-altman/,,OpenAI,CEO,20 Mar 2026
Jensen,Huang,https://www.linkedin.com/in/jenhsunhuang/,,NVIDIA,Founder and CEO,05 Apr 2026
Aravind,Srinivas,https://www.linkedin.com/in/aravind-srinivas-16051987/,,Perplexity,CEO,12 May 2026
```

---

## 💻 Running the Project

Start the interactive AI Agent in your terminal:
```powershell
& ".\.venv\Scripts\python.exe" src\agent.py
```

Or run the standalone MCP Server directly (for use with Claude Desktop, Cursor, or MCP Inspector):
```powershell
& ".\.venv\Scripts\python.exe" src\mcp_server.py
```

---

## 💬 Example Prompts to Try

Once the agent is running (`You:`), try asking:

- **Network Overview:**
  > `"Give me summary statistics of my LinkedIn network and my top companies."`
- **Role & Company Search:**
  > `"Who do I know working at Microsoft, Google, or NVIDIA?"`
  > `"List all CEOs or Founders in my connections."`
- **5-Category Comparison:**
  > `"Compare all CEOs in my connections across Tagline, Bio, Skills, Education, and Experience."`
  > `"Compare my connections at Microsoft and Google in a table by Tagline, Bio, Skills, Education, and Experience."`

---
