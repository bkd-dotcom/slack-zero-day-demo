import requests
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
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        
        vulns = data.get("vulns", [])
        return vulns
    except Exception as e:
        logger.error(f"Error querying OSV API for {package_name}: {e}")
        return []
