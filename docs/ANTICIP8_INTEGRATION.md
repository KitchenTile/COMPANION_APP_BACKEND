# Anticip8 API Integration Guide

## Overview

This document serves as a code-level guide for the Anticip8 engineering team to review the Anticip8 integration. The backend orchestration service uses Anticip8 as the predictive engine for the project.

## Core Integration Files

The integration is primarily isolated within the following backend files:

1. `app/services/anticip8/anticip8_manager.py` - Core API client and request handling.
2. `app/utils/journey_planner.py` - Business logic that formats graph data into Anticip8 payloads.

## Base Configuration & Rate Limiting

**File:** `anticip8_manager.py`
**Class:** `Anticip8RoutePredictor`

- **Headers:** Loaded via environment variables (`ANTICIP8_KEY`, `ANTICIP8_KEY_SECRET`).
- **Rate Limiting Handling:** I implemented a custom `_post_with_backoff` method. This method automatically catches `429 Too Many Requests` errors or throttled responses, parses the "available in X seconds" message, and uses `time.sleep()` to pause execution before retrying.

## Endpoints & Functional Mapping

### 1. Generate Context (`POST /context/`)

- **Purpose:** Initializes the prediction context with the user's clinical/behavioral profile and current travel step.
- **Where it is used:** `journey_planner.py`
- **Trigger Functions:**
  - `anticip8_graph_with_failures()`
  - `anticip8_calculate_new_probability()`
- **Payload Construction:** Before making anticipation calls, the `JourneyPlanner` constructs the context payload using the user's Supabase profile data (`subject_profile_text`), the specific travel node data (`recent_history_text`), and dynamically injected previous events (`triggers_text`).

### 2. Anticipation Prediction (`POST /anticipation/`)

- **Purpose:** Generates failure branches and evaluates probability shifts when preventative interventions are applied.
- **Where it is used:** `anticip8_manager.py`
- **Trigger Function:** `anticip8_call(self, context_id, anticipation_list, anticip8_gen_number)`
- **Implementation Details:**
  - **Risk Generation:** Inside `journey_planner.py` -> `anticip8_graph_with_failures()`, I pass the current route step to `anticip8_call()` and request multiple generated actions (`topn_anticip8_gen_actions = 4`).
  - **Prevention Recalculation:** Inside `journey_planner.py` -> `anticip8_calculate_new_probability()`, I pass the previously generated risks along with the proposed prevention to see how the probabilities change (`topn_anticip8_gen_actions = 1`).
  - **Response Handling:** The `anticip8_call` method extracts the `ranked_anticipations` array and maps the resulting `action` and `probability` floats directly to our `JourneyStepFailure` Pydantic models for graph visualization on the frontend.

### 3. Handling Anticip8 Return Values

**File:** `journey_planner.py`

I handle the `ranked_anticipations` array returned by the API in two distinct ways to build the travel graphs:

- **Mapping Generated Risks:** In `anticip8_graph_with_failures()`, I iterate over the returned `anticip8_failures`. I extract the `action` string and `probability` float, separate the original node from the generated failure nodes, and attach the Anticip8 probabilities to the internal `JourneyStepFailure` models.

- **Filtering Recalculations by Source:** In `anticip8_calculate_new_probability()`, I iterate through the returned probability recalculations. I specifically filter the results to ensure I am only mapping the adjusted probabilities of our known nodes into the `risk_impacts` dictionary, which ultimately dictates the visual weight of the route step.
