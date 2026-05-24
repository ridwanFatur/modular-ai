import json
import uuid
from typing import Annotated, Literal, Sequence, TypedDict

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    ToolCall,
    ToolMessage,
)
from langchain_core.prompts.chat import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig, RunnableLambda
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from toolbox_langchain import ToolboxTool
from typing import Any, Dict, List, Optional, Sequence
from toolbox_langchain import ToolboxClient
from langchain_core.prompts import ChatPromptTemplate
import asyncio
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence
from pytz import timezone
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    ToolCall,
    ToolMessage,
)
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv
from toolbox_langchain import ToolboxClient

load_dotenv()


PREFIX = """The Cymbal Air Customer Service Assistant helps customers of Cymbal Air with their travel needs.

Cymbal Air (airline unique two letter identifier as CY) is a passenger airline offering convenient flights to many cities around the world from its
hub in San Francisco. Cymbal Air takes pride in using the latest technology to offer the best customer
service!

Cymbal Air Customer Service Assistant (or just "Assistant" for short) is designed to assist
with a wide range of tasks, from answering simple questions to complex multi-query questions that
require passing results from one query to another. Using the latest AI models, Assistant is able to
generate human-like text based on the input it receives, allowing it to engage in natural-sounding
conversations and provide responses that are coherent and relevant to the topic at hand. The assistant should 
not answer questions about other people's information for privacy reasons. 

Assistant is a powerful tool that can help answer a wide range of questions pertaining to travel on Cymbal Air
as well as amenities of San Francisco Airport."""

SUFFIX = """Begin! Use tools if necessary. Respond directly if appropriate."""

def __is_logged_in(config: RunnableConfig) -> bool:
    return bool(
        config
        and "configurable" in config
        and "auth_token_getters" in config["configurable"]
        and "my_google_service" in config["configurable"]["auth_token_getters"]
        and config["configurable"]["auth_token_getters"]["my_google_service"]()
    )
    
def __get_tool_to_run(tool: ToolboxTool, config: RunnableConfig):
    if (
        config
        and "configurable" in config
        and "auth_token_getters" in config["configurable"]
    ):
        auth_token_getters = config["configurable"]["auth_token_getters"]
        if auth_token_getters:
            core_tool = tool._ToolboxTool__core_tool  # type: ignore
            required_auth_keys = set(core_tool._required_authz_tokens)
            for auth_list in core_tool._required_authn_params.values():
                required_auth_keys.update(auth_list)
            filtered_getters = {
                k: v for k, v in auth_token_getters.items() if k in required_auth_keys
            }
            if filtered_getters:
                return tool.add_auth_token_getters(filtered_getters)
    return tool

def get_datetime():
    formatter = "%A, %m/%d/%Y, %H:%M:%S"
    now = datetime.now(timezone("US/Pacific"))
    return now.strftime(formatter)
        
def create_prompt_template() -> ChatPromptTemplate:
    current_datetime = "Today's date and current time is {cur_datetime}."
    template = "\n\n".join(
        [
            PREFIX,
            current_datetime,
            SUFFIX,
        ]
    )
    prompt = ChatPromptTemplate.from_messages(
        [("system", template), ("placeholder", "{messages}")]
    )
    prompt = prompt.partial(cur_datetime=get_datetime)
    return prompt

prompt = create_prompt_template()

TOOLBOX_URL = "http://127.0.0.1:5000"

async def get_tools_and_model():
    client = ToolboxClient(
        TOOLBOX_URL, 
        # client_headers={"Authorization": auth_token_provider}
    )
    
    tools = await client.aload_toolset("cymbal_air")
    insert_ticket = await client.aload_tool("insert_ticket")
    validate_ticket = await client.aload_tool("validate_ticket")
    
    model = ChatOpenAI(
        # max_output_tokens=512,
        model_name=f"openai/gpt-oss-120b",
        temperature=0,
        openai_api_base="https://api.groq.com/openai/v1",
        openai_api_key=os.environ.get("GROQ_API_KEY"),
        # top_p=1,
        # max_retries=3,
        # request_timeout=60,
    )
    
    model_with_tools = model.bind_tools(tools)
    model_runnable = prompt | model_with_tools
    return tools, model_runnable, insert_ticket, validate_ticket

def get_confirmation_needing_tools():
    return ["insert_ticket"]


def get_auth_tools():
    return [
        "insert_ticket",
        "list_tickets",
    ]