"""
AIOS Agent Monitor API Server - Simple Version
"""

import http.server
import socketserver
import json
from pathlib import Path
import sys

PORT = 18792
AIOS_ROOT = Path(__file__).parent.parent
AGENT_DATA_FILE = AIOS_ROOT / "agent_system" / "data" / "agents.jsonl"


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/agents":
            self.send_response(200)
            self.send_header("Content-type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            agents = []
            total_tasks = 0
            active_count = 0
            archived_count = 0

            if AGENT_DATA_FILE.exists():
                with open(AGENT_DATA_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            agent = json.loads(line)
                            agents.append(agent)
                            total_tasks += agent["stats"]["tasks_completed"]
                            if agent["status"] == "active":
                                active_count += 1
                            elif agent["status"] == "archived":
                                archived_count += 1

            data = {
                "summary": {
                    "total_agents": len(agents),
                    "active": active_count,
                    "archived": archived_count,
                    "total_tasks_processed": total_tasks,
                },
                "agents": agents,
            }

            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

        elif self.path == "/" or self.path == "/monitor.html":
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()

            html_file = AIOS_ROOT / "agent_system" / "monitor.html"
            if html_file.exists():
                self.wfile.write(html_file.read_bytes())
            else:
                self.wfile.write(b"<h1>monitor.html not found</h1>")
        else:
            self.send_error(404)

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as httpd:
        print(f"Agent Monitor: http://127.0.0.1:{PORT}/")
        sys.stdout.flush()
        httpd.serve_forever()
