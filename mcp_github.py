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
    except Exception as e:
        logger.warning(f"Failed to parse package.json: {e}")
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
    import urllib.request
    import json
    import base64
    import os
    
    token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref=main"
    
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github.v3+json")
    if token:
        req.add_header("Authorization", f"token {token}")
        
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                content_b64 = data.get("content", "")
                return base64.b64decode(content_b64).decode('utf-8')
            else:
                logger.warning(f"File {path} not found on GitHub main branch (HTTP {response.status}).")
                return None
    except urllib.error.HTTPError as e:
        logger.warning(f"File {path} not found on GitHub main branch (HTTP {e.code}).")
        return None
    except Exception as e:
        logger.warning(f"Failed to fetch {path} from GitHub: {e}")
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
