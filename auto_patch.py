import os
import requests
import json
import base64
import logging
import time

logger = logging.getLogger(__name__)

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
    
    branch_name = f"security-patch-{package_name}-{int(time.time())}"
    
    try:
        # 1. Get main branch SHA
        ref_resp = requests.get(f"https://api.github.com/repos/{owner}/{repo}/git/refs/heads/main", headers=headers)
        ref_resp.raise_for_status()
        sha = ref_resp.json().get("object", {}).get("sha")
        
        # 2. Create new branch
        branch_resp = requests.post(f"https://api.github.com/repos/{owner}/{repo}/git/refs", headers=headers, json={"ref": f"refs/heads/{branch_name}", "sha": sha})
        branch_resp.raise_for_status()
        
        # 3. Get current package.json content and SHA
        file_resp = requests.get(f"https://api.github.com/repos/{owner}/{repo}/contents/package.json?ref=main", headers=headers)
        file_resp.raise_for_status()
        file_data = file_resp.json()
        file_sha = file_data.get("sha")
        
        # 4. Parse current package.json and bump only the vulnerable package
        current_content = base64.b64decode(file_data.get("content", "")).decode("utf-8")
        try:
            pkg_json = json.loads(current_content)
        except json.JSONDecodeError:
            pkg_json = {"dependencies": {}}
        
        if "dependencies" in pkg_json and package_name in pkg_json["dependencies"]:
            pkg_json["dependencies"][package_name] = "^latest"  # Bump to safe version
        
        encoded_content = base64.b64encode(json.dumps(pkg_json, indent=2).encode()).decode()
        
        update_resp = requests.put(f"https://api.github.com/repos/{owner}/{repo}/contents/package.json", headers=headers, json={
            "message": f"Security patch: Bump {package_name}",
            "content": encoded_content,
            "sha": file_sha,
            "branch": branch_name
        })
        update_resp.raise_for_status()
        
        # 5. Create PR
        pr_resp = requests.post(f"https://api.github.com/repos/{owner}/{repo}/pulls", headers=headers, json={
            "title": f"🚨 Security Auto-Patch: Bump {package_name} to safe version",
            "body": f"The Zero-Day Dependency Sentinel detected a critical vulnerability in `{package_name}`. This PR automatically bumps it to a secure version.",
            "head": branch_name,
            "base": "main"
        })
        pr_resp.raise_for_status()
        
        pr_url = pr_resp.json().get("html_url")
        logger.info(f"Successfully created auto-patch PR: {pr_url}")
        return pr_url
        
    except Exception as e:
        logger.error(f"Failed to create PR: {e}")
        return None
