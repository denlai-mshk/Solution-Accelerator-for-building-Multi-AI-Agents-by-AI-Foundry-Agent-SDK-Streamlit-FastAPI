import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from azure.ai.projects.aio import AIProjectClient
from azure.identity.aio import DefaultAzureCredential
from azure.ai.agents.models import ListSortOrder
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from utils.agent_query import query_agents
from utils.agent_setup import setup_agents
from dotenv import load_dotenv
load_dotenv()


project_client: AIProjectClient = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global project_client
    project_client = None
    credential = None

    try:
        credential = DefaultAzureCredential()
        endpoint = os.getenv("PROJECT_ENDPOINT", "")
        if not endpoint:
            raise ValueError("PROJECT_ENDPOINT environment variable is required and was not set.")

        project_client = AIProjectClient(endpoint=endpoint, credential=credential)
        await project_client.__aenter__()  # async initialization of the client

        yield  # application runs here

    finally:
        if project_client:
            await project_client.__aexit__(None, None, None)  # async cleanup of client

        if credential:
            await credential.close()  # ensure credential is closed too



app = FastAPI(lifespan=lifespan)

# Allow CORS for frontend Streamlit client
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.get("/ping")
async def ping():
    now = datetime.utcnow()
    timestamp = now.strftime("%y-%m-%d %H:%M:%S")
    return {"ping": timestamp}

class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None  # Optional thread ID to reuse threads


@app.post("/chat")
async def chat_endpoint(chat_req: ChatRequest):
    agents_client = project_client.agents
    agent_id = os.getenv(
        "ENTRY_AGENT_ID",
        ""
    )
    
    if not agent_id:
        raise ValueError("ENTRY_AGENT_ID environment variable is required and was not set.")
    
    agent = await agents_client.get_agent(agent_id)
    print(f"Got agent, agent ID: {agent.id}")

    thread_id = chat_req.thread_id
    if thread_id:
        try:
            thread = await agents_client.threads.get(thread_id=thread_id)
            print(f"Reusing existing thread, thread ID: {thread.id}")
        except Exception as e:
            print(f"Error retrieving thread {thread_id}: {e}. Creating a new thread.")
            thread = await agents_client.threads.create()
            thread_id = thread.id
            print(f"Created new thread, thread ID: {thread.id}")
    else:
        thread = await agents_client.threads.create()
        thread_id = thread.id
        print(f"Created new thread, thread ID: {thread.id}")

    message = await agents_client.messages.create(
        thread_id=thread_id,
        role="user",
        content=chat_req.message
    )

    run = await agents_client.runs.create_and_process(thread_id=thread_id, agent_id=agent.id)

    while run.status in ["queued", "in_progress", "requires_action"]:
        await asyncio.sleep(1)
        run = await agents_client.runs.get(thread_id=thread_id, run_id=run.id)
        print(f"Run status: {run.status}")

    if run.status == "failed":
        print(f"Run failed with error: {run.last_error}")
        return {"response": f"Error: failed to process request (status: {run.status})", "thread_id": thread_id}

    messages = agents_client.messages.list(thread_id=thread_id, order=ListSortOrder.Descending)
    async for msg in messages:
        if hasattr(msg, "text_messages") and msg.text_messages:
            response_text = msg.text_messages[-1].text.value
            print(f"Response: {response_text}")
            return {"response": response_text, "thread_id": thread_id}

    print("No textual message found in response.")
    return {"response": "No response from assistant.", "thread_id": thread_id}

@app.post("/agentteam")
async def agentteam_endpoint(chat_req: ChatRequest):
    # Call query_agents with the user question
    response, thread_id = await query_agents(chat_req.message, chat_req.thread_id, project_client)
    return {"response": response, "thread_id": thread_id}

@app.get("/agentsetup")
async def agentsetup_endpoint():
    await setup_agents(project_client)
    return {"status": "Agent setup completed."}

if __name__ == '__main__':
    uvicorn.run('main:app', host='0.0.0.0', port=8000)
