## Core Architecture

- **Web Framework:** FastAPI for RESTful endpoints and WebSocket connections.
- **Database:** Supabase (PostgreSQL) for user profiles, conversational memory, process logs, and vector embeddings.
- **Task Queue & Pub/Sub:** Redis handles asynchronous task delegation between the Client Agent and Orchestrator Agent, as well as WebSocket broadcasting.
- **AI Framework:** OpenAI models power the reasoning agents, intent categorization, and text-to-speech generation.

## Key Features

### Multi-Agent System

- **Client Agent:** Acts as the user-facing interface. It categorizes user intent (Social or Task (Tool Use)), handles general social interactions directly, and dispatches complex tasks.
- **Orchestrator Agent:** A reasoning engine that processes complex tasks, delegates actions to predefined tools, and manages the execution loop until a resolution is reached.

### Route Planning and Predictive Analytics

- **Google Maps Integration:** Computes transit routes and decodes polylines for physical user tracking.
- **Anticip8 Integration:** Generates context-aware travel graphs. It anticipates potential route deviations (e.g., missed stops, physical hazards) based on the user's clinical context, and recalculates probabilities based on preventative interventions.
- **Lost User Management:** Handles coordinate tracking and route recalculation when a user deviates from their physical path.

### Google Workspace Automation

- **OAuth & Token Management:** Manages Google credential lifecycles, database storage, and automatic token refreshing.
- **Gmail Ingestion:** Background workers watch specific inboxes, extract emails, chunk text, generate vector embeddings using SentenceTransformers (gte-small), and upsert data to Supabase.
- **Calendar Management:** Automatically detects appointment intents (New, Reschedule, Cancel), checks calendar Free/Busy status, handles conflicts by requesting user consent, and updates events.

### Tooling Infrastructure

The orchestrator utilizes a strict set of tools to resolve user queries:

- Google Maps Route Calculation
- Anticip8 Route Prediction
- Gmail Outbound Service
- Asynchronous User Interaction

## Project Structure

- `/app/services/client_agent/` - Intent parsing and social interaction logic.
- `/app/services/orchestrator/` - Reasoning engine, tool loop, and memory state management.
- `/app/services/data_interpreter/` - Email processing, embedding generation, and calendar event classification.
- `/app/services/google_services/` - Base clients for Gmail and Google Calendar APIs.
- `/app/services/anticip8/` - Anticip8 prediction models and API wrappers.
- `/app/utils/` - Route graphing, tree plotting, helper functions, and WebSocket Pub/Sub controllers.
- `main.py` - FastAPI entry point and endpoint definitions.
- `exec_file.py` - Background worker daemon processing the Redis task queue.

## Environment Variables Required

To run this application, ensure the following environment variables are configured:

- `SUPABASE_URL`, `SUPABASE_API_KEY`
- `REDIS_HOST`
- `OPENAI_API_KEY`
- `GOOGLE_MAPS_API_KEY`
- `OAUTH_CLIENT2_ID`, `OAUTH_CLIENT2_SECRET`
- `ANTICIP8_KEY`, `ANTICIP8_KEY_SECRET`

## Execution

1. Ensure the Redis instance is running.
2. Start the FastAPI web server.
3. Start the background orchestrator worker (`python exec_file.py`) to process the task queue.
