from typing import TypedDict, Literal

from langgraph.graph import StateGraph, END
from my_agent.utils.nodes import call_model, should_continue, tool_node, process_results, ask_personalization
from my_agent.utils.state import AgentState


# Define the config
class GraphConfig(TypedDict):
    model_name: Literal["anthropic", "openai"]


# Define a new graph
workflow = StateGraph(AgentState, config_schema=GraphConfig)

# Define the two nodes we will cycle between
# Add nodes
workflow.add_node("agent", call_model)
workflow.add_node("action", tool_node)
workflow.add_node("ask_personalization", ask_personalization)
workflow.add_node("process_results", process_results)

# Set the entrypoint as `agent`
# This means that this node is the first one called
workflow.set_entry_point("agent")

# We now add a conditional edge
# Add edges
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "continue": "action",
        "ask_personalization": "ask_personalization",
        "end": END,
    },
)

# We now add a normal edge from `tools` to `agent`.
# This means that after `tools` is called, `agent` node is called next.
workflow.add_edge("action", "agent")
workflow.add_edge("ask_personalization", "process_results")
workflow.add_edge("process_results", END)

# Finally, we compile it!
# This compiles it into a LangChain Runnable,
# meaning you can use it as you would any other runnable
graph = workflow.compile()
