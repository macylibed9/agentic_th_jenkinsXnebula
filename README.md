# Intelligent Test Harness Agent

An AI agent that connects to Jenkins and NetBox via MCP (Model Context Protocol), enabling natural language queries across CI/CD pipelines and infrastructure.

## Architecture

```
claude_multi_agent.py          ← Main agent (Claude via Portkey/ADI Hub)
├── jenkins_mcp_server_fastmcp.py  ← Jenkins REST API tools
└── netbox_mcp_server.py           ← NetBox DCIM/IPAM tools
```

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure credentials:**
   ```bash
   copy .env.example .env
   ```

   Edit `.env`:
   ```
   # Portkey / ADI Hub
   PORTKEY_API_KEY=your_portkey_api_key

   # Jenkins
   JENKINS_URL=http://your-jenkins-host/jenkins
   JENKINS_USERNAME=your_username
   JENKINS_TOKEN=your_jenkins_api_token

   # NetBox
   NETBOX_URL=http://your-netbox-host/netbox
   NETBOX_TOKEN=your_netbox_api_token
   ```

3. **Run the agent:**
   ```bash
   python claude_multi_agent.py
   ```

## Example Queries

**Jenkins:**
- `List all failing jobs`
- `Show console output of the last failed build for job X`
- `What's in the build queue?`

**NetBox:**
- `List all active devices at site dc-manila`
- `What VLANs are configured at site hq?`
- `Show IP addresses in the 10.0.0.0/24 prefix`

**Cross-system:**
- `What is the IP of the server running job X?`
- `Which devices at site dc-manila have failed builds?`

## Available Tools

### Jenkins (`jenkins_mcp_server_fastmcp.py`)
- `get_jenkins_status` — Server status and version
- `list_jobs` — All jobs with last build status
- `get_job_details` — Details for a specific job
- `get_build_info` — Build details and result
- `get_console_output` — Build console logs (truncated to 10KB)
- `trigger_build` — Trigger a job build
- `get_queue` — Current build queue
- `get_computers` — Nodes and agents

### NetBox (`netbox_mcp_server.py`)
- `list_devices` — Devices with filters (site, role, status)
- `get_device` — Full details for a specific device
- `list_device_interfaces` — Interfaces for a device
- `list_sites` — All sites
- `list_racks` — Racks by site
- `list_ip_addresses` — IPAM addresses with filters
- `list_prefixes` — IP prefixes/subnets
- `list_vlans` — VLANs by site or group
- `list_virtual_machines` — VMs by cluster or site
- `list_cables` — Physical cable connections
- `list_tenants` — Tenants
- `search_netbox` — Global search across all objects

## Troubleshooting

**403 NetBox error** — Token lacks permissions. Verify in NetBox → Admin → API Tokens that the token is active and its user has read access to DCIM/IPAM.

**401 Jenkins error** — Regenerate your API token: Jenkins → Your Name → Configure → API Token.

**Rate limit (429)** — The agent automatically retries with exponential backoff (5s, 10s, 20s).

**Server not connecting** — Missing credentials in `.env` will skip that server gracefully; the agent runs with whichever servers are available.
