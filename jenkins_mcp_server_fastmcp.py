"""
Jenkins REST API MCP Server (FastMCP version)
Simpler, cleaner implementation using FastMCP
"""
import base64
import os
from fastmcp import FastMCP
import httpx

# Load environment variables
JENKINS_URL = os.getenv("JENKINS_URL", "")
JENKINS_USERNAME = os.getenv("JENKINS_USERNAME", "")
JENKINS_TOKEN = os.getenv("JENKINS_TOKEN", "")

# Create FastMCP server
mcp = FastMCP("Jenkins Test Harness")

def get_auth_header():
    """Create Basic Auth header for Jenkins"""
    credentials = f"{JENKINS_USERNAME}:{JENKINS_TOKEN}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return f"Basic {encoded}"

async def jenkins_request(path: str, method: str = "GET", data: dict = None) -> dict:
    """Make authenticated request to Jenkins"""
    url = f"{JENKINS_URL.rstrip('/')}/{path.lstrip('/')}"
    headers = {
        "Authorization": get_auth_header(),
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        if method == "GET":
            response = await client.get(url, headers=headers, follow_redirects=True)
        elif method == "POST":
            response = await client.post(url, headers=headers, json=data, follow_redirects=True)
        
        response.raise_for_status()
        
        try:
            return response.json()
        except:
            return {"text": response.text}

# Tool 1: Get Jenkins Status
@mcp.tool()
async def get_jenkins_status() -> str:
    """Get Jenkins server status and version information"""
    data = await jenkins_request("api/json")
    import json
    return json.dumps(data, indent=2)

# Tool 2: List Jobs
@mcp.tool()
async def list_jobs(folder: str = "") -> str:
    """
    List all Jenkins jobs with their status
    
    Args:
        folder: Optional folder path to list jobs from (e.g., 'MyFolder/SubFolder')
    """
    path = f"job/{folder}/api/json" if folder else "api/json?tree=jobs[name,url,color]"
    data = await jenkins_request(path)
    
    jobs = data.get("jobs", [])
    formatted = "\n".join([
        f"• {job['name']} - Status: {job.get('color', 'unknown')}"
        for job in jobs
    ])
    
    import json
    return f"Found {len(jobs)} jobs:\n\n{formatted}\n\nRaw data:\n{json.dumps(data, indent=2)}"

# Tool 3: Get Job Info
@mcp.tool()
async def get_job_info(job_name: str) -> str:
    """
    Get detailed information about a specific job

    Args:
        job_name: Name of the job (can include folder path like 'Folder/JobName')
    """
    # Handle folder paths correctly - replace '/' with '/job/'
    jenkins_path = job_name.replace('/', '/job/')
    data = await jenkins_request(f"job/{jenkins_path}/api/json")
    import json
    return json.dumps(data, indent=2)

# Tool 4: Get Build Info
@mcp.tool()
async def get_build_info(job_name: str, build_number: str) -> str:
    """
    Get information about a specific build

    Args:
        job_name: Name of the job
        build_number: Build number or 'lastBuild', 'lastSuccessfulBuild', 'lastFailedBuild'
    """
    # Handle folder paths correctly - replace '/' with '/job/'
    jenkins_path = job_name.replace('/', '/job/')
    data = await jenkins_request(f"job/{jenkins_path}/{build_number}/api/json")
    import json
    return json.dumps(data, indent=2)

# Tool 5: Get Console Output
@mcp.tool()
async def get_console_output(job_name: str, build_number: str) -> str:
    """
    Get console output/log for a specific build

    Args:
        job_name: Name of the job
        build_number: Build number or 'lastBuild'
    """
    # Handle folder paths correctly - replace '/' with '/job/'
    jenkins_path = job_name.replace('/', '/job/')
    data = await jenkins_request(f"job/{jenkins_path}/{build_number}/consoleText")
    
    text = data.get("text", "")
    # Limit console output to avoid overwhelming context
    if len(text) > 10000:
        text = text[:5000] + "\n\n... [truncated] ...\n\n" + text[-5000:]
    
    return text

# Tool 6: Trigger Build
@mcp.tool()
async def trigger_build(job_name: str, parameters: dict = None) -> str:
    """
    Trigger a new build for a job
    
    Args:
        job_name: Name of the job to build
        parameters: Optional build parameters as key-value pairs
    """
    # Handle folder paths correctly - replace '/' with '/job/'
    jenkins_path = job_name.replace('/', '/job/')
    if parameters:
        path = f"job/{jenkins_path}/buildWithParameters"
        await jenkins_request(path, method="POST", data=parameters)
    else:
        path = f"job/{jenkins_path}/build"
        await jenkins_request(path, method="POST")
    
    return f"Build triggered successfully for job: {job_name}"

# Tool 7: Get Queue Info
@mcp.tool()
async def get_queue_info() -> str:
    """Get information about the Jenkins build queue"""
    data = await jenkins_request("queue/api/json")
    
    items = data.get("items", [])
    if items:
        formatted = f"Build Queue ({len(items)} items):\n\n"
        for i, item in enumerate(items, 1):
            task = item.get("task", {})
            job_name = task.get("name", "Unknown")
            reason = item.get("why", "No reason provided")
            blocked = item.get("blocked", False)
            buildable = item.get("buildable", True)
            
            formatted += f"{i}. Job: {job_name}\n"
            formatted += f"   Status: {'Blocked' if blocked else 'Buildable' if buildable else 'Waiting'}\n"
            formatted += f"   Reason: {reason}\n\n"
        
        import json
        formatted += f"\nRaw data:\n{json.dumps(data, indent=2)}"
        return formatted
    else:
        import json
        return "Build Queue is empty\n\n" + json.dumps(data, indent=2)

# Tool 8: Get Node Info
@mcp.tool()
async def get_node_info(node_name: str = "") -> str:
    """
    Get information about Jenkins nodes/agents
    
    Args:
        node_name: Optional node name, leave empty for all nodes
    """
    if node_name:
        data = await jenkins_request(f"computer/{node_name}/api/json")
    else:
        data = await jenkins_request("computer/api/json")
    
    import json
    return json.dumps(data, indent=2)

if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
