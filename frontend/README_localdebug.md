# Local host for testing

### Step 1: Fill Environmental Variables in .env
```
SPEECH_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SPEECHSERVICE_REGION=eastus
AGENTIC_BACKEND=http://localhost:8000/agentteam
SPEECH_LANG=en-US
IS_CLOUD=false
WEBSITES_PORT=8000
```
**remember set IS_CLOUD=false** If you run this script locally with microphone, then set it as false
### Step 2: open terminal (command prompt)
### Step 3:  cd frontend
### Step 4 (run once at 1st time): \frontend> python -m venv venv
### Step 5: \frontend> venv\Scripts\activate.bat
### Step 6 (run once at 1st time ): \frontend> python -m pip install -r requirements.txt
### Step 7: \frontend> streamlit run main.py
### Step 8: Follow the steps in \backend\README_localdebug.md

## Testing
Send this question 

Hello, Please provide me current time in '%Y-%m-%d %H:%M:%S' format, and the weather in New York. Finally, convert the Celsius to Fahrenheit and send an email to Example Recipient with summary of results.



