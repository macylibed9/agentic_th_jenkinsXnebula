"""
NetBox REST API MCP Server (FastMCP version)
Wraps NetBox REST API as an MCP server for Claude to query infrastructure data
"""
import json
import os
from fastmcp import FastMCP
import httpx

NETBOX_URL = os.getenv("NETBOX_URL", "")
NETBOX_TOKEN = os.getenv("NETBOX_TOKEN", "")

mcp = FastMCP("NetBox Agent")


def get_headers() -> dict:
    return {
        "Authorization": f"Token {NETBOX_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


async def netbox_get(path: str, params: dict = None) -> dict:
    """Make authenticated GET request to NetBox API"""
    url = f"{NETBOX_URL.rstrip('/')}/api/{path.lstrip('/')}"
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.get(url, headers=get_headers(), params=params or {}, follow_redirects=True)
        response.raise_for_status()
        return response.json()


def fmt(data: dict) -> str:
    return json.dumps(data, indent=2)


# ── Devices ──────────────────────────────────────────────────────────────────

@mcp.tool()
async def list_devices(
    site: str = "",
    role: str = "",
    status: str = "",
    manufacturer: str = "",
    device_type: str = "",
    name: str = "",
    limit: int = 50,
) -> str:
    """
    List devices from NetBox with optional filters.

    Args:
        site: Filter by site slug (e.g. 'dc-manila')
        role: Filter by device role slug (e.g. 'router', 'switch')
        status: Filter by status (active, planned, staged, failed, inventory, decommissioning)
        manufacturer: Filter by manufacturer slug
        device_type: Filter by device type slug
        name: Filter by device name (supports partial match)
        limit: Max results to return (default 50)
    """
    params = {"limit": limit}
    if site:
        params["site"] = site
    if role:
        params["role"] = role
    if status:
        params["status"] = status
    if manufacturer:
        params["manufacturer"] = manufacturer
    if device_type:
        params["device_type"] = device_type
    if name:
        params["name__icontains"] = name

    data = await netbox_get("dcim/devices/", params)
    results = data.get("results", [])
    count = data.get("count", 0)

    summary = f"Found {count} device(s) (showing {len(results)}):\n\n"
    for d in results:
        site_name = d.get("site", {}) or {}
        role_name = d.get("role", {}) or {}
        summary += (
            f"• {d['name']}\n"
            f"  Site: {site_name.get('name', 'N/A')}  |  "
            f"Role: {role_name.get('name', 'N/A')}  |  "
            f"Status: {d.get('status', {}).get('label', 'N/A')}  |  "
            f"IP: {(d.get('primary_ip') or {}).get('address', 'N/A')}\n"
        )
    return summary + "\nRaw data:\n" + fmt(data)


@mcp.tool()
async def get_device(device_name: str) -> str:
    """
    Get full details of a specific device by name.

    Args:
        device_name: Exact name of the device
    """
    data = await netbox_get("dcim/devices/", {"name": device_name})
    results = data.get("results", [])
    if not results:
        return f"No device found with name: {device_name}"
    return fmt(results[0])


@mcp.tool()
async def list_device_interfaces(device_name: str) -> str:
    """
    List all interfaces for a specific device.

    Args:
        device_name: Name of the device
    """
    data = await netbox_get("dcim/interfaces/", {"device": device_name, "limit": 100})
    results = data.get("results", [])
    count = data.get("count", 0)

    summary = f"Device '{device_name}' has {count} interface(s):\n\n"
    for iface in results:
        enabled = "UP" if iface.get("enabled") else "DOWN"
        summary += (
            f"• {iface['name']}  [{iface.get('type', {}).get('label', 'N/A')}]  "
            f"Status: {enabled}  "
            f"MAC: {iface.get('mac_address') or 'N/A'}\n"
        )
    return summary + "\nRaw data:\n" + fmt(data)


# ── Sites & Racks ─────────────────────────────────────────────────────────────

@mcp.tool()
async def list_sites(status: str = "", region: str = "") -> str:
    """
    List all sites in NetBox.

    Args:
        status: Filter by status (active, planned, retired)
        region: Filter by region slug
    """
    params: dict = {"limit": 100}
    if status:
        params["status"] = status
    if region:
        params["region"] = region

    data = await netbox_get("dcim/sites/", params)
    results = data.get("results", [])

    summary = f"Found {data.get('count', 0)} site(s):\n\n"
    for s in results:
        summary += (
            f"• {s['name']} (slug: {s['slug']})  "
            f"Status: {s.get('status', {}).get('label', 'N/A')}  "
            f"Region: {(s.get('region') or {}).get('name', 'N/A')}\n"
        )
    return summary + "\nRaw data:\n" + fmt(data)


@mcp.tool()
async def list_racks(site: str = "", status: str = "") -> str:
    """
    List racks, optionally filtered by site.

    Args:
        site: Filter by site slug
        status: Filter by status (active, planned, reserved, available, deprecated)
    """
    params: dict = {"limit": 100}
    if site:
        params["site"] = site
    if status:
        params["status"] = status

    data = await netbox_get("dcim/racks/", params)
    results = data.get("results", [])

    summary = f"Found {data.get('count', 0)} rack(s):\n\n"
    for r in results:
        summary += (
            f"• {r['name']}  "
            f"Site: {(r.get('site') or {}).get('name', 'N/A')}  "
            f"U Height: {r.get('u_height', 'N/A')}  "
            f"Status: {r.get('status', {}).get('label', 'N/A')}\n"
        )
    return summary + "\nRaw data:\n" + fmt(data)


# ── IPAM ──────────────────────────────────────────────────────────────────────

@mcp.tool()
async def list_ip_addresses(
    device: str = "",
    prefix: str = "",
    status: str = "",
    address: str = "",
    limit: int = 50,
) -> str:
    """
    List IP addresses from IPAM.

    Args:
        device: Filter by device name
        prefix: Filter by parent prefix (e.g. '192.168.1.0/24')
        status: Filter by status (active, reserved, deprecated, dhcp, slaac)
        address: Search by specific address or partial (e.g. '10.0.0')
        limit: Max results (default 50)
    """
    params: dict = {"limit": limit}
    if device:
        params["device"] = device
    if prefix:
        params["parent"] = prefix
    if status:
        params["status"] = status
    if address:
        params["address"] = address

    data = await netbox_get("ipam/ip-addresses/", params)
    results = data.get("results", [])

    summary = f"Found {data.get('count', 0)} IP address(es) (showing {len(results)}):\n\n"
    for ip in results:
        assigned = ip.get("assigned_object") or {}
        device_name = "unassigned"
        if assigned:
            device_obj = assigned.get("device") or {}
            device_name = device_obj.get("name", assigned.get("name", "N/A"))
        summary += (
            f"• {ip['address']}  "
            f"Status: {ip.get('status', {}).get('label', 'N/A')}  "
            f"DNS: {ip.get('dns_name') or 'N/A'}  "
            f"Assigned to: {device_name}\n"
        )
    return summary + "\nRaw data:\n" + fmt(data)


@mcp.tool()
async def list_prefixes(
    prefix: str = "",
    site: str = "",
    vrf: str = "",
    status: str = "",
    role: str = "",
    limit: int = 50,
) -> str:
    """
    List IP prefixes/subnets from IPAM.

    Args:
        prefix: Filter by prefix (e.g. '10.0.0.0/8')
        site: Filter by site slug
        vrf: Filter by VRF name
        status: Filter by status (active, container, reserved, deprecated)
        role: Filter by role slug
        limit: Max results (default 50)
    """
    params: dict = {"limit": limit}
    if prefix:
        params["prefix"] = prefix
    if site:
        params["site"] = site
    if vrf:
        params["vrf"] = vrf
    if status:
        params["status"] = status
    if role:
        params["role"] = role

    data = await netbox_get("ipam/prefixes/", params)
    results = data.get("results", [])

    summary = f"Found {data.get('count', 0)} prefix(es) (showing {len(results)}):\n\n"
    for p in results:
        summary += (
            f"• {p['prefix']}  "
            f"Status: {p.get('status', {}).get('label', 'N/A')}  "
            f"Site: {(p.get('site') or {}).get('name', 'N/A')}  "
            f"VRF: {(p.get('vrf') or {}).get('name', 'global')}  "
            f"Util: {p.get('utilization', 'N/A')}%\n"
        )
    return summary + "\nRaw data:\n" + fmt(data)


@mcp.tool()
async def list_vlans(
    site: str = "",
    group: str = "",
    role: str = "",
    vid: int = 0,
    limit: int = 50,
) -> str:
    """
    List VLANs from IPAM.

    Args:
        site: Filter by site slug
        group: Filter by VLAN group slug
        role: Filter by role slug
        vid: Filter by VLAN ID number
        limit: Max results (default 50)
    """
    params: dict = {"limit": limit}
    if site:
        params["site"] = site
    if group:
        params["group"] = group
    if role:
        params["role"] = role
    if vid:
        params["vid"] = vid

    data = await netbox_get("ipam/vlans/", params)
    results = data.get("results", [])

    summary = f"Found {data.get('count', 0)} VLAN(s) (showing {len(results)}):\n\n"
    for v in results:
        summary += (
            f"• VLAN {v['vid']} - {v['name']}  "
            f"Status: {v.get('status', {}).get('label', 'N/A')}  "
            f"Site: {(v.get('site') or {}).get('name', 'N/A')}\n"
        )
    return summary + "\nRaw data:\n" + fmt(data)


# ── Virtual Machines ──────────────────────────────────────────────────────────

@mcp.tool()
async def list_virtual_machines(
    site: str = "",
    cluster: str = "",
    status: str = "",
    name: str = "",
    limit: int = 50,
) -> str:
    """
    List virtual machines from NetBox.

    Args:
        site: Filter by site slug
        cluster: Filter by cluster name
        status: Filter by status (active, planned, staged, failed, decommissioning)
        name: Filter by VM name (partial match)
        limit: Max results (default 50)
    """
    params: dict = {"limit": limit}
    if site:
        params["site"] = site
    if cluster:
        params["cluster"] = cluster
    if status:
        params["status"] = status
    if name:
        params["name__icontains"] = name

    data = await netbox_get("virtualization/virtual-machines/", params)
    results = data.get("results", [])

    summary = f"Found {data.get('count', 0)} VM(s) (showing {len(results)}):\n\n"
    for vm in results:
        summary += (
            f"• {vm['name']}  "
            f"Status: {vm.get('status', {}).get('label', 'N/A')}  "
            f"Cluster: {(vm.get('cluster') or {}).get('name', 'N/A')}  "
            f"vCPUs: {vm.get('vcpus', 'N/A')}  "
            f"RAM: {vm.get('memory', 'N/A')} MB  "
            f"IP: {(vm.get('primary_ip') or {}).get('address', 'N/A')}\n"
        )
    return summary + "\nRaw data:\n" + fmt(data)


# ── Cables & Connections ──────────────────────────────────────────────────────

@mcp.tool()
async def list_cables(device: str = "", site: str = "", limit: int = 50) -> str:
    """
    List cables/connections in NetBox.

    Args:
        device: Filter cables connected to a specific device
        site: Filter by site slug
        limit: Max results (default 50)
    """
    params: dict = {"limit": limit}
    if site:
        params["site"] = site

    data = await netbox_get("dcim/cables/", params)
    results = data.get("results", [])

    summary = f"Found {data.get('count', 0)} cable(s) (showing {len(results)}):\n\n"
    for c in results:
        a_end = c.get("a_terminations", [{}])
        b_end = c.get("b_terminations", [{}])
        summary += (
            f"• Cable {c['id']}  "
            f"Type: {c.get('type', {}).get('label', 'N/A') if c.get('type') else 'N/A'}  "
            f"Status: {c.get('status', {}).get('label', 'N/A')}  "
            f"A: {a_end[0].get('object', {}).get('display', 'N/A') if a_end else 'N/A'}  "
            f"B: {b_end[0].get('object', {}).get('display', 'N/A') if b_end else 'N/A'}\n"
        )
    return summary + "\nRaw data:\n" + fmt(data)


# ── Tenants ───────────────────────────────────────────────────────────────────

@mcp.tool()
async def list_tenants(group: str = "") -> str:
    """
    List tenants in NetBox.

    Args:
        group: Filter by tenant group slug
    """
    params: dict = {"limit": 100}
    if group:
        params["group"] = group

    data = await netbox_get("tenancy/tenants/", params)
    results = data.get("results", [])

    summary = f"Found {data.get('count', 0)} tenant(s):\n\n"
    for t in results:
        summary += (
            f"• {t['name']} (slug: {t['slug']})  "
            f"Group: {(t.get('group') or {}).get('name', 'N/A')}\n"
        )
    return summary + "\nRaw data:\n" + fmt(data)


# ── Search ────────────────────────────────────────────────────────────────────

@mcp.tool()
async def search_netbox(query: str, limit: int = 20) -> str:
    """
    Search across all NetBox objects using the global search endpoint.

    Args:
        query: Search term (device name, IP, prefix, etc.)
        limit: Max results per object type (default 20)
    """
    data = await netbox_get("search/", {"q": query, "limit": limit})
    results = data.get("results", [])

    if not results:
        return f"No results found for '{query}'"

    summary = f"Search results for '{query}' ({len(results)} found):\n\n"
    for r in results:
        obj_type = r.get("object_type", "unknown")
        obj = r.get("object", {})
        summary += f"• [{obj_type}] {obj.get('display', obj.get('name', 'N/A'))}\n"

    return summary + "\nRaw data:\n" + fmt(data)


if __name__ == "__main__":
    if not all([NETBOX_URL, NETBOX_TOKEN]):
        print("Error: NETBOX_URL and NETBOX_TOKEN must be set", flush=True)
    else:
        mcp.run()
