import subprocess
import json
import logging
import os
import re

logger = logging.getLogger(__name__)

def parse_package_json(content):
    try:
        data = json.loads(content)
        return data.get("dependencies", {})
    except:
        return {}

def parse_requirements_txt(content):
    deps = {}
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "==" in line:
            pkg, ver = line.split("==", 1)
            deps[pkg.strip()] = ver.strip()
        elif ">=" in line:
            pkg, ver = line.split(">=", 1)
            deps[pkg.strip()] = ver.strip()
    return deps

def parse_go_mod(content):
    deps = {}
    in_require = False
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("require ("):
            in_require = True
            continue
        if line == ")" and in_require:
            in_require = False
            continue
            
        if line.startswith("require "):
            parts = line.split()
            if len(parts) >= 3:
                deps[parts[1]] = parts[2]
        elif in_require:
            parts = line.split()
            if len(parts) >= 2:
                deps[parts[0]] = parts[1]
    return deps

def fetch_single_file_stateless(owner, repo, path):
    try:
        env = os.environ.copy()
        
        init_req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "slack-bot", "version": "1.0"}
            }
        }
        
        tool_req = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "get_file_contents",
                "arguments": {
                    "owner": owner,
                    "repo": repo,
                    "path": path
                }
            }
        }
        
        full_input = json.dumps(init_req) + "\n" + json.dumps(tool_req) + "\n"
        
        process = subprocess.Popen(
            ['npx', '-y', '@modelcontextprotocol/server-github'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
        )
        
        stdout, stderr = process.communicate(input=full_input, timeout=10)
        
        for line in stdout.splitlines():
            try:
                response_data = json.loads(line)
                if response_data.get("id") == 2:
                    if "error" in response_data:
                        return None
                        
                    tool_result = response_data.get("result", {})
                    content_items = tool_result.get("content", [])
                    if not content_items:
                        return None
                        
                    file_content_str = content_items[0].get("text", "")
                    if not file_content_str:
                        return None
                        
                    github_response = json.loads(file_content_str)
                    return github_response.get("content", "")
            except json.JSONDecodeError:
                continue
                
        return None
    except Exception as e:
        logger.warning(f"Failed to read/parse {path}: {e}")
        return None

def get_repo_dependencies():
    """
    Connects to the official GitHub MCP server to dynamically read and parse
    dependencies from package.json, requirements.txt, and go.mod statelessly.
    """
    logger.info("Starting live stateless GitHub MCP Server connections...")
    
    owner = "bkd-dotcom"
    repo = "slack-zero-day-demo"
    
    all_deps = {
        "npm": {},
        "PyPI": {},
        "Go": {}
    }
    
    # 1. Fetch package.json
    logger.info("Fetching package.json...")
    pkg_content = fetch_single_file_stateless(owner, repo, "package.json")
    if pkg_content:
        all_deps["npm"] = parse_package_json(pkg_content)
        logger.info(f"Parsed {len(all_deps['npm'])} npm dependencies.")
        
    # 2. Fetch requirements.txt
    logger.info("Fetching requirements.txt...")
    req_content = fetch_single_file_stateless(owner, repo, "requirements.txt")
    if req_content:
        all_deps["PyPI"] = parse_requirements_txt(req_content)
        logger.info(f"Parsed {len(all_deps['PyPI'])} PyPI dependencies.")
        
    # 3. Fetch go.mod
    logger.info("Fetching go.mod...")
    go_content = fetch_single_file_stateless(owner, repo, "go.mod")
    if go_content:
        all_deps["Go"] = parse_go_mod(go_content)
        logger.info(f"Parsed {len(all_deps['Go'])} Go dependencies.")
            
    return all_deps
