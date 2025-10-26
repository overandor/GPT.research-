# CHAMP-LM Research Platform

This repository contains a modular research orchestration engine for running continuous novelty discovery rounds with large language model ensembles.

## Features
- Resilient streaming layer with circuit breakers and health metrics
- KPI engines tracking novelty, impact, and publication readiness
- LLM orchestrator with parallel request handling and retry logic
- Prometheus-based monitoring and health inspection APIs
- Dockerized deployment with optional local model backends

## Development
Install dependencies and run the test suite:

```bash
pip install -r requirements.txt
pytest
```

To start the full stack:

```bash
docker-compose up --build
```
