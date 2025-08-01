# Solution Accelerator for Building Multi AI Agents  
**by AI Foundry Agent SDK + Streamlit + FastAPI**

![cover](/assets/cover.png)

Welcome to this Solution Accelerator repo designed to help you build Multi AI Agents easily using the latest Azure AI Foundry Agent SDK, combined with Streamlit for frontend and FastAPI for backend API. This project aims to simplify your AI agent development journey with a ready-to-use, production-capable codebase.

## Introduction  
With the new [Azure AI Foundry Agent SDK](https://learn.microsoft.com/en-us/azure/ai-foundry/agents/overview), creating AI agents has become simpler and more abstracted. This SDK offers a high-level, easy-to-use framework that might fit your needs better than more complex solutions like Semantic Kernel, which can sometimes be overkill for many use cases. Before diving into Semantic Kernel, give this accelerator a try—it might be just right for your project’s scale and complexity.

## How This Solution Accelerator Speeds Up Your Development

- **Frontend with Streamlit:** A friendly UI client is implemented in Streamlit. It supports local microphone input for voice-enabled questions, making interaction natural and intuitive.
  
- **Backend with FastAPI:** The backend API server uses FastAPI, leveraging its async/await pattern for efficient and scalable asynchronous processing.
  
- **Production Readiness:** Using Robust middleware like `uvicorn`, this base code is production-ready and can be deployed reliably on Azure App Services or similar platforms.

By combining these technologies, you get a smooth developer experience and fast iteration cycles, with modern tools designed for scalability and performance.

## What You Need to Prepare

To run this solution, make sure you have the following prerequisites:

- An **Azure subscription** with owner or contributor permissions.
- An **Azure App Service** to deploy the frontend and backend.
- A **provisioned Azure AI Foundry project** with all necessary resources and the GPT-4o model deployed.
- **Azure Speech Service** if you want to enable local microphone voice input.
- **Application Insight** **Log Analytic Workspace** for AI Agents converationtracking and metrics monitoring
- Development environment ready: **Visual Studio Code** with Azure extensions.
- An **intermediate level of Python programming** experience to customize or extend the solution.

## Positioning Between Semantic Kernel and Agent SDK
![sdklevel](/assets/level.png)
The Semantic Kernel and Agent SDK frameworks are developed to offer developers a powerful yet flexible pathway to build AI applications leveraging large language models (LLMs) and agentic patterns without being overwhelmed by low-level complexity.

The **Agent SDK** is designed as the simpler, easier-to-use interface. It acts as a highly abstracted layer where developers can create and manage AI agents with minimal effort—eliminating the need to directly interact with LLM models, manage conversation histories, or write custom application logic to coordinate between users, agents, or AI search components. This SDK abstracts those complexities, enabling quick development of intelligent agents deployable across multiple platforms and scenarios.

In contrast, the **Semantic Kernel** SDK provides a more powerful but advanced framework. It is designed for developers needing deeper control and customization at the AI Foundry or cloud resource level, supporting complex functionalities such as semantic reasoning, memory management, and intricate orchestration of AI services. While the learning curve is steeper, Semantic Kernel enables sophisticated agent behaviors and workflows beyond the abstractions offered


## High-Level Architecture
![High-Level Architecture](/assets/arch.png)

This solution uses Azure App Services to host:

- **Frontend:** Streamlit app providing the UI for user interaction.
- **Backend:** FastAPI server orchestrating AI agents.

The communication between frontend and backend happens over simple, straightforward REST APIs.

The core magic happens in the backend, where **multi AI agents** are orchestrated:

- The **team leader (orchestrator agent)** manages the lifecycle of the agents.
- The **team members (function-calling agents)** perform specialized tasks.

Using the AI Foundry Agent SDK means you don’t directly have to deal with Azure OpenAI service calls, Cosmos DB, storage, or AI search. All these resources are securely connected through your Azure AI Foundry project with least privilege, letting you focus only on your agent logic and behavior, without worrying about complex security or integration plumbing.

## AI Agent Tracking and Monitoring  

![tracking](/assets/tracking.png)

This repo also demonstrates setting up a full telemetry and monitoring system using:

- **OpenTelemetry**
- **azure monitor opentelemetry**
- **Azure Monitor**
- **Application Insights**
- **Log Analytics Workspace**

Together, these tools provide a holistic environment to track how your multiple AI agents communicate, monitor model usage metrics, and analyze agent conversations in real-time or historically. This visibility allows you to continuously improve the agents’ performance and usage within your AI Foundry workspace.

## Agentic Patterns Demonstrated

Two common agent communication patterns are included as examples:

- **Handoff:** A unidirectional workflow where the team leader passes tasks to team members sequentially.
- **Supervisor:** A bidirectional conversation pattern where the team leader reviews and asserts if the agents' combined outputs fulfill the user’s request by checking task completeness


## References
[azure-sdk-for-python sample](https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/ai/azure-ai-agents/samples/agents_multiagent/sample_agents_multi_agent_team.py)

[Azure AI Agents client library for Python](https://learn.microsoft.com/en-us/python/api/overview/azure/ai-agents-readme?view=azure-python)



