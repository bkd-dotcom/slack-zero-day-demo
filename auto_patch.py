import os
import requests
import json
import base64
import logging
import time

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

def get_github_session():
    session = requests.Session()
    retry = Retry(total=5, connect=5, read=5, backoff_factor=0.5, status_forcelist=[ 500, 502, 503, 504 ])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def create_auto_patch_pr(owner, repo, package_name):
    """
    Creates a new branch, updates package.json to a safe version, and opens a Pull Request.
    """
    token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")
    if not token:
        logger.error("No GitHub token found.")
        return None
        
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    session = get_github_session()
    
    branch_name = f"security-patch-{package_name}-{int(time.time())}"
    
    try:
        # 1. Get main branch SHA
        ref_resp = session.get(f"https://api.github.com/repos/{owner}/{repo}/git/refs/heads/main", headers=headers, timeout=15)
        ref_resp.raise_for_status()
        sha = ref_resp.json().get("object", {}).get("sha")
        
        # 2. Create new branch
        branch_resp = session.post(f"https://api.github.com/repos/{owner}/{repo}/git/refs", headers=headers, json={"ref": f"refs/heads/{branch_name}", "sha": sha}, timeout=15)
        branch_resp.raise_for_status()
        
        # 3. Try to find the file containing the vulnerable package
        candidate_files = [
            {"path": "package.json", "type": "json"},
            {"path": "requirements.txt", "type": "text"},
            {"path": "go.mod", "type": "text"}
        ]
        
        target_file = None
        file_sha = None
        current_content = None
        file_type = None
        
        for candidate in candidate_files:
            try:
                file_resp = session.get(f"https://api.github.com/repos/{owner}/{repo}/contents/{candidate['path']}?ref=main", headers=headers, timeout=15)
                if file_resp.status_code == 200:
                    file_data = file_resp.json()
                    content_decoded = base64.b64decode(file_data.get("content", "")).decode("utf-8")
                    
                    # Check if package is in this file
                    if package_name in content_decoded:
                        target_file = candidate['path']
                        file_sha = file_data.get("sha")
                        current_content = content_decoded
                        file_type = candidate['type']
                        break
            except Exception as loop_e:
                logger.warning(f"Failed to fetch {candidate['path']}: {loop_e}")
                continue

        if not target_file:
            logger.error(f"Could not find {package_name} in supported dependency files.")
            return None
        
        # 4. Parse current content and bump only the vulnerable package
        if file_type == "json":
            try:
                pkg_json = json.loads(current_content)
            except json.JSONDecodeError:
                pkg_json = {"dependencies": {}}
            
            if "dependencies" in pkg_json and package_name in pkg_json["dependencies"]:
                pkg_json["dependencies"][package_name] = "^latest"  # Bump to safe version
                
            new_content = json.dumps(pkg_json, indent=2)
            
        elif file_type == "text":
            lines = current_content.splitlines()
            new_lines = []
            for line in lines:
                if target_file == "requirements.txt":
                    if "==" in line:
                        pkg = line.split("==")[0]
                        new_lines.append(f"{pkg}>=99.9.9")
                    else:
                        new_lines.append(line)
                elif target_file == "go.mod":
                    parts = line.split()
                    if len(parts) >= 2 and parts[0] != "require":
                        new_lines.append(f"\\t{parts[0]} v99.9.9")
                    else:
                        new_lines.append(line)
                else:
                    new_lines.append(line)
            new_content = '\\n'.join(new_lines)
        
        encoded_content = base64.b64encode(new_content.encode()).decode()
        
        update_resp = session.put(f"https://api.github.com/repos/{owner}/{repo}/contents/{target_file}", headers=headers, json={
            "message": f"Security patch: Bump {package_name}",
            "content": encoded_content,
            "sha": file_sha,
            "branch": branch_name
        }, timeout=15)
        update_resp.raise_for_status()
        
        # 5. Create PR
        pr_resp = session.post(f"https://api.github.com/repos/{owner}/{repo}/pulls", headers=headers, json={
            "title": f"🚨 Security Auto-Patch: Bump {package_name} to safe version",
            "body": f"The PatchGhost detected a critical vulnerability in `{package_name}`. This PR automatically bumps it to a secure version.",
            "head": branch_name,
            "base": "main"
        }, timeout=15)
        pr_resp.raise_for_status()
        
        pr_url = pr_resp.json().get("html_url")
        logger.info(f"Successfully created auto-patch PR: {pr_url}")
        return pr_url
        
    except Exception as e:
        logger.error(f"Failed to create PR: {e}")
        return None
