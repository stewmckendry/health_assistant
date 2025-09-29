#!/usr/bin/env python3
"""
Start MCP servers in HTTP mode for Railway deployment.
Each MCP server runs on a different port and the agents connect via HTTP.
"""

import asyncio
import os
import sys
import logging
from pathlib import Path
import subprocess
from typing import List

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define MCP servers and their ports
MCP_SERVERS = [
    {
        "name": "Dr. OFF MCP Server",
        "module": "src.agents.dr_off_agent.mcp.server_http",
        "port": 8001,
        "env_var": "MCP_DR_OFF_PORT"
    },
    {
        "name": "Dr. OPA MCP Server", 
        "module": "src.agents.dr_opa_agent.mcp.server_http",
        "port": 8002,
        "env_var": "MCP_DR_OPA_PORT"
    }
]

async def start_mcp_server(server_config: dict):
    """Start a single MCP server in HTTP mode"""
    name = server_config["name"]
    module = server_config["module"]
    port = server_config["port"]
    env_var = server_config["env_var"]
    
    # Set the port environment variable
    os.environ[env_var] = str(port)
    
    logger.info(f"Starting {name} on port {port}")
    
    try:
        # Run as a subprocess
        process = await asyncio.create_subprocess_exec(
            sys.executable, "-m", module,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=os.environ.copy()
        )
        
        # Monitor the process
        async def monitor_output(stream, prefix):
            while True:
                line = await stream.readline()
                if not line:
                    break
                logger.info(f"[{name}] {prefix}: {line.decode().strip()}")
        
        # Start monitoring tasks
        stdout_task = asyncio.create_task(monitor_output(process.stdout, "OUT"))
        stderr_task = asyncio.create_task(monitor_output(process.stderr, "ERR"))
        
        # Wait for process
        await process.wait()
        
        # Wait for output tasks to complete
        await stdout_task
        await stderr_task
        
        if process.returncode != 0:
            logger.error(f"{name} exited with code {process.returncode}")
        else:
            logger.info(f"{name} exited normally")
            
    except Exception as e:
        logger.error(f"Error starting {name}: {e}")
        raise

async def main():
    """Start all MCP servers concurrently"""
    logger.info("=" * 80)
    logger.info("Starting MCP Servers for Railway Deployment")
    logger.info("=" * 80)
    
    # Check if we're on Railway
    if os.environ.get("RAILWAY_ENVIRONMENT"):
        logger.info("Running on Railway - using HTTP mode for MCP servers")
    else:
        logger.info("Running locally - using HTTP mode for testing")
    
    # Start all servers concurrently
    tasks = []
    for server in MCP_SERVERS:
        task = asyncio.create_task(start_mcp_server(server))
        tasks.append(task)
    
    # Wait for all servers to complete (they shouldn't unless there's an error)
    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        logger.info("Shutting down MCP servers...")
        for task in tasks:
            task.cancel()
    except Exception as e:
        logger.error(f"Error running MCP servers: {e}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("MCP servers stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)