# ReAct implementation references

- https://github.com/langchain-ai/react-agent — README: each follow-up is appended to the same thread; template graph executes reason -> tool -> observe -> repeat until final answer; tools are declared in `tools.py` and orchestration in `graph.py`.
- https://raw.githubusercontent.com/langchain-ai/react-agent/main/src/react_agent/graph.py — sample uses a model node, `ToolNode(TOOLS)`, conditional routing based on `AIMessage.tool_calls`, and an edge from tools back to model.
- https://raw.githubusercontent.com/langchain-ai/react-agent/main/src/react_agent/tools.py — example keeps callable tools in an explicit `TOOLS` list.
- https://reference.langchain.com/python/langgraph.prebuilt/chat_agent_executor/create_react_agent — LangGraph ReAct cycle semantics and checkpoint/thread memory description; reference notes the older factory is deprecated in favor of `create_agent`, while user-requested template uses the explicit custom graph cycle.
