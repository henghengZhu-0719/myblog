from langchain_mcp_adapters.client import MultiServerMCPClient


DASHSCOPE_API_KEY = "sk-f434639a7e1345ed99c660461d92389d"
async def get_mcp_tools():
    client = MultiServerMCPClient({
        "WebSearch": {
            "transport": "http",
            "url": "https://dashscope.aliyuncs.com/api/v1/mcps/WebSearch/mcp",
            "headers": {"Authorization": f"Bearer {DASHSCOPE_API_KEY}"},
        }
    })
    return await client.get_tools()