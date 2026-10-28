import os
import sys
from pathlib import Path
import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

load_dotenv(PROJECT_ROOT / ".env", override=True)

import mcp_server

SYSTEM_PROMPT = (
    "You are LinkPlus, an intelligent LinkedIn network assistant. "
    "Use the provided tools to search Connections.csv, analyze network stats, and compare connections. "
    "When asked to compare connections or provide profile details/bios, organize the info across:\n"
    "1. Tagline (Headline)\n"
    "2. Bio (About / Summary)\n"
    "3. Skills\n"
    "4. Education\n"
    "5. Experience\n"
    "Present both a side-by-side Markdown comparison table and a category-by-category breakdown. "
    "If public web search snippets are sparse for well-known leaders in the CSV, supplement with accurate background context while noting what came from the CSV."
)

TOOLS_SPEC = [
    {
        "functionDeclarations": [
            {
                "name": "search_connections",
                "description": "Search exported Connections.csv by name, company, or job title.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "query": {"type": "STRING"},
                        "company": {"type": "STRING"},
                        "position": {"type": "STRING"},
                        "limit": {"type": "INTEGER"},
                    },
                },
            },
            {
                "name": "get_network_stats",
                "description": "Get summary statistics of your Connections.csv network.",
                "parameters": {"type": "OBJECT", "properties": {}},
            },
            {
                "name": "get_profile_details",
                "description": "Fetch profile details for a single connection LinkedIn URL.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "linkedin_url": {"type": "STRING"},
                        "person_name": {"type": "STRING"},
                        "company": {"type": "STRING"},
                    },
                    "required": ["linkedin_url"],
                },
            },
            {
                "name": "compare_connections",
                "description": "Enrich and compare connections from Connections.csv across Tagline, Bio, Skills, Education, and Experience.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "company": {"type": "STRING"},
                        "position": {"type": "STRING"},
                        "query": {"type": "STRING"},
                        "limit": {"type": "INTEGER"},
                    },
                },
            },
        ]
    }
]

def execute_tool(name: str, args: dict):
    args = dict(args or {})
    if name == "search_connections":
        return mcp_server.search_connections(**args)
    if name == "get_network_stats":
        return mcp_server.get_network_stats()
    if name == "get_profile_details":
        args["allow_web_search"] = True
        return mcp_server.get_profile_details(**args)
    if name == "compare_connections":
        args["allow_web_search"] = True
        return mcp_server.compare_connections(**args)
    return {"error": f"Unknown tool: {name}"}

def build_endpoint(api_key: str, model: str) -> str:
    if api_key.startswith("AQ."):
        return f"https://aiplatform.googleapis.com/v1beta1/publishers/google/models/{model}:generateContent?key={api_key}"
    return f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

def call_gemini(api_key: str, contents: list) -> dict:
    models_to_try = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
    last_err = ""
    for model in models_to_try:
        url = build_endpoint(api_key, model)
        payload = {
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": contents,
            "tools": TOOLS_SPEC,
        }
        resp = requests.post(url, json=payload, timeout=60)
        if resp.status_code == 200:
            return resp.json()
        last_err = f"({resp.status_code} on {model}): {resp.text}"
        if resp.status_code not in (404, 400):
            break
    raise RuntimeError(f"Gemini API request failed {last_err}")

def run_turn(api_key: str, user_input: str) -> str:
    contents = [{"role": "user", "parts": [{"text": user_input}]}]
    for _ in range(5):
        data = call_gemini(api_key, contents)
        candidate = data.get("candidates", [{}])[0]
        content = candidate.get("content", {})
        parts = content.get("parts", [])
        if not parts:
            return "No response received from Gemini."

        fn_calls = [p["functionCall"] for p in parts if "functionCall" in p]
        if not fn_calls:
            text_parts = [p.get("text", "") for p in parts if "text" in p]
            return "\n".join(text_parts).strip()

        contents.append(content)
        fn_responses = []
        for fc in fn_calls:
            fn_name = fc["name"]
            fn_args = fc.get("args", {})
            print(f"  [Calling MCP Tool: {fn_name}({fn_args})]")
            result = execute_tool(fn_name, fn_args)
            fn_responses.append(
                {
                    "functionResponse": {
                        "name": fn_name,
                        "response": {"result": result},
                    }
                }
            )
        contents.append({"role": "user", "parts": fn_responses})

    return "Reached maximum tool call iterations."

def main():
    api_key = (os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key or api_key in ("your_openai_api_key_here", "your_gemini_api_key_here"):
        print("Error: Please set your GEMINI_API_KEY inside .env first!")
        return

    key_type = "Vertex AI Express (AQ.*)" if api_key.startswith("AQ.") else "Google AI Studio (AIza*)"
    print("\n========================================================")
    print(f"LinkPlus AI Agent is ready! [{key_type}]")
    print("Type your question below, or type 'exit' to quit.")
    print("========================================================")

    while True:
        user_input = input("\nYou: ").strip()
        if user_input.lower() in ("exit", "quit"):
            break
        if not user_input:
            continue

        try:
            answer = run_turn(api_key, user_input)
            print(f"\nLinkPlus:\n{answer}")
        except Exception as error:
            print(f"\nError: {error}")

if __name__ == "__main__":
    main()
