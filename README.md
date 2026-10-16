# Project Apex-01 – Motorsport Telemetry & Data Acquisition System

A modular telemetry platform for simulated (and future physical) motorsport data acquisition, processing, and real‑time visualization. The repository contains a FastAPI backend, a Vite/React frontend, and tooling for simulated telemetry data.

## Secret handling

- **No hard‑coded credentials** are present in the source code. All secret values (API keys, database URLs, etc.) must be provided via environment variables.
- A template file **`.env.example`** is included in the repository. Copy it to `.env` and fill in the actual values required for your deployment:
  ```
  cp .env.example .env
  # edit .env with real values
  ```
- The real `.env` file is excluded from version control by the project's `.gitignore` to prevent accidental leakage.
- When deploying (e.g., to Vercel or a local environment), ensure the required variables are supplied through the platform’s environment‑variable configuration.

## Getting started

*(Further setup instructions omitted for brevity – see the full README for detailed installation, testing, and deployment steps.)*
