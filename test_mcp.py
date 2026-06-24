import subprocess
import json
import time

def test_mcp():
    process = subprocess.Popen(
        ['npx', '-y', '@modelcontextprotocol/server-github'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

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
    
    process.stdin.write(json.dumps(init_req) + "\n")
    process.stdin.flush()
    
    time.sleep(1)
    
    # Read the initialization response
    init_res = process.stdout.readline()
    
    tools_req = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }
    process.stdin.write(json.dumps(tools_req) + "\n")
    process.stdin.flush()
    
    time.sleep(2)
    process.terminate()
    
    tools_res = process.stdout.readline()
    
    with open("mcp_tools.json", "w") as f:
        f.write(tools_res)

if __name__ == "__main__":
    test_mcp()
