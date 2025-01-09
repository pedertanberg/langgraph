from functools import lru_cache
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from my_agent.utils.tools import tools, findUser
from langgraph.prebuilt import ToolNode
from typing import Literal
from langchain_core.messages import HumanMessage, AIMessage


@lru_cache(maxsize=4)
def _get_model(model_name: str):
    if model_name == "openai":
        model = ChatOpenAI(temperature=0, model_name="gpt-4o")
    elif model_name == "anthropic":
        model =  ChatAnthropic(temperature=0, model_name="claude-3-sonnet-20240229")
    else:
        raise ValueError(f"Unsupported model type: {model_name}")

    model = model.bind_tools(tools)
    return model

def should_continue(state):
    messages = state["messages"]
    last_message = messages[-1]
    
    # If we haven't asked about personalization yet and we have search results
    if not state.get("asked_personalization", False) and last_message.tool_calls:
        return "ask_personalization"
    # If there are tool calls, continue
    elif last_message.tool_calls:
        return "continue"
    # Otherwise end
    else:
        return "end"

def ask_personalization(state):
    """Ask the user if they want personalized results."""
    return {
        "messages": [AIMessage(content="Would you like personalized product recommendations? (yes/no)")],
        "asked_personalization": True
    }

def process_results(state, config):
    """Process search results with or without personalization."""
    messages = state["messages"]
    last_message = messages[-1]
    
    # Get the search results from the last tool call response
    search_results = None
    for prev_message in reversed(messages):
        if hasattr(prev_message, "tool_calls"):
            tool_outputs = [call.get("function", {}).get("name") == "search" for call in prev_message.tool_calls]
            if any(tool_outputs):
                search_results = prev_message.tool_calls[tool_outputs.index(True)].get("output")
                break
    
    if not search_results:
        return {"messages": [AIMessage(content="I couldn't find any products matching your search.")]}

    # If the user wants personalization
    if last_message.content.lower().strip() == "yes":
        model_name = config.get('configurable', {}).get("model_name", "anthropic")
        model = _get_model(model_name)
        
        # Get user profile
        user_profile = findUser()
        
        # Create a prompt for personalized recommendations
        personalization_prompt = f"""
        Given the following user profile and search results, provide personalized product recommendations.
        Rank the products based on relevance to the user and add a one-sentence explanation for each recommendation.
        
        User Profile:
        - Age: {user_profile['age']}
        - Occupation: {user_profile['occupation']}
        - Interests: {', '.join(user_profile['interests'])}
        - Recent Purchases: {', '.join(item['name'] for item in user_profile['purchase_history'])}
        
        Search Results:
        {search_results}
        
        Please provide the recommendations in a clear format, rank them by relevance to the user's profile, and add a one-sentence explanation for why each product might be particularly suitable for this user.
        """
        
        # Get personalized recommendations
        response = model.invoke([{"role": "user", "content": personalization_prompt}])
        return {"messages": [response], "user_profile": user_profile}
    
    # If user doesn't want personalization, format regular results
    formatted_results = "Here are the products I found:\n\n"
    for product in search_results:
        formatted_results += f"""
        - {product['title']}
        Price: {product['price']}
        Category: {product['category']}
        Description: {product['description_short']}
        
        """
    
    return {"messages": [AIMessage(content=formatted_results)]}


system_prompt = """You are a helpful shopping assistant at Elkjøp, a Norwegian electronics retailer. 
    Generate a personalized response for a customer based on their profile and the search results.t"""

# Define the function that calls the model
def call_model(state, config):
    messages = state["messages"]
    messages = [{"role": "system", "content": system_prompt}] + messages
    model_name = config.get('configurable', {}).get("model_name", "anthropic")
    model = _get_model(model_name)
    response = model.invoke(messages)
    # We return a list, because this will get added to the existing list
    return {"messages": [response]}

# Define the function to execute tools
tool_node = ToolNode(tools)