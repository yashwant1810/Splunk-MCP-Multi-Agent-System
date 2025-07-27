import os
import sys
import asyncio
from dotenv import load_dotenv
from contextlib import AsyncExitStack
from typing import Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()

class MCPClient:
    def __init__(self, server_script_path: Optional[str] = None):
        self.exit_stack = AsyncExitStack()
        self.session: Optional[ClientSession] = None
        self.server_script_path = server_script_path or os.getenv("SPLUNK_MCP_PATH", "python/server.py")

    async def connect(self):
        if not self.server_script_path.endswith('.py'):
            raise ValueError("Only .py server scripts are supported for now.")

        # Build environment variables for the server
        env_vars = {
            "TRANSPORT": "stdio",
            "SPLUNK_HOST": os.getenv("SPLUNK_HOST")
        }
        
        # Check for token-based authentication first
        splunk_token = os.getenv("SPLUNK_TOKEN")
        if splunk_token:
            print("🔐 Using token-based authentication")
            env_vars["SPLUNK_TOKEN"] = splunk_token
            # Don't include username/password when using token
        else:
            # Fallback to username/password authentication
            splunk_username = os.getenv("SPLUNK_USERNAME")
            splunk_password = os.getenv("SPLUNK_PASSWORD")
            
            if splunk_username and splunk_password:
                print("🔐 Using username/password authentication")
                env_vars["SPLUNK_USERNAME"] = splunk_username
                env_vars["SPLUNK_PASSWORD"] = splunk_password
            else:
                raise ValueError(
                    "Authentication required: Either set SPLUNK_TOKEN or both SPLUNK_USERNAME and SPLUNK_PASSWORD"
                )

        server_params = StdioServerParameters(
            command=sys.executable,
            args=[self.server_script_path],
            env=env_vars
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.session = await self.exit_stack.enter_async_context(ClientSession(*stdio_transport))
        await self.session.initialize()

    async def validate_spl(self, query: str):
        return await self.session.call_tool("validate_spl", {"query": query})

    async def search_oneshot(self, query: str, earliest_time: str = "-24h", latest_time: str = "now"):
        return await self.session.call_tool("search_oneshot", {
            "query": query,
            "earliest_time": earliest_time,
            "latest_time": latest_time,
            "output_format": "markdown"
        })

    async def get_indexes(self):
        return await self.session.call_tool("get_indexes", {})

    async def run_saved_search(self, search_name: str):
        return await self.session.call_tool("run_saved_search", {
            "search_name": search_name,
            "trigger_actions": False
        })

    async def search_export(self, query: str, earliest_time: str = "-24h", latest_time: str = "now", max_count: int = 100, output_format: str = "json", risk_tolerance: Optional[int] = None, sanitize_output: Optional[bool] = None):
        payload = {
            "query": query,
            "earliest_time": earliest_time,
            "latest_time": latest_time,
            "max_count": max_count,
            "output_format": output_format,
        }
        if risk_tolerance is not None:
            payload["risk_tolerance"] = risk_tolerance
        if sanitize_output is not None:
            payload["sanitize_output"] = sanitize_output
        return await self.session.call_tool("search_export", payload)

    async def get_saved_searches(self):
        return await self.session.call_tool("get_saved_searches", {})

    async def get_config(self):
        return await self.session.call_tool("get_config", {})

    async def close(self):
        await self.exit_stack.aclose()

# Example usage (for testing only)
async def main():
    client = MCPClient()
    try:
        await client.connect()
        result = await client.get_config()
        print("✅ Connection successful!")
        print(result)
    except Exception as e:
        print(f"❌ Connection failed: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())