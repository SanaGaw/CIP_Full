# Collective Intelligence Platform v2 (CIP v2)

This repository contains a pilot implementation of the Collective Intelligence Platform (CIP) version 2. The goal of CIP is to enable cross‑functional groups to deliberate on complex organizational questions through a structured, multi‑phase process. Participants contribute anonymously, ideas are extracted and clustered, tensions are surfaced, and a structured advisory report is produced at the end.

## Architecture

The application is built using **Python 3.11**, **FastAPI**, **WebSockets**, and **SQLite**. A tiered LLM router abstracts multiple providers (Anthropic, OpenRouter, Gemini, Groq) and local NLP components (spaCy, sentence‑transformers, scikit‑learn) handle idea extraction, clustering and diversity metrics. Observability is built in via a structured trace system.

This pilot focuses on debuggability and observability over feature completeness. Many components are stubs that log their actions rather than implementing the full logic described in the build specification.

## Getting Started

1. Clone this repository and navigate into the `cip_v2` directory.
2. Copy `.env.example` to `.env` and set any API keys or secrets as needed.
3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Run the application:

   ```bash
   uvicorn cip.main:app --reload
   ```

5. Open your browser at `http://localhost:8000` to verify the API is running.

## Project Structure

- `cip/` – core application code (configuration, database, agents, engines, NLP, etc.)
- `tests/` – pytest-based unit tests
- `static/` – minimal CSS and JavaScript assets
- `templates/` – Jinja2 HTML templates for admin, facilitator, participant and replay views
- `.env.example` – sample environment configuration
- `Dockerfile` – container definition for deployment
- `railway.toml` – deployment configuration for Railway

## Limitations

This pilot does not implement the full functionality described in the build prompt. Many modules contain placeholder functions or stubs that should be replaced with real logic. The LLM clients return stub responses; bridging and orchestrator logic are highly simplified; UI templates are placeholders. Use this project as a starting point for further development.

## License

This project is provided as-is for demonstration purposes.