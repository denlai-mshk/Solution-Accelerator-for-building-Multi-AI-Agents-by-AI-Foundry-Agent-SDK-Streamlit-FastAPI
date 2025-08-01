# Local host for testing

### Step 1: Fill Environmental Variables in .env
```
PROJECT_ENDPOINT=https://xxxxxxxxxxxx.services.ai.azure.com/api/projects/yyyyyyyyyyyyyy
ENTRY_AGENT_ID=asst_xxxxxxxxxxxxxxxxxxxxxxxx
SCM_DO_BUILD_DURING_DEPLOYMENT=true
MODEL_DEPLOYMENT_NAME=gpt-4o
AZURE_TRACING_GEN_AI_CONTENT_RECORDING_ENABLED=true
AGENT_TEAM_NAME=xxxxxxxxxxx
APPLICATIONINSIGHTS_CONNECTION_STRING=xxxxxxxxxxxxxxxxxx
```
### Step 2: open terminal (command prompt)
### Step 3:  cd backend
### Step 4 (run once at 1st time): \backend> python -m venv venv
### Step 5: \backend> venv\Scripts\activate.bat
### Step 6 (run once at 1st time ): \backend> python -m pip install -r requirements.txt
### Step 7: \backend> python -m main
### Step 8: open terminal 2 (command prompt 2)
### Step 9: Send this curl to setup the agents
```
curl http://localhost:8000/agentsetup
```
Check the TeamLeader agent id from **\config\MULTIAGENT-DEMO_agent_ids.json** and fill this agent id in **.env**

ENTRY_AGENT_ID=asst_xxxxxxxxxxxxxxxxxxxxxxxx

## Testing
Check your browser that showing the streamlit GUI, send the sample question or say hi

# Prompt Engineering
Study both yaml files to learn how the prompt instructions for steering the user query by multi ai agents collaboration.
```
\config\agent_team_config.yaml
\config\agentmember_instruction.yaml
```

## References
[azure-sdk-for-python sample](https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/ai/azure-ai-agents/samples/agents_multiagent/sample_agents_multi_agent_team.py)