# agent_query.py
import os
import json
from azure.ai.projects.aio import AIProjectClient  # aio async client variant if needed
from azure.identity.aio import DefaultAzureCredential
from utils.agent_team import AgentTeam, _create_task
from dotenv import load_dotenv
from utils.agent_trace_configurator import AgentTraceConfigurator

load_dotenv()

from utils.user_functions_with_traces import (
    fetch_current_datetime,
    fetch_weather,
    send_email_using_recipient_name,
    convert_temperature,
)

# Mapping function names in yaml to actual python functions
function_name_to_func = {
    "fetch_current_datetime": fetch_current_datetime,
    "fetch_weather": fetch_weather,
    "send_email_using_recipient_name": send_email_using_recipient_name,
    "convert_temperature": convert_temperature,
}


async def query_agents(user_request: str, project_client) -> tuple[str, str]:
    if not project_client:
        return "Error: AIProjectClient is not initialized.", ""

    agents_client = project_client.agents

    # Enable auto function calls on the agent client
    agents_client.enable_auto_function_calls({
        _create_task,
        fetch_current_datetime,
        fetch_weather,
        send_email_using_recipient_name,
        convert_temperature,
    })

    model_deployment_name = os.getenv("MODEL_DEPLOYMENT_NAME")
    if not model_deployment_name:
        return "Error: Please define the environment variable MODEL_DEPLOYMENT_NAME.", ""

    # Setup tracing
    AgentTraceConfigurator(agents_client=agents_client).setup_tracing(1)

    team_name = os.getenv("AGENT_TEAM_NAME")
    if not team_name:
        return "Error: Environment variable AGENT_TEAM_NAME is not set.", ""

    # Try to get an existing AgentTeam, else create one
    try:
        agent_team = AgentTeam.get_team(team_name)
    except ValueError:
        try:
            agent_team = AgentTeam(team_name, agents_client=agents_client)
        except ValueError as ve:
            return f"Error: {ve}", ""

    agent_ids_file = agent_team._agent_ids_file

    if not agent_ids_file or not os.path.exists(agent_ids_file):
        return "Please run /agent_setup before asking a question.", ""

    try:
        with open(agent_ids_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        agents_data = data.get("agents", {})
    except (json.JSONDecodeError, IOError) as e:
        return f"Warning: Failed to read or parse JSON file '{agent_ids_file}': {e}\nPlease run /agent_setup before asking a question.", ""

    if not agents_data:
        return "Please run /agent_setup before asking a question.", ""

    # Load and verify agents exist by asynchronously calling get_agent
    agents_loaded = False
    for agent_name, info in agents_data.items():
        agent_id = info.get("id")
        role = info.get("role")
        if agent_id and role in ("leader", "member"):
            member = await agent_team.get_agent(agent_id)  # async call
            if member:
                agents_loaded = True

    if not agents_loaded:
        return "Please run /agent_setup before asking a question.", ""

    # Process the user request and get response and thread ID
    response, thread_id = await agent_team.process_request_threadid(request=user_request)
    return response, thread_id


# Standalone async test runner
if __name__ == "__main__":
    import asyncio

    async def main():
        user_request = (
            "Hello, Please provide me current time in '%Y-%m-%d %H:%M:%S' format, and the weather in New York. "
            "Finally, convert the Celsius to Fahrenheit and send an email to Example Recipient with summary of results."
        )
        # Make sure project_client is initialized here or else mock it for test
        resp, tid = await query_agents(user_request)
        print("Agent Response:", resp)
        print("Thread ID:", tid)

    asyncio.run(main())
