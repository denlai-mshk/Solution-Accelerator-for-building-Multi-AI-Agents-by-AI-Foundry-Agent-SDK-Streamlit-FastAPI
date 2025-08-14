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
For collecting the **APPLICATIONINSIGHTS_CONNECTION_STRING**. You have to setup Log Analytic Workspace and Application Insight to your AI Foundry resource. And then you come back to AI Foundry workspace, locate your project, Left menu **Tracing / Monitoring**, set the data source to your Application Insight. Then you will have the InstrumentationKey for that connection string.

Leave the **ENTRY_AGENT_ID** be empty at this moment. You will have this agent id on step 9

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
Check the **TeamLeader** agent id from **\config\MULTIAGENT-DEMO_agent_ids.json** and fill this agent id in **.env**

ENTRY_AGENT_ID=asst_xxxxxxxxxxxxxxxxxxxxxxxx

## Testing
Check your browser that showing the streamlit GUI, send the sample question or say hi



# Deploy to App Service

### Step 1:Create App service plan(linux)

### Step 2:Create App service (web app) - Python 3.12

### Step 3:Fill Environmental Variables
```
PROJECT_ENDPOINT=https://xxxxxxxxxxxx.services.ai.azure.com/api/projects/yyyyyyyyyyyyyy
ENTRY_AGENT_ID=asst_xxxxxxxxxxxxxxxxxxxxxxxx
SCM_DO_BUILD_DURING_DEPLOYMENT=true
MODEL_DEPLOYMENT_NAME=gpt-4o
AZURE_TRACING_GEN_AI_CONTENT_RECORDING_ENABLED=true
AGENT_TEAM_NAME=xxxxxxxxxxx
APPLICATIONINSIGHTS_CONNECTION_STRING=xxxxxxxxxxxxxxxxxx
```

Check the TeamLeader agent id from **\config\MULTIAGENT-DEMO_agent_ids.json** and fill this agent id in **.env**

ENTRY_AGENT_ID=asst_xxxxxxxxxxxxxxxxxxxxxxxx

### Step 4:Use Visual Studio Code - Azure Extension to deploy the backend app
1. Open a new Visual Studio Code for \backend as project root
2. Switch to Azure extension from left menu
3. Workspace > click agenticbackend > click the Azure App Service icon next to the WOKRSPACE
4. Select your subscription and resource group that contains your App Service Web App created from Step 2
5. Confirm overwrite the App Service, wait till the deployment finish

### Step 5:Fill Startup script & Restart
put this in azure portal , or use azure cli to update the app configuration
```
gunicorn -w 2 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 main:app
```
![startupscript](/backend/startupscript.jpg)

https://learn.microsoft.com/en-us/azure/app-service/quickstart-python?tabs=fastapi%2Cwindows%2Cazure-cli%2Cazure-cli-deploy%2Cdeploy-instructions-azportal%2Cterminal-bash%2Cdeploy-instructions-zip-azcli

or use Azure Cli

```
az webapp config set --startup-file "gunicorn -w 2 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 main:app" --name $APP_SERVICE_NAME --resource-group $RESOURCE_GROUP_NAME

az webapp restart --name $APP_SERVICE_NAME --resource-group $RESOURCE_GROUP_NAME
```
### Step 6: Enable App Service System Identity

### Step 7: Grant Role "AI User" to App Service System Identity against AI foundry resource

# Prompt Engineering
Study both yaml files to learn how the prompt instructions for steering the user query by multi ai agents collaboration.
```
\config\agent_team_config.yaml
\config\agentmember_instruction.yaml
```

## References
[azure-sdk-for-python sample](https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/ai/azure-ai-agents/samples/agents_multiagent/sample_agents_multi_agent_team.py)





