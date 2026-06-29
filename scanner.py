import json
import urllib.request
import logging

logger = logging.getLogger(__name__)

def check_osv_vulnerabilities(package_name, ecosystem="npm"):
    """
    Queries the OSV.dev Real-Time Search API to find known vulnerabilities
    for a given package.
    """
    url = "https://api.osv.dev/v1/query"
    payload = {
        "package": {
            "name": package_name,
            "ecosystem": ecosystem
        }
    }
    
    try:
        req = urllib.request.Request(
            url, 
            data=json.dumps(payload).encode('utf-8'), 
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data.get("vulns", [])
    except Exception as e:
        logger.error(f"Error querying OSV API for {package_name}: {e}")
        return []
