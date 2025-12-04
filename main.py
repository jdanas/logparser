import re
import json
from typing import Optional, Dict, Any
from dataclasses import dataclass
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax
from rich.panel import Panel

console = Console()

@dataclass
class LogEntry:
    timestamp: str
    environment: str
    level: str
    message: str
    raw: str

def parse_line(line: str) -> Optional[LogEntry]:
    # Regex to parse standard Laravel log format
    # [2025-12-04 06:53:18] local.INFO: Message...
    pattern = r"^\[(.*?)\] (\w+)\.(\w+): (.*)$"
    match = re.match(pattern, line)
    if match:
        return LogEntry(
            timestamp=match.group(1),
            environment=match.group(2),
            level=match.group(3),
            message=match.group(4),
            raw=line
        )
    return None

def extract_json(text: str) -> Optional[Dict[str, Any]]:
    """Attempts to find and parse JSON within a string."""
    # Look for something that looks like a JSON object starting after 'called ' or just find the first '{'
    try:
        start_index = text.find('{')
        if start_index == -1:
            return None
        
        # This is a naive extractor, it assumes the JSON goes to the end or brackets allow it.
        # For the specific example: ... called {"request": ...}
        json_str = text[start_index:]
        return json.loads(json_str)
    except json.JSONDecodeError:
        return None

def process_log_file(filename: str):
    console.print(f"[bold blue]Parsing {filename}...[/bold blue]\n")
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                entry = parse_line(line.strip())
                if not entry:
                    continue

                # Filter 1: LogDataController
                if "LogDataController@saveLogData" in entry.message:
                    console.print(f"[bold green]Found Asset Event:[/bold green] [{entry.timestamp}]")
                    json_data = extract_json(entry.message)
                    if json_data:
                        # The 'details' field inside 'request' is a stringified JSON, let's parse it for better display if possible
                        if "request" in json_data and "details" in json_data["request"]:
                            try:
                                details_parsed = json.loads(json_data["request"]["details"])
                                json_data["request"]["details"] = details_parsed
                            except:
                                pass # Keep as string if parsing fails
                        
                        console.print(Syntax(json.dumps(json_data, indent=2), "json", theme="monokai", background_color="default"))
                    else:
                        console.print(entry.message)
                    console.print("-" * 40)

                # Filter 2: SQL Errors
                elif "SQLSTATE" in entry.message:
                    console.print(f"[bold red]Found SQL Error:[/bold red] [{entry.timestamp}]")
                    # Highlight the error message
                    console.print(Panel(entry.message, title="SQL Exception", border_style="red"))
                    console.print("-" * 40)

    except FileNotFoundError:
        console.print(f"[bold red]Error:[/bold red] File {filename} not found.")

import sys

if __name__ == "__main__":
    log_file = sys.argv[1] if len(sys.argv) > 1 else "laravel.log"
    process_log_file(log_file)