#!/usr/bin/env python3
"""
VPS Provisioner MCP Server
Provides tools for managing VPS deployments through Model Context Protocol
"""

import asyncio
import os
import sys
import time
import logging
from typing import Any, Dict, List, Optional

import requests
from mcp.server import Server
from mcp.types import Tool, TextContent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger("vps-provisioner-mcp")

# Configuration from environment
PROVISIONER_URL = os.getenv('PROVISIONER_URL', 'http://localhost:5001')
API_KEY = os.getenv('API_KEY', '39bf160a-775d-4408-babb-5098cd3e4353')

# Create MCP server instance
server = Server("vps-provisioner")


def make_request(method: str, endpoint: str, data: Optional[Dict] = None, timeout: int = 30) -> Dict[str, Any]:
    """Make HTTP request to provisioner API with error handling"""
    url = f"{PROVISIONER_URL}{endpoint}"
    headers = {
        'Content-Type': 'application/json',
        'X-API-Key': API_KEY
    }

    try:
        logger.info(f"{method} {url}")
        if method == 'GET':
            response = requests.get(url, headers=headers, timeout=timeout)
        elif method == 'POST':
            response = requests.post(url, json=data, headers=headers, timeout=timeout)
        else:
            return {"error": f"Unsupported method: {method}"}

        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        logger.error(f"Request timeout for {url}")
        return {"error": f"Request timeout after {timeout}s"}
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error to {url}")
        return {"error": f"Cannot connect to provisioner at {PROVISIONER_URL}"}
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error: {e}")
        return {"error": f"HTTP {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {"error": f"Unexpected error: {str(e)}"}


def format_status_response(status_data: Dict[str, Any]) -> str:
    """Format status response with emojis and structure"""
    if "error" in status_data:
        return f"❌ Error: {status_data['error']}"

    job_id = status_data.get('job_id', 'unknown')
    status = status_data.get('status', 'unknown')
    app = status_data.get('app', 'unknown')
    ip = status_data.get('ip_address', 'unknown')

    # Status emoji
    status_emoji = {
        'pending': '⏳',
        'running': '⚙️',
        'completed': '✅',
        'failed': '❌'
    }.get(status, '❓')

    result = f"{status_emoji} **Status: {status.upper()}**\n\n"
    result += f"📋 Job ID: `{job_id}`\n"
    result += f"📦 Application: {app}\n"
    result += f"🌐 IP Address: {ip}\n"

    # Progress information
    if 'progress' in status_data:
        progress = status_data['progress']
        result += f"\n📊 Progress: {progress.get('percent', 0)}%\n"
        if 'current_step' in progress:
            result += f"   Current: {progress['current_step']}\n"

    # Logs
    if 'logs' in status_data and status_data['logs']:
        result += f"\n📝 Recent logs:\n```\n"
        logs = status_data['logs'][-10:]  # Last 10 lines
        result += '\n'.join(logs)
        result += "\n```\n"

    # Completion details
    if status == 'completed' and 'result' in status_data:
        res = status_data['result']
        result += f"\n🎉 **Deployment Completed!**\n\n"

        if 'url' in res:
            result += f"🔗 URL: {res['url']}\n"
        if 'credentials' in res:
            creds = res['credentials']
            result += f"\n🔐 Credentials:\n"
            for key, value in creds.items():
                result += f"   {key}: `{value}`\n"
        if 'notes' in res:
            result += f"\n📌 Notes:\n{res['notes']}\n"

    # Failure details
    if status == 'failed' and 'error' in status_data:
        result += f"\n💥 Error: {status_data['error']}\n"

    return result


@server.list_tools()
async def list_tools() -> List[Tool]:
    """Return list of available tools"""
    return [
        Tool(
            name="deploy_app",
            description="Deploy pre-configured application (n8n, wireguard, outline, vaultwarden, 3x-ui, seafile, filebrowser)",
            inputSchema={
                "type": "object",
                "properties": {
                    "ip_address": {
                        "type": "string",
                        "description": "VPS IP address"
                    },
                    "username": {
                        "type": "string",
                        "description": "SSH username (usually 'root')"
                    },
                    "password": {
                        "type": "string",
                        "description": "SSH password"
                    },
                    "app": {
                        "type": "string",
                        "enum": ["n8n", "wireguard", "outline", "vaultwarden", "3x-ui", "seafile", "filebrowser"],
                        "description": "Application to deploy"
                    },
                    "custom_domain": {
                        "type": "string",
                        "description": "Custom domain (optional)"
                    }
                },
                "required": ["ip_address", "username", "password", "app"]
            }
        ),
        Tool(
            name="deploy_universal",
            description="Deploy ANY Docker application from docker-compose/image/repo",
            inputSchema={
                "type": "object",
                "properties": {
                    "ip_address": {
                        "type": "string",
                        "description": "VPS IP address"
                    },
                    "username": {
                        "type": "string",
                        "description": "SSH username"
                    },
                    "password": {
                        "type": "string",
                        "description": "SSH password"
                    },
                    "source_type": {
                        "type": "string",
                        "enum": ["docker-compose", "docker-image", "github-repo"],
                        "description": "Source type"
                    },
                    "source_url": {
                        "type": "string",
                        "description": "Source URL (compose file, image name, or repo URL)"
                    },
                    "app_name": {
                        "type": "string",
                        "description": "Application name"
                    },
                    "ports": {
                        "type": "object",
                        "description": "Port mappings (e.g. {'3001': '3001'})"
                    },
                    "env_vars": {
                        "type": "object",
                        "description": "Environment variables (e.g. {'API_KEY': 'xyz'})"
                    },
                    "max_memory_mb": {
                        "type": "number",
                        "description": "Max memory in MB"
                    },
                    "max_cpu": {
                        "type": "number",
                        "description": "Max CPU cores"
                    }
                },
                "required": ["ip_address", "username", "password", "source_type", "source_url", "app_name"]
            }
        ),
        Tool(
            name="check_status",
            description="Check deployment job status",
            inputSchema={
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "string",
                        "description": "Job ID to check"
                    }
                },
                "required": ["job_id"]
            }
        ),
        Tool(
            name="wait_for_completion",
            description="Wait for job to complete and return final result",
            inputSchema={
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "string",
                        "description": "Job ID to wait for"
                    },
                    "timeout": {
                        "type": "number",
                        "description": "Timeout in seconds (default: 1800)",
                        "default": 1800
                    }
                },
                "required": ["job_id"]
            }
        ),
        Tool(
            name="list_jobs",
            description="List recent deployment jobs",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "number",
                        "description": "Number of jobs to return (default: 10)",
                        "default": 10
                    },
                    "status": {
                        "type": "string",
                        "description": "Filter by status (pending/running/completed/failed)"
                    }
                }
            }
        ),
        Tool(
            name="get_stats",
            description="Get provisioner statistics",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> List[TextContent]:
    """Handle tool execution"""

    try:
        if name == "deploy_app":
            # Deploy pre-configured application
            payload = {
                "ip_address": arguments["ip_address"],
                "username": arguments["username"],
                "password": arguments["password"],
                "app": arguments["app"]
            }
            if "custom_domain" in arguments:
                payload["custom_domain"] = arguments["custom_domain"]

            logger.info(f"Deploying {arguments['app']} to {arguments['ip_address']}")
            result = make_request('POST', '/provision', payload)

            if "error" in result:
                return [TextContent(type="text", text=f"❌ Error: {result['error']}")]

            job_id = result.get('job_id', 'unknown')
            response = f"✅ Deployment started!\n\n"
            response += f"📋 Job ID: `{job_id}`\n"
            response += f"📦 Application: {arguments['app']}\n"
            response += f"🌐 IP Address: {arguments['ip_address']}\n\n"
            response += f"💡 Use `check_status` with job_id `{job_id}` to monitor progress\n"
            response += f"💡 Or use `wait_for_completion` to wait for deployment to finish"

            return [TextContent(type="text", text=response)]

        elif name == "deploy_universal":
            # Deploy universal Docker application
            payload = {
                "ip_address": arguments["ip_address"],
                "username": arguments["username"],
                "password": arguments["password"],
                "source_type": arguments["source_type"],
                "source_url": arguments["source_url"],
                "app_name": arguments["app_name"]
            }

            # Optional parameters
            if "ports" in arguments:
                payload["ports"] = arguments["ports"]
            if "env_vars" in arguments:
                payload["env_vars"] = arguments["env_vars"]
            if "max_memory_mb" in arguments:
                payload["max_memory_mb"] = arguments["max_memory_mb"]
            if "max_cpu" in arguments:
                payload["max_cpu"] = arguments["max_cpu"]

            logger.info(f"Deploying universal app {arguments['app_name']} to {arguments['ip_address']}")
            result = make_request('POST', '/provision/universal', payload)

            if "error" in result:
                return [TextContent(type="text", text=f"❌ Error: {result['error']}")]

            job_id = result.get('job_id', 'unknown')
            response = f"✅ Universal deployment started!\n\n"
            response += f"📋 Job ID: `{job_id}`\n"
            response += f"📦 Application: {arguments['app_name']}\n"
            response += f"🔗 Source: {arguments['source_url']}\n"
            response += f"🌐 IP Address: {arguments['ip_address']}\n\n"
            response += f"💡 Use `check_status` with job_id `{job_id}` to monitor progress"

            return [TextContent(type="text", text=response)]

        elif name == "check_status":
            # Check job status
            job_id = arguments["job_id"]
            logger.info(f"Checking status for job {job_id}")

            result = make_request('GET', f'/status/{job_id}')
            formatted = format_status_response(result)

            return [TextContent(type="text", text=formatted)]

        elif name == "wait_for_completion":
            # Wait for job completion with polling
            job_id = arguments["job_id"]
            timeout = arguments.get("timeout", 1800)
            poll_interval = 10  # seconds

            logger.info(f"Waiting for job {job_id} to complete (timeout: {timeout}s)")

            start_time = time.time()
            last_status = None

            response = f"⏳ Waiting for job `{job_id}` to complete...\n\n"

            while True:
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    response += f"\n⚠️ Timeout reached after {timeout}s\n"
                    response += f"Job may still be running. Use `check_status` to verify."
                    return [TextContent(type="text", text=response)]

                result = make_request('GET', f'/status/{job_id}')

                if "error" in result:
                    response += f"\n❌ Error: {result['error']}"
                    return [TextContent(type="text", text=response)]

                status = result.get('status', 'unknown')

                # Show progress update if status changed
                if status != last_status:
                    if 'progress' in result:
                        progress = result['progress']
                        percent = progress.get('percent', 0)
                        current_step = progress.get('current_step', 'Processing...')
                        response += f"📊 {percent}% - {current_step}\n"
                    last_status = status

                # Check if completed or failed
                if status == 'completed':
                    response += f"\n" + format_status_response(result)
                    return [TextContent(type="text", text=response)]

                if status == 'failed':
                    response += f"\n" + format_status_response(result)
                    return [TextContent(type="text", text=response)]

                # Wait before next poll
                await asyncio.sleep(poll_interval)

        elif name == "list_jobs":
            # List recent jobs
            limit = arguments.get("limit", 10)
            status_filter = arguments.get("status")

            logger.info(f"Listing jobs (limit: {limit}, status: {status_filter})")

            endpoint = f'/jobs?limit={limit}'
            if status_filter:
                endpoint += f'&status={status_filter}'

            result = make_request('GET', endpoint)

            if "error" in result:
                return [TextContent(type="text", text=f"❌ Error: {result['error']}")]

            jobs = result.get('jobs', [])

            if not jobs:
                return [TextContent(type="text", text="📋 No jobs found")]

            response = f"📋 **Recent Jobs** (showing {len(jobs)})\n\n"

            for job in jobs:
                job_id = job.get('job_id', 'unknown')
                status = job.get('status', 'unknown')
                app = job.get('app', 'unknown')
                ip = job.get('ip_address', 'unknown')
                created = job.get('created_at', 'unknown')

                status_emoji = {
                    'pending': '⏳',
                    'running': '⚙️',
                    'completed': '✅',
                    'failed': '❌'
                }.get(status, '❓')

                response += f"{status_emoji} `{job_id}` - {app} @ {ip}\n"
                response += f"   Status: {status} | Created: {created}\n\n"

            return [TextContent(type="text", text=response)]

        elif name == "get_stats":
            # Get provisioner statistics
            logger.info("Fetching provisioner statistics")

            result = make_request('GET', '/stats')

            if "error" in result:
                return [TextContent(type="text", text=f"❌ Error: {result['error']}")]

            response = f"📊 **VPS Provisioner Statistics**\n\n"

            total = result.get('total_jobs', 0)
            response += f"📋 Total Jobs: {total}\n\n"

            if 'by_status' in result:
                response += f"**By Status:**\n"
                for status, count in result['by_status'].items():
                    status_emoji = {
                        'pending': '⏳',
                        'running': '⚙️',
                        'completed': '✅',
                        'failed': '❌'
                    }.get(status, '❓')
                    response += f"   {status_emoji} {status}: {count}\n"
                response += "\n"

            if 'by_app' in result:
                response += f"**By Application:**\n"
                for app, count in result['by_app'].items():
                    response += f"   📦 {app}: {count}\n"

            return [TextContent(type="text", text=response)]

        else:
            return [TextContent(type="text", text=f"❌ Unknown tool: {name}")]

    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}", exc_info=True)
        return [TextContent(type="text", text=f"❌ Error executing {name}: {str(e)}")]


async def main():
    """Main entry point for MCP server"""
    logger.info(f"Starting VPS Provisioner MCP Server")
    logger.info(f"Provisioner URL: {PROVISIONER_URL}")
    logger.info(f"API Key: {'*' * (len(API_KEY) - 4)}{API_KEY[-4:]}")

    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)
