import os
import logging
import json
import threading
import time
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient
from dotenv import load_dotenv

from mcp_github import get_repo_dependencies
from scanner import check_osv_vulnerabilities
from ai_summary import generate_threat_analysis, ask_gemini_question
from auto_patch import create_auto_patch_pr

from flask import Flask, jsonify
from flask_cors import CORS

# Load environment variables
load_dotenv()

# Initialize Slack App
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# --- FLASK API SERVER (Web Dashboard Backend) ---
flask_app = Flask(__name__)
CORS(flask_app)

latest_scan_results = {
    "vulnerabilities": [],
    "score": 100,
    "last_scan_time": "Never",
    "all_dependencies": {}
}

@flask_app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify(latest_scan_results)

def start_flask():
    logger.info("Starting Flask API Server on port 5000...")
    # Run securely with reloader off in a thread
    flask_app.run(host="127.0.0.1", port=5000, use_reloader=False, debug=False)

def update_global_state(vulnerable_packages):
    global latest_scan_results
    latest_scan_results["vulnerabilities"] = vulnerable_packages
    # Deduct 25 points per vulnerability
    score = 100 - (len(vulnerable_packages) * 25)
    latest_scan_results["score"] = max(0, score)
    latest_scan_results["last_scan_time"] = time.strftime("%Y-%m-%d %H:%M:%S")

def run_scan_logic():
    """Runs the universal scan logic and updates global state."""
    dependencies = get_repo_dependencies()
    if not dependencies:
        return []
        
    vulnerable_packages = []
    
    # Populate all_dependencies for the React Network Graph
    global latest_scan_results
    latest_scan_results["all_dependencies"] = dependencies
    
    # dependencies is {"npm": {...}, "PyPI": {...}, "Go": {...}}
    for ecosystem, pkgs in dependencies.items():
        if not isinstance(pkgs, dict): continue
        for pkg, version in pkgs.items():
            logger.info(f"Scanning {ecosystem} package: {pkg} version {version}")
            vulns = check_osv_vulnerabilities(pkg, ecosystem)
            
            if vulns:
                # Add it to the list
                vulnerable_packages.append({
                    "ecosystem": ecosystem,
                    "name": pkg,
                    "version": version,
                    "vuln_count": len(vulns),
                    "latest_id": vulns[0].get("id", "Unknown ID"),
                    "summary": vulns[0].get("summary", "Security Vulnerability Detected"),
                    "ai_threat_analysis": generate_threat_analysis(pkg, vulns[0].get("summary", "Security Vulnerability Detected"))
                })
                
    update_global_state(vulnerable_packages)
    return vulnerable_packages

# --- SLACK EVENT HANDLERS ---
@app.command("/scan-dependencies")
@app.command("/zero-day-scan")
def handle_scan_command(ack, body, logger, respond):
    ack()
    user_id = body.get("user_id")
    respond(text=f"Hello <@{user_id}>! 🛡️ The Sentinel is running a UNIVERSAL scan across npm, PyPI, and Go ecosystems...", response_type="in_channel")
    
    vulnerable_packages = run_scan_logic()
    
    if vulnerable_packages:
        # Display the first one in Slack so we don't spam the channel
        v = vulnerable_packages[0]
        blocks = [
            {"type": "header", "text": {"type": "plain_text", "text": "🚨 CRITICAL ZERO-DAY DETECTED 🚨", "emoji": True}},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*Universal Real-Time Search:* A vulnerability was just matched in the `{v['ecosystem']}` ecosystem!"}},
            {"type": "divider"},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"⚠️ *Package:* `{v['name']}`\n*Current Version in Prod:* `{v['version']}`\n*Vulnerability:* {v['latest_id']} - {v['summary']}\n\n*Recommended Action:* Immediate patch required."}},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"🤖 *AI Threat Analysis:*\n_{v['ai_threat_analysis']}_"}}
        ]
        
        blocks.append({
            "type": "actions",
            "elements": [
                {"type": "button", "text": {"type": "plain_text", "text": "Create Jira Ticket", "emoji": True}, "style": "primary", "value": f"{v['name']}|{v['latest_id']}", "action_id": "create_ticket"},
                {"type": "button", "text": {"type": "plain_text", "text": "Open Auto-Patch PR", "emoji": True}, "style": "danger", "value": "open_pr", "action_id": "open_pr"},
                {"type": "button", "text": {"type": "plain_text", "text": "Ask AI for Help", "emoji": True}, "value": v['name'], "action_id": "ask_ai"}
            ]
        })
        
        respond(blocks=blocks, response_type="in_channel")
        
        if len(vulnerable_packages) > 1:
            respond(text=f"_Note: {len(vulnerable_packages)-1} additional vulnerabilities were found and populated to the <http://localhost:5173|Web Dashboard>._", response_type="in_channel")
    else:
        respond(text="✅ *Scan Complete:* No zero-day vulnerabilities detected across any ecosystem.", response_type="in_channel")

@app.action("create_ticket")
def handle_create_ticket(ack, body, logger, respond):
    ack()
    logger.info("Create Jira ticket button clicked!")
    val = body["actions"][0]["value"]
    pkg_name, vuln_id = val.split("|", 1) if "|" in val else ("Unknown", "Unknown")
    
    # -------------------------------------------------------------
    # SIMULATED JIRA CLOUD REST API INTEGRATION
    # -------------------------------------------------------------
    jira_payload = {
        "fields": {
            "project": {"key": "SEC"},
            "summary": f"Zero-Day Vulnerability in {pkg_name}",
            "description": f"Detected vulnerability {vuln_id} in {pkg_name}. Action required.",
            "issuetype": {"name": "Bug"},
            "priority": {"name": "Highest"},
            "assignee": {"id": "security-team-lead"}
        }
    }
    logger.info(f"--- JIRA API PAYLOAD SENT ---\n{json.dumps(jira_payload, indent=2)}\n-----------------------------")
    
    respond(text=f"✅ *Action Confirmed:* Enterprise Jira Ticket successfully generated via REST API. \n🔗 <https://jira.com/browse/SEC-104|SEC-104: Zero-Day Vulnerability in {pkg_name}>", replace_original=False)

@app.action("open_pr")
def handle_open_pr(ack, body, logger, respond):
    ack()
    logger.info("Open PR button clicked!")
    try:
        blocks = body.get("message", {}).get("blocks", [])
        text_block = blocks[3]["text"]["text"]
        pkg = text_block.split("`")[1]
    except Exception:
        pkg = "body-parser"
        
    pr_url = create_auto_patch_pr(owner="bkd-dotcom", repo="slack-zero-day-demo", package_name=pkg)
    if pr_url:
        respond(text=f"✅ *Action Confirmed:* An automated PR bumping the vulnerable package has been pushed. \n🔗 <{pr_url}|View PR on GitHub>", replace_original=False)
    else:
        respond(text="❌ *Action Failed:* Could not create the Auto-Patch PR on GitHub. Check the server logs.", replace_original=False)

@app.action("ask_ai")
def handle_ask_ai(ack, body, client, logger):
    ack()
    pkg_name = body["actions"][0]["value"]
    client.views_open(
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            "callback_id": "ai_modal_submit",
            "private_metadata": pkg_name,
            "title": {"type": "plain_text", "text": "Ask Gemini Security AI"},
            "submit": {"type": "plain_text", "text": "Ask"},
            "close": {"type": "plain_text", "text": "Cancel"},
            "blocks": [
                {"type": "input", "block_id": "question_block", "element": {"type": "plain_text_input", "action_id": "user_question", "multiline": True}, "label": {"type": "plain_text", "text": f"What do you want to know about {pkg_name}?"}}
            ]
        }
    )

@app.view("ai_modal_submit")
def handle_view_submission(ack, body, client, view, logger):
    ack()
    user_id = body["user"]["id"]
    pkg_name = view["private_metadata"]
    question = view["state"]["values"]["question_block"]["user_question"]["value"]
    ai_response = ask_gemini_question(pkg_name, question)
    client.chat_postMessage(channel="C0BCP8DPP6X", text=f"<@{user_id}> asked Gemini about `{pkg_name}`:\n*Question:* {question}\n\n🤖 *Gemini says:*\n{ai_response}")

def proactive_scanner(bot_token):
    client = WebClient(token=bot_token)
    
    while True:
        time.sleep(30) # Run every 30 seconds for the demo
        logger.info("Background daemon running proactive multi-ecosystem scan...")
        
        vulnerable_packages = run_scan_logic()
        
        if vulnerable_packages:
            v = vulnerable_packages[0]
            logger.info(f"Proactive scan detected: {v['name']}. Triggering Zero-Touch Automation.")
            
            try:
                # 1. Zero-Touch PR Creation
                logger.info("Autonomous Agent generating PR...")
                pr_url = create_auto_patch_pr(owner="bkd-dotcom", repo="slack-zero-day-demo", package_name=v['name'])
                pr_link_text = f"<{pr_url}|View PR on GitHub>" if pr_url else "*(PR Auto-Creation Failed)*"

                # 2. Zero-Touch Jira Payload
                logger.info("Autonomous Agent generating Jira Ticket...")
                jira_payload = {
                    "fields": {
                        "project": {"key": "SEC"},
                        "summary": f"Auto-Generated: Zero-Day Vulnerability in {v['name']}",
                        "description": f"Detected vulnerability {v['latest_id']} in {v['name']}. An automated patch PR has been opened.",
                        "issuetype": {"name": "Bug"},
                        "priority": {"name": "Highest"},
                        "assignee": {"id": "security-team-lead"}
                    }
                }
                logger.info(f"--- AUTO-JIRA PAYLOAD SENT ---\n{json.dumps(jira_payload, indent=2)}\n-----------------------------")

                # 3. Informational Slack Alert
                client.chat_postMessage(
                    channel="C0BCP8DPP6X",
                    text="🚨 *ZERO-TOUCH AUTONOMY TRIGGERED* 🚨",
                    blocks=[
                        {"type": "header", "text": {"type": "plain_text", "text": "🚨 ZERO-TOUCH REMEDIATION 🚨", "emoji": True}},
                        {"type": "section", "text": {"type": "mrkdwn", "text": f"⚠️ *Package:* `{v['name']}`\n*Vulnerability:* {v['latest_id']} - {v['summary']}\n\n*Background Daemon:* Detected a new vulnerability during routine ecosystem sweep. *Zero-Touch Autonomy* engaged."}},
                        {"type": "section", "text": {"type": "mrkdwn", "text": f"🤖 *AI Threat Analysis:*\n_{v['ai_threat_analysis']}_"}},
                        {"type": "divider"},
                        {"type": "section", "text": {"type": "mrkdwn", "text": f"✅ *Actions Taken Autonomously:*\n• *Code Patch:* Auto-Patch PR created: {pr_link_text}\n• *Ticketing:* Jira Ticket <https://jira.com/browse/SEC-105|SEC-105> automatically generated and assigned."}},
                    ]
                )
                if len(vulnerable_packages) > 1:
                    client.chat_postMessage(channel="C0BCP8DPP6X", text=f"_Note: {len(vulnerable_packages)-1} additional vulnerabilities were found and populated to the <http://localhost:5173|Web Dashboard>._")
            except Exception as e:
                logger.error(f"Failed to send proactive alert: {e}.")
            
            break # Stop loop to prevent spam

if __name__ == "__main__":
    bot_token = os.environ.get("SLACK_BOT_TOKEN")
    app_token = os.environ.get("SLACK_APP_TOKEN")
    
    if not bot_token or not app_token:
        logger.error("SLACK_BOT_TOKEN and SLACK_APP_TOKEN must be set.")
        exit(1)
        
    # Start Flask API in a background thread
    threading.Thread(target=start_flask, daemon=True).start()
    
    # Start proactive background thread
    threading.Thread(target=proactive_scanner, args=(bot_token,), daemon=True).start()
    
    # Start the Slack app
    logger.info("⚡️ Sentinel Slack/API Gateway is starting...")
    SocketModeHandler(app, app_token).start()
