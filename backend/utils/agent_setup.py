import os
import json
import yaml
from azure.ai.agents.models import ToolSet, FunctionTool
from utils.agent_team import AgentTeam, _create_task
from utils.user_functions_with_traces import (
    fetch_current_datetime,
    fetch_weather,
    send_email_using_recipient_name,
    convert_temperature,
)
from utils.agent_trace_configurator import AgentTraceConfigurator
from dotenv import load_dotenv

load_dotenv()

# Mapping function names in yaml to actual python functions
function_name_to_func = {
    "fetch_current_datetime": fetch_current_datetime,
    "fetch_weather": fetch_weather,
    "send_email_using_recipient_name": send_email_using_recipient_name,
    "convert_temperature": convert_temperature,
}


def load_agent_config(yaml_file_path: str):
    with open(yaml_file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


async def setup_agents(project_client):
    if not project_client:
        print("Error: AIProjectClient is not initialized.")
        return

    agents_client = project_client.agents

    agents_client.enable_auto_function_calls({
        _create_task,
        fetch_current_datetime,
        fetch_weather,
        send_email_using_recipient_name,
        convert_temperature,
    })

    model_deployment_name = os.getenv("MODEL_DEPLOYMENT_NAME")
    if not model_deployment_name:
        print("Error: Please define the environment variable MODEL_DEPLOYMENT_NAME.")
        return

    # Setup tracing
    AgentTraceConfigurator(agents_client=agents_client).setup_tracing(1)

    agent_team = AgentTeam(os.getenv("AGENT_TEAM_NAME"), agents_client=agents_client)
    agent_ids_file = agent_team._agent_ids_file

    agents_exist = False
    if agent_ids_file and os.path.exists(agent_ids_file):
        try:
            with open(agent_ids_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            agents_data = data.get("agents", {})
            if isinstance(agents_data, dict) and agents_data:
                # Agents exist, dismantle team first
                print("Existing agents found, dismantling current team...")
                # Assume dismantle_team is async; await if so
                maybe_coro = agent_team.dismantle_team()
                if hasattr(maybe_coro, "__await__"):
                    await maybe_coro
                else:
                    # sync method
                    pass
                agents_exist = True
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Failed to read or parse JSON file '{agent_ids_file}': {e}")

    # Load agent config file from /backend/config
    yaml_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config", "agentmember_instruction.yaml"))
    agent_config = load_agent_config(yaml_path)

    # Create agents from yaml config
    for agent in agent_config.get("agents", []):
        user_function_names = agent.get("user_functions", [])
        user_functions = {
            function_name_to_func[name]
            for name in user_function_names if name in function_name_to_func
        }
        functions = FunctionTool(functions=user_functions)
        toolset = ToolSet()
        toolset.add(functions)

        # Assuming add_agent is sync; if async, await it accordingly
        maybe_coro = agent_team.add_agent(
            model=model_deployment_name,
            name=agent.get("name"),
            instructions=agent.get("instructions"),
            toolset=toolset,
            can_delegate=agent.get("can_delegate", False),
        )
        if hasattr(maybe_coro, "__await__"):
            await maybe_coro

    # Assemble all agents in the team (await if async)
    maybe_coro = agent_team.assemble_team()
    if hasattr(maybe_coro, "__await__"):
        await maybe_coro

    print("Agent team setup completed.")


# Run standalone test asynchronously
if __name__ == "__main__":
    import asyncio

    asyncio.run(setup_agents())
