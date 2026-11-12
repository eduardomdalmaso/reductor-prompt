import sys
import logging
from mcp.server.mcpserver import MCPServer

from src.adapters.inbound.mcp.brain_tools import register_brain_tools
from src.adapters.inbound.mcp.knowledge_tools import register_knowledge_tools
from src.adapters.inbound.mcp.decision_tools import register_decision_tools

# Desativa logs verbosos no stdout para não corromper o canal stdio do MCP
logging.basicConfig(level=logging.ERROR)

mcp = MCPServer("ReductorPrompt-KnowledgeServer")

register_brain_tools(mcp)
register_knowledge_tools(mcp)
register_decision_tools(mcp)

if __name__ == "__main__":
    mcp.run(transport="stdio")
