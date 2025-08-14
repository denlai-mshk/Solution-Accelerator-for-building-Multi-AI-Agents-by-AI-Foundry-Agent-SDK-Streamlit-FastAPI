# pylint: disable=line-too-long,useless-suppression
# ------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# ------------------------------------
import os
import json
import yaml  # type: ignore

from opentelemetry import trace
from opentelemetry.trace import Span  # noqa: F401 # pylint: disable=unused-import
from typing import Any, Dict, Optional, Set, List
from azure.ai.agents.aio import AgentsClient  # async client variant
from azure.ai.agents.models import FunctionTool, ToolSet, MessageRole, Agent, AgentThread

tracer = trace.get_tracer(__name__)


class _AgentTeamMember:
    """
    Represents an individual agent on a team.

    :param model: The model (e.g. GPT-4) used by this agent.
    :param name: The agent's name.
    :param instructions: The agent's initial instructions or "personality".
    :param toolset: An optional ToolSet with specialized tools for this agent.
    :param can_delegate: Whether this agent has delegation capability (e.g., 'create_task').
                         Defaults to True.
    """

    def __init__(
        self, model: str, name: str, instructions: str, toolset: Optional[ToolSet] = None, can_delegate: bool = True
    ) -> None:
        self.model = model
        self.name = name
        self.instructions = instructions
        self.agent_instance: Optional[Agent] = None
        self.toolset: Optional[ToolSet] = toolset
        self.can_delegate = can_delegate


class AgentTask:
    """
    Encapsulates a task for an agent to perform.

    :param recipient: The name of the agent who should receive the task.
    :param task_description: The description of the work to be done or question to be answered.
    :param requestor: The name of the agent or user requesting the task.
    """

    def __init__(self, recipient: str, task_description: str, requestor: str) -> None:
        self.recipient = recipient
        self.task_description = task_description
        self.requestor = requestor


class AgentTeam:
    """
    A class that represents a team of agents.
    """

    # Static container to store all instances of AgentTeam
    _teams: Dict[str, "AgentTeam"] = {}

    _agents_client: AgentsClient
    _agent_thread: Optional[AgentThread] = None
    _team_leader: Optional[_AgentTeamMember] = None
    _members: List[_AgentTeamMember] = []
    _tasks: List[AgentTask] = []
    _team_name: str = ""
    _current_request_span: Optional[Span] = None
    _current_task_span: Optional[Span] = None

    _agent_ids_file: Optional[str] = None  # Filepath for storing agent IDs JSON

    def __init__(self, team_name: str, agents_client: AgentsClient):
        """
        Initialize a new AgentTeam and set it as the singleton instance.
        """
        if not isinstance(team_name, str) or not team_name:
            raise ValueError("Team name must be a non-empty string.")
        if team_name in AgentTeam._teams:
            raise ValueError(f"A team with the name '{team_name}' already exists.")
        if agents_client is None:
            raise ValueError("No AgentsClient provided.")

        self.team_name = team_name
        self._agents_client = agents_client
        AgentTeam._teams[team_name] = self

        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.abspath(os.path.join(current_dir, "..", "config", "agent_team_config.yaml"))

        with open(file_path, "r") as config_file:
            config = yaml.safe_load(config_file)
            self.TEAM_LEADER_INSTRUCTIONS = config["TEAM_LEADER_INSTRUCTIONS"]
            self.TEAM_LEADER_INITIAL_REQUEST = config["TEAM_LEADER_INITIAL_REQUEST"]
            self.TEAM_LEADER_TASK_COMPLETENESS_CHECK_INSTRUCTIONS = config[
                "TEAM_LEADER_TASK_COMPLETENESS_CHECK_INSTRUCTIONS"
            ]
            self.TEAM_MEMBER_CAN_DELEGATE_INSTRUCTIONS = config["TEAM_MEMBER_CAN_DELEGATE_INSTRUCTIONS"]
            self.TEAM_MEMBER_NO_DELEGATE_INSTRUCTIONS = config["TEAM_MEMBER_NO_DELEGATE_INSTRUCTIONS"]
            self.TEAM_LEADER_MODEL = config["TEAM_LEADER_MODEL"].strip()

        parent_dir = os.path.dirname(current_dir)  # this will be \proj
        self._agent_ids_file = os.path.join(parent_dir, "config", f"{self.team_name}_agent_ids.json")

    @staticmethod
    def get_team(team_name: str) -> "AgentTeam":
        """Static method to fetch the AgentTeam instance by name."""
        team = AgentTeam._teams.get(team_name)
        if team is None:
            raise ValueError(f"No team found with the name '{team_name}'.")
        return team

    @staticmethod
    def _remove_team(team_name: str) -> None:
        """Static method to remove an AgentTeam instance by name."""
        if team_name not in AgentTeam._teams:
            raise ValueError(f"No team found with the name '{team_name}'.")
        del AgentTeam._teams[team_name]

    def add_agent(
        self, model: str, name: str, instructions: str, toolset: Optional[ToolSet] = None, can_delegate: bool = True
    ) -> None:
        """
        Add a new agent (team member) to this AgentTeam.

        :param model: The model name (e.g. GPT-4) for the agent.
        :param name: The name of the agent being added.
        :param instructions: The initial instructions/personality for the agent.
        :param toolset: An optional ToolSet to configure specific tools (functions, etc.)
                        for this agent. If None, we'll create a default set.
        :param can_delegate: If True, the agent can delegate tasks (via create_task).
                            If False, the agent does not get 'create_task' in its ToolSet
                            and won't mention delegation in instructions.
        """
        if toolset is None:
            toolset = ToolSet()

        if can_delegate:
            # If agent can delegate, ensure it has 'create_task'
            try:
                function_tool = toolset.get_tool(FunctionTool)
                function_tool.add_functions(agent_team_default_functions)
            except ValueError:
                default_function_tool = FunctionTool(agent_team_default_functions)
                toolset.add(default_function_tool)

        member = _AgentTeamMember(
            model=model,
            name=name,
            instructions=instructions,
            toolset=toolset,
            can_delegate=can_delegate,
        )
        self._members.append(member)

    def set_team_leader(self, model: str, name: str, instructions: str, toolset: Optional[ToolSet] = None) -> None:
        """
        Set the team leader for this AgentTeam.

        If team leader has not been set prior to the call to assemble_team,
        then a default team leader will be set.

        :param model: The model name (e.g. GPT-4) for the agent.
        :param name: The name of the team leader.
        :param instructions: The instructions for the team leader. These instructions
                             are not modified by the implementation, so all required
                             information about other team members and how to pass tasks
                             to them should be included.
        :param toolset: An optional ToolSet to configure specific tools (functions, etc.)
                        for the team leader.
        """
        member = _AgentTeamMember(model=model, name=name, instructions=instructions, toolset=toolset)
        self._team_leader = member

    def add_task(self, task: AgentTask) -> None:
        """
        Add a new task to the team's task list.

        :param task: The task to be added.
        """
        self._tasks.append(task)

    def _create_team_leader(self) -> None:
        """
        Create the team leader agent.
        """
        assert self._agents_client is not None, "agents_client must not be None"
        assert self._team_leader is not None, "team leader has not been added"

        self._team_leader.agent_instance = self._agents_client.create_agent(
            model=self._team_leader.model,
            name=self._team_leader.name,
            instructions=self._team_leader.instructions,
            toolset=self._team_leader.toolset,
        )

    def _set_default_team_leader(self):
        """
        Set the default 'TeamLeader' agent with awareness of all other agents.
        """
        toolset = ToolSet()
        toolset.add(default_function_tool)
        instructions = self.TEAM_LEADER_INSTRUCTIONS.format(agent_name="TeamLeader", team_name=self.team_name) + "\n"
        for member in self._members:
            instructions += f"- {member.name}: {member.instructions}\n"

        self._team_leader = _AgentTeamMember(
            model=self.TEAM_LEADER_MODEL,
            name="TeamLeader",
            instructions=instructions,
            toolset=toolset,
            can_delegate=True,
        )

    def _save_agent_ids(self):
        """
        Save the team leader and member agent names, ids, and roles to a JSON file.
        """
        data = {"agents": {}}

        if self._team_leader and self._team_leader.agent_instance:
            data["agents"][self._team_leader.name] = {
                "id": self._team_leader.agent_instance.id,
                "role": "leader",
            }

        for member in self._members:
            if member.agent_instance and (not self._team_leader or member.name != self._team_leader.name):
                data["agents"][member.name] = {
                    "id": member.agent_instance.id,
                    "role": "member",
                }

        with open(self._agent_ids_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def _load_agent_ids(self):
        """
        Load the saved agents with ids and roles from JSON file.
        Return a dict with separate keys for leader and members:

        {
            "team_leader_id": "...",
            "member_agent_ids": ["...", "...", ...]
        }
        """
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        agent_ids_file = os.path.join(parent_dir, "config", f"{self.team_name}_agent_ids.json")

        if not os.path.exists(agent_ids_file):
            return {"team_leader_id": None, "member_agent_ids": []}

        with open(agent_ids_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        agents = data.get("agents", {})
        team_leader_id = None
        member_agent_ids = []

        for name, info in agents.items():
            if info.get("role") == "leader":
                team_leader_id = info.get("id")
            elif info.get("role") == "member":
                member_agent_ids.append(info.get("id"))

        return {"team_leader_id": team_leader_id, "member_agent_ids": member_agent_ids}

    async def assemble_team(self):
        """
        Create the team leader agent and initialize all member agents with
        their configured or default toolsets. After creation, save their IDs.
        """
        assert self._agents_client is not None, "agents_client must not be None"

        if self._team_leader is None:
            self._set_default_team_leader()

        self._team_leader.agent_instance = await self._agents_client.create_agent(
            model=self._team_leader.model,
            name=self._team_leader.name,
            instructions=self._team_leader.instructions,
            toolset=self._team_leader.toolset,
        )

        for member in self._members:
            if member is self._team_leader:
                continue

            team_description = ""
            for other_member in self._members:
                if other_member != member:
                    team_description += f"- {other_member.name}: {other_member.instructions}\n"

            if member.can_delegate:
                extended_instructions = self.TEAM_MEMBER_CAN_DELEGATE_INSTRUCTIONS.format(
                    name=member.name,
                    team_name=self.team_name,
                    original_instructions=member.instructions,
                    team_description=team_description,
                )
            else:
                extended_instructions = self.TEAM_MEMBER_NO_DELEGATE_INSTRUCTIONS.format(
                    name=member.name,
                    team_name=self.team_name,
                    original_instructions=member.instructions,
                    team_description=team_description,
                )

            member.agent_instance = await self._agents_client.create_agent(
                model=member.model, name=member.name, instructions=extended_instructions, toolset=member.toolset
            )
        self._save_agent_ids()

    async def dismantle_team(self) -> None:
        """
        Delete all agents (including the team leader) from the project client,
        using the saved agent IDs from JSON file.
        """
        assert self._agents_client is not None, "agents_client must not be None"

        ids = self._load_agent_ids()
        team_leader_id = ids.get("team_leader_id")
        member_agent_ids = ids.get("member_agent_ids", [])

        if team_leader_id:
            print(f"Deleting team leader agent with ID '{team_leader_id}'")
            try:
                await self._agents_client.delete_agent(team_leader_id)
            except Exception as e:
                print(f"Warning: Failed to delete leader agent with ID '{team_leader_id}': {e}")

        for agent_id in member_agent_ids:
            if agent_id != team_leader_id:
                print(f"Deleting agent with ID '{agent_id}'")
                try:
                    await self._agents_client.delete_agent(agent_id)
                except Exception as e:
                    print(f"Warning: Failed to delete agent with ID '{agent_id}': {e}")

        try:
            if os.path.exists(self._agent_ids_file):
                os.remove(self._agent_ids_file)
        except Exception as e:
            print(f"Warning: Failed to remove agent IDs file '{self._agent_ids_file}': {e}")

        AgentTeam._remove_team(self.team_name)

    def _add_task_completion_event(
        self,
        span: Span,
        result: str,
    ) -> None:
        attributes: Dict[str, Any] = {}
        attributes["agent_team.task.result"] = result
        span.add_event(name=f"agent_team.task_completed", attributes=attributes)

    async def process_request_threadid(self, request: str, thread_id: Optional[str] = None) -> tuple[str, str]:
        """
        Handle a user's request by creating a team and delegating tasks to
        the team leader. The team leader may generate additional tasks.

        :param request: The user's request or question.
        :param thread_id: Optional thread ID; if provided and not empty, reuse existing thread.
        :return: A tuple containing the last outcome from the agent team as a string,
                and the thread ID as a string.
        """
        assert self._agents_client is not None, "project client must not be None"
        assert self._team_leader is not None, "team leader must not be None"

        last_outcome = ""  # Initialize last outcome variable

        # Use existing thread if thread_id given and valid; else create new thread
        if thread_id is not None and thread_id.strip() != "":
            try:
                self._agent_thread = await self._agents_client.threads.get(thread_id)
                print(f"Using existing thread with ID: {self._agent_thread.id}")
            except Exception as e:
                print(f"Failed to get thread with ID '{thread_id}': {e}")
                # fallback to creating new thread
                self._agent_thread = await self._agents_client.threads.create()
                print(f"Created new thread with ID: {self._agent_thread.id}")
        else:
            self._agent_thread = await self._agents_client.threads.create()
            print(f"Created thread with ID: {self._agent_thread.id}")

        with tracer.start_as_current_span("agent_team_request") as current_request_span:
            self._current_request_span = current_request_span
            if self._current_request_span is not None:
                self._current_request_span.set_attribute("agent_team.name", self.team_name)
            team_leader_request = self.TEAM_LEADER_INITIAL_REQUEST.format(original_request=request)
            _create_task(
                team_name=self.team_name,
                recipient=self._team_leader.name,
                request=team_leader_request,
                requestor="user",
            )
            while self._tasks:
                task = self._tasks.pop(0)
                with tracer.start_as_current_span("agent_team_task") as current_task_span:
                    self._current_task_span = current_task_span
                    if self._current_task_span is not None:
                        self._current_task_span.set_attribute("agent_team.name", self.team_name)
                        self._current_task_span.set_attribute("agent_team.task.recipient", task.recipient)
                        self._current_task_span.set_attribute("agent_team.task.requestor", task.requestor)
                        self._current_task_span.set_attribute("agent_team.task.description", task.task_description)
                    print(
                        f"Starting task for agent '{task.recipient}'. "
                        f"Requestor: '{task.requestor}'. "
                        f"Task description: '{task.task_description}'."
                    )
                    message = await self._agents_client.messages.create(
                        thread_id=self._agent_thread.id,
                        role="user",
                        content=task.task_description,
                    )
                    print(f"Created message with ID: {message.id} for task in thread {self._agent_thread.id}")
                    agent = self._get_member_by_name(task.recipient)
                    if agent and agent.agent_instance:
                        run = await self._agents_client.runs.create_and_process(
                            thread_id=self._agent_thread.id, agent_id=agent.agent_instance.id
                        )
                        print(f"Created and processed run for agent '{agent.name}', run ID: {run.id}")
                        text_message = await self._agents_client.messages.get_last_message_text_by_role(
                            thread_id=self._agent_thread.id, role=MessageRole.AGENT
                        )
                        if text_message and text_message.text:
                            print(f"Agent '{agent.name}' completed task. Outcome: {text_message.text.value}")
                            last_outcome = text_message.text.value  # Capture last outcome here
                            if self._current_task_span is not None:
                                self._add_task_completion_event(self._current_task_span, result=text_message.text.value)

                    if not self._tasks and not task.recipient == "TeamLeader":
                        team_leader_request = self.TEAM_LEADER_TASK_COMPLETENESS_CHECK_INSTRUCTIONS
                        _create_task(
                            team_name=self.team_name,
                            recipient=self._team_leader.name,
                            request=team_leader_request,
                            requestor="user",
                        )
                    self._current_task_span = None
            self._current_request_span = None

        return last_outcome, self._agent_thread.id


    async def process_request(self, request: str) -> None:
        """
        Handle a user's request by creating a team and delegating tasks to
        the team leader. The team leader may generate additional tasks.

        :param request: The user's request or question.
        """
        assert self._agents_client is not None, "project client must not be None"
        assert self._team_leader is not None, "team leader must not be None"

        if self._agent_thread is None:
            self._agent_thread = await self._agents_client.threads.create()
            print(f"Created thread with ID: {self._agent_thread.id}")

        with tracer.start_as_current_span("agent_team_request") as current_request_span:
            self._current_request_span = current_request_span
            if self._current_request_span is not None:
                self._current_request_span.set_attribute("agent_team.name", self.team_name)
            team_leader_request = self.TEAM_LEADER_INITIAL_REQUEST.format(original_request=request)
            _create_task(
                team_name=self.team_name,
                recipient=self._team_leader.name,
                request=team_leader_request,
                requestor="user",
            )
            while self._tasks:
                task = self._tasks.pop(0)
                with tracer.start_as_current_span("agent_team_task") as current_task_span:
                    self._current_task_span = current_task_span
                    if self._current_task_span is not None:
                        self._current_task_span.set_attribute("agent_team.name", self.team_name)
                        self._current_task_span.set_attribute("agent_team.task.recipient", task.recipient)
                        self._current_task_span.set_attribute("agent_team.task.requestor", task.requestor)
                        self._current_task_span.set_attribute("agent_team.task.description", task.task_description)
                    print(
                        f"Starting task for agent '{task.recipient}'. "
                        f"Requestor: '{task.requestor}'. "
                        f"Task description: '{task.task_description}'."
                    )
                    message = await self._agents_client.messages.create(
                        thread_id=self._agent_thread.id,
                        role="user",
                        content=task.task_description,
                    )
                    print(f"Created message with ID: {message.id} for task in thread {self._agent_thread.id}")
                    agent = self._get_member_by_name(task.recipient)
                    if agent and agent.agent_instance:
                        run = await self._agents_client.runs.create_and_process(
                            thread_id=self._agent_thread.id, agent_id=agent.agent_instance.id
                        )
                        print(f"Created and processed run for agent '{agent.name}', run ID: {run.id}")
                        text_message = await self._agents_client.messages.get_last_message_text_by_role(
                            thread_id=self._agent_thread.id, role=MessageRole.AGENT
                        )
                        if text_message and text_message.text:
                            print(f"Agent '{agent.name}' completed task. Outcome: {text_message.text.value}")
                            if self._current_task_span is not None:
                                self._add_task_completion_event(self._current_task_span, result=text_message.text.value)

                    if not self._tasks and not task.recipient == "TeamLeader":
                        team_leader_request = self.TEAM_LEADER_TASK_COMPLETENESS_CHECK_INSTRUCTIONS
                        _create_task(
                            team_name=self.team_name,
                            recipient=self._team_leader.name,
                            request=team_leader_request,
                            requestor="user",
                        )
                    self._current_task_span = None
            self._current_request_span = None

    def _get_member_by_name(self, name) -> Optional[_AgentTeamMember]:
        """
        Retrieve a team member (agent) by name.
        If no member with the specified name is found, returns None.

        :param name: The agent's name within this team.
        """
        if name == "TeamLeader":
            return self._team_leader
        for member in self._members:
            if member.name == name:
                return member
        return None

    async def get_agent(self, agent_id: str) -> Optional[_AgentTeamMember]:
        """
        Given an agent ID, retrieve the agent instance from the Azure client,
        and populate/fill a corresponding _AgentTeamMember instance with attributes from stored JSON.

        This function also updates the AgentTeam's _team_leader or _members accordingly.

        Returns the _AgentTeamMember instance or None if not found.
        """
        if not os.path.exists(self._agent_ids_file):
            return None

        with open(self._agent_ids_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        agents = data.get("agents", {})
        found_name = None
        found_role = None

        for name, info in agents.items():
            if info.get("id") == agent_id:
                found_name = name
                found_role = info.get("role")
                break

        if not found_name or not found_role:
            return None

        try:
            agent_instance = await self._agents_client.get_agent(agent_id)
        except Exception as e:
            print(f"Failed to get agent instance by ID {agent_id}: {e}")
            return None

        team_member = None
        if found_role == "leader" and self._team_leader and self._team_leader.name == found_name:
            team_member = self._team_leader
        else:
            for member in self._members:
                if member.name == found_name:
                    team_member = member
                    break

        if team_member is None:
            default_model = self.TEAM_LEADER_MODEL if found_role == "leader" else ""
            default_instructions = ""
            default_toolset = None
            default_can_delegate = found_role == "leader"

            team_member = _AgentTeamMember(
                model=default_model,
                name=found_name,
                instructions=default_instructions,
                toolset=default_toolset,
                can_delegate=default_can_delegate,
            )
            if found_role == "leader":
                self._team_leader = team_member
            else:
                self._members.append(team_member)

        team_member.agent_instance = agent_instance
        return team_member


"""
Requests another agent in the team to complete a task.

:param span (Span): The event will be added to this span
:param team_name (str): The name of the team.
:param recipient (str): The name of the agent that is being requested to complete the task.
:param request (str): A description of the to complete. This can also be a question.
:param requestor (str): The name of the agent who is requesting the task.
:return: True if the task was successfully received, False otherwise.
:rtype: str
"""


def _add_create_task_event(
    span: Span,
    team_name: str,
    requestor: str,
    recipient: str,
    request: str,
) -> None:

    attributes: Dict[str, Any] = {}
    attributes["agent_team.task.team_name"] = team_name
    attributes["agent_team.task.requestor"] = requestor
    attributes["agent_team.task.recipient"] = recipient
    attributes["agent_team.task.description"] = request
    span.add_event(name=f"agent_team.create_task", attributes=attributes)


def _create_task(team_name: str, recipient: str, request: str, requestor: str) -> str:
    """
    Requests another agent in the team to complete a task.

    :param team_name (str): The name of the team.
    :param recipient (str): The name of the agent that is being requested to complete the task.
    :param request (str): A description of the to complete. This can also be a question.
    :param requestor (str): The name of the agent who is requesting the task.
    :return: True if the task was successfully received, False otherwise.
    :rtype: str
    """
    task = AgentTask(recipient=recipient, task_description=request, requestor=requestor)
    team: Optional[AgentTeam] = None
    try:
        team = AgentTeam.get_team(team_name)
        span: Optional[Span] = None
        if team._current_task_span is not None:
            span = team._current_task_span
        elif team._current_request_span is not None:
            span = team._current_request_span

        if span is not None:
            _add_create_task_event(
                span=span, team_name=team_name, requestor=requestor, recipient=recipient, request=request
            )
    except:
        pass
    if team is not None:
        team.add_task(task)
        return "True"
    return "False"


# Any additional functions that might be used by the agents:
agent_team_default_functions: Set = {
    _create_task,
}


default_function_tool = FunctionTool(functions=agent_team_default_functions)
