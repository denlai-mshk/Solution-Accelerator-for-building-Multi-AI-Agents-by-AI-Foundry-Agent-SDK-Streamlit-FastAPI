# Deploy to App Service

### Step 1:Create App service plan(linux)

### Step 2:Create App service (web app) - Python 3.12

### Step 3:Fill Environmental Variables 
```
SPEECH_KEY=xxxxxxxxxxxxxx
SPEECHSERVICE_REGION=eastus
AGENTIC_BACKEND=https://xxxxxx.yyyyyyy.azurewebsites.net/agentteam
SPEECH_LANG=en-US
IS_CLOUD=true
WEBSITES_PORT=8000
SCM_DO_BUILD_DURING_DEPLOYMENT=true
```
**remember set IS_CLOUD=true** keep this value = true in Azure App Service deployment.

### Step 4:Use Visual Studio Code - Azure Extension to deploy the backend app
1. Open a new Visual Studio Code for \backend as project root
2. Switch to Azure extension from left menu
3. Workspace > click voicewebclient > click the Azure App Service icon next to the WOKRSPACE
4. Select your subscription and resource group that contains your App Service Web App created from Step 2
5. Confirm overwrite the App Service, wait till the deployment finish


### Step 5:Fill Startup script & Restart
put this in azure portal , or use azure cli to update the app configuration
```
pip install -r requirements.txt && python -m streamlit run main.py --server.port 8000 --server.address 0.0.0.0

```
![startupscript](/frontend/startupscript.jpg)


or use Azure Cli

```
az webapp config set --startup-file "pip install -r requirements.txt && python -m streamlit run main.py --server.port 8000 --server.address 0.0.0.0" --name $APP_SERVICE_NAME --resource-group $RESOURCE_GROUP_NAME

az webapp restart --name $APP_SERVICE_NAME --resource-group $RESOURCE_GROUP_NAME
```










