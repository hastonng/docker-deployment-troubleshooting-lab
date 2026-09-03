# Docker Deployment Troubleshooting Lab

A small, real (not toy) demo of how I diagnose and fix container
deployment problems — built as a case study, not a tutorial.

> Replace `hastonng` below with your actual GitHub username once
> the repo is pushed, so the CI badge and links resolve.

[![CI](https://github.com/<github-username>/docker-deployment-troubleshooting-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/<github-username>/docker-deployment-troubleshooting-lab/actions/workflows/ci.yml)

## What this is

A working Flask API (`task-tracker-api`) — small enough to read in five
minutes, real enough to actually break in the ways production services
break. Around it:

- a **Dockerfile** with a proper health check, non-root user, and correct
  network binding
- an **automated test suite** (pytest)
- a **CI/CD pipeline** (GitHub Actions) that runs the tests, builds the
  image, and smoke-tests it by waiting for the container to report
  healthy and curling it from outside — not just checking that it started
- **three deliberately broken deployment scenarios**, each with the exact
  symptom you'd see, the diagnostic commands used to isolate the root
  cause, the fix, and how to verify it — written up as case studies in
  [`broken-deployment/`](broken-deployment/)
- a general-purpose [**troubleshooting runbook**](docs/runbook.md) for
  this class of problem, not just these three examples

## Why I built it this way

Anyone can claim "I fix Docker and deployment problems." This repo is the
evidence: three real, common failure modes, each broken on purpose,
diagnosed the same way I'd diagnose them on a client's actual system, and
fixed with a verifiable before/after — not just described.

| Scenario | Symptom | Root cause |
|---|---|---|
| [1 — Unreachable app](broken-deployment/scenario-1-unreachable-app/) | Container is "Up", port is published, nothing answers from the host | App bound to `127.0.0.1` instead of `0.0.0.0` inside the container |
| [2 — False "unhealthy"](broken-deployment/scenario-2-false-unhealthy/) | App works fine, but `docker ps` reports it unhealthy | Health check left pointing at a stale port after the app moved to a new one |
| [3 — Crash loop](broken-deployment/scenario-3-crash-loop/) | Container starts, crashes, restarts, repeats | A config value copy-pasted from `docker inspect` *output* used as env *input* |

## Running it

```bash
# Run the working version
docker compose up --build
curl http://localhost:8080/health
curl http://localhost:8080/tasks

# Run the tests
pip install -r app/requirements-dev.txt
pytest tests/ -v

# Reproduce a broken scenario (example: scenario 1)
docker build -f broken-deployment/scenario-1-unreachable-app/Dockerfile.broken -t demo:broken1 .
docker run -d -p 8080:8080 --name demo1 demo:broken1
curl http://localhost:8080/health   # fails — see the scenario README for the full diagnosis
```

## Stack

Python (Flask, gunicorn) · Docker · Docker Compose · GitHub Actions · pytest

## About

I'm Haston, a Cloud Reliability & DevOps engineer based in Kuala Lumpur. I
help small software teams (startups, agencies, SaaS teams of ~5–30 devs)
troubleshoot AWS, Docker, Linux and CI/CD problems, and make their
deployments more reliable — usually as fixed-scope engagements rather than
retainers. This repo is representative of that work, done on my own time
against a system I control end-to-end.
