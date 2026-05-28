"""
Unified Claude Agent — Jenkins + NetBox (via Portkey/ADI Hub)
Connects to both MCP servers simultaneously and routes tool calls appropriately.
Missing credentials for either server will gracefully skip that server.
"""
import asyncio
import os
import json
import time
from contextlib import AsyncExitStack
from dotenv import load_dotenv
from portkey_ai import Portkey
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()

portkey_client = Portkey(api_key=os.getenv("PORTKEY_API_KEY"))

CLAUDE_MODEL = "@bedrock-global/us.anthropic.claude-sonnet-4-6"

SYSTEM_PROMPT = """You are an Intelligent Test Harness Agent — an AI assistant that helps engineering teams manage automated testing workflows and infrastructure.

You have access to two systems:

## Jenkins (CI/CD)
- Trigger and monitor builds and test pipelines
- Analyze build failures and console output
- List jobs, check queue status, retrieve build history
- Identify failing tests and suggest root causes

## NetBox (Infrastructure / DCIM / IPAM)
- Query devices, sites, racks, cables, and interfaces
- Look up IP addresses, prefixes, and VLANs
- List virtual machines and clusters
- Search across all infrastructure objects

## Cross-system capabilities
You can correlate data across both systems — for example:
- "Which devices in NetBox are associated with failing Jenkins builds?"
- "What is the IP of the server running job X?"
- "Show me all test results for the dc-manila site's devices"

## Guidelines
- Be proactive: anticipate what information the user needs and fetch it
- Summarize large outputs; offer raw details on request
- Chain tools intelligently across both systems
- When diagnosing failures, check related systems automatically
- If a tool is not available (server not connected), say so clearly
"""


def call_claude_with_retry(messages: list, tools: list, max_retries: int = 3):
    """Call Claude via Portkey with exponential backoff on rate limits."""
    for attempt in range(max_retries):
        try:
            return portkey_client.chat.completions.create(
                model=CLAUDE_MODEL,
                messages=messages,
                tools=tools,
                max_tokens=2048,
            )
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "Too many tokens" in error_str:
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) * 5
                    print(f"⏳ Rate limit hit. Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    raise Exception("Rate limit exceeded. Please wait a few minutes and try again.")
            else:
                raise


async def chat_with_agent(
    user_message: str,
    tool_session_map: dict[str, ClientSession],
    all_tools: list,
) -> str:
    """
    Send a message to Claude. Claude can call any tool from either MCP server.
    tool_session_map: {tool_name -> ClientSession} for routing tool calls.
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    print(f"\n🤖 You: {user_message}")
    print(f"💭 Thinking... ({len(all_tools)} tools available)\n")

    while True:
        response = call_claude_with_retry(messages, all_tools)
        choice = response.choices[0]
        message = choice.message

        print(f"🔍 Finish reason: {choice.finish_reason}")

        if (
            choice.finish_reason in ["tool_calls", "tool_use"]
            and hasattr(message, "tool_calls")
            and message.tool_calls
        ):
            print(f"🔍 Tool calls: {len(message.tool_calls)}")
            messages.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": message.tool_calls,
            })

            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_input = json.loads(tool_call.function.arguments)

                session = tool_session_map.get(tool_name)
                if session is None:
                    error_msg = f"Tool '{tool_name}' not found in any connected MCP server."
                    print(f"   ❌ {error_msg}")
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": error_msg,
                    })
                    continue

                print(f"🔧 Calling: {tool_name}")
                print(f"   Params: {tool_input}")

                try:
                    result = await session.call_tool(tool_name, tool_input)
                    tool_result_text = "".join(
                        c.text for c in result.content if hasattr(c, "text")
                    )
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": tool_result_text,
                    })
                    print("   ✅ Success\n")
                except Exception as e:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": f"Error: {str(e)}",
                    })
                    print(f"   ❌ Error: {e}\n")
        else:
            print("🔍 No tool calls")
            return message.content or ""


def build_server_params() -> list[tuple[str, StdioServerParameters]]:
    """
    Build MCP server configs for each available integration.
    Returns list of (label, StdioServerParameters) for servers with valid creds.
    """
    servers = []
    env = os.environ.copy()

    jenkins_vars = ["JENKINS_URL", "JENKINS_USERNAME", "JENKINS_TOKEN"]
    if all(os.getenv(v) for v in jenkins_vars):
        servers.append((
            "Jenkins",
            StdioServerParameters(
                command="python",
                args=["jenkins_mcp_server_fastmcp.py"],
                env={**env, **{v: os.getenv(v) for v in jenkins_vars}},
            ),
        ))
    else:
        print("⚠️  Jenkins credentials not set — Jenkins tools will be unavailable.")
        print("    Set JENKINS_URL, JENKINS_USERNAME, JENKINS_TOKEN in .env to enable.")

    netbox_vars = ["NETBOX_URL", "NETBOX_TOKEN"]
    if all(os.getenv(v) for v in netbox_vars):
        servers.append((
            "NetBox",
            StdioServerParameters(
                command="python",
                args=["netbox_mcp_server.py"],
                env={**env, **{v: os.getenv(v) for v in netbox_vars}},
            ),
        ))
    else:
        print("⚠️  NetBox credentials not set — NetBox tools will be unavailable.")
        print("    Set NETBOX_URL and NETBOX_TOKEN in .env to enable.")

    return servers


async def main():
    print("=" * 70)
    print("Intelligent Test Harness Agent — Jenkins + NetBox (via ADI Hub)")
    print("=" * 70)

    if not os.getenv("PORTKEY_API_KEY"):
        print("\n❌ ERROR: PORTKEY_API_KEY not set in .env")
        return

    server_configs = build_server_params()
    if not server_configs:
        print("\n❌ No MCP servers could be started. Set credentials in .env and retry.")
        return

    tool_session_map: dict[str, ClientSession] = {}
    all_tools: list = []

    async with AsyncExitStack() as stack:
        for label, params in server_configs:
            print(f"\n🔌 Connecting to {label} MCP Server...")
            try:
                read, write = await stack.enter_async_context(stdio_client(params))
                session = await stack.enter_async_context(ClientSession(read, write))
                await session.initialize()

                tools_result = await session.list_tools()
                count = len(tools_result.tools)
                print(f"✅ {label} connected — {count} tools available")

                for tool in tools_result.tools:
                    tool_session_map[tool.name] = session
                    all_tools.append({
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": tool.inputSchema,
                        },
                    })
            except Exception as e:
                print(f"❌ Failed to connect to {label}: {e}")

        if not all_tools:
            print("\n❌ No tools loaded. Check server logs above.")
            return

        connected = list({v for v in tool_session_map.values()})
        print(f"\n{'=' * 70}")
        print(f"Ready! {len(all_tools)} tools loaded across {len(connected)} server(s).")
        print("\nExample queries:")
        print("  Jenkins:  'List all failing jobs'")
        print("  Jenkins:  'Show console output of the last failed build for job X'")
        print("  NetBox:   'List all active devices at site dc-manila'")
        print("  NetBox:   'What VLANs are configured at site hq?'")
        print("  Combined: 'What is the IP of the server running job X?'")
        print("\nType 'quit' or 'exit' to stop.")
        print("=" * 70)

        while True:
            try:
                user_input = input("\n📝 You: ").strip()

                if user_input.lower() in ["quit", "exit", "q"]:
                    print("\n👋 Goodbye!")
                    break

                if not user_input:
                    continue

                response = await chat_with_agent(user_input, tool_session_map, all_tools)
                print(f"\n🤖 Claude:\n{response}\n")

            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                import traceback
                traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
