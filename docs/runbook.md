# Docker Deployment Troubleshooting Runbook

A general checklist for diagnosing "it's deployed but something's wrong"
issues with a containerized app, in the order that actually narrows the
problem fastest. Written for the three scenarios in this repo, but the
method generalizes to most real client tickets.

## Step 0 — Reproduce and observe, before touching anything

```
docker ps -a                        # is it running, restarting, or exited?
docker inspect <container>          # full config: ports, env, health check, mounts
docker logs <container> --tail 100  # recent output — the single highest-value command
```

These three commands answer 80% of "what's wrong" before any deeper
investigation. Resist the urge to start changing config before running
them.

## Step 1 — Is the process crashing, or is it running but unreachable?

- **Status cycles between `Restarting` / `Exited`** → it's crashing. Go
  straight to the logs (`docker logs`) — the traceback or error is almost
  always right there. See [scenario 3](../broken-deployment/scenario-3-crash-loop/).
- **Status is `Up` (or `Up (unhealthy)`) but nothing responds** → it's a
  networking or health-check problem, not a crash. Continue below.

## Step 2 — For "running but unreachable": test from inside first

```
docker exec <container> curl -s http://localhost:<port>/health
```

- **Works from inside, fails from the host** → almost always a bind
  address problem (`127.0.0.1` instead of `0.0.0.0`). Check with
  `docker exec <container> ss -tlnp`. See [scenario 1](../broken-deployment/scenario-1-unreachable-app/).
- **Fails from inside too** → the app itself isn't listening where you
  expect. Check the actual port with `ss -tlnp` inside the container and
  compare it to what's `EXPOSE`d and published.

## Step 3 — For "app works but Docker reports unhealthy"

```
docker inspect <container> --format '{{json .Config.Healthcheck}}'
```

Read the exact command Docker is running on a timer, and run it manually
with `docker exec`. A container's health status only ever reflects the
health check *as configured* — it can drift from reality after a port,
path, or route change that nobody updated the check to match. See
[scenario 2](../broken-deployment/scenario-2-false-unhealthy/).

## Step 4 — Environment and configuration sanity check

```
docker inspect <container> --format '{{json .Config.Env}}' | python3 -m json.tool
docker compose config          # if using Compose — shows fully resolved values
```

Look especially for values that look like they were copy-pasted from
`docker inspect`/`docker ps` *output* (e.g. `8080/tcp`, `unix:///var/run/...`)
rather than typed as plain config *input*. See [scenario 3](../broken-deployment/scenario-3-crash-loop/).

## Step 5 — Resource and platform checks (when the above don't explain it)

```
docker stats --no-stream <container>     # CPU/memory — OOMKilled shows in `docker inspect` State
docker inspect <container> --format '{{.State.OOMKilled}}'
docker system df                          # disk pressure
uname -m && docker inspect <image> --format '{{.Architecture}}'   # arch mismatch (arm64 vs amd64)
```

## Step 6 — CI/CD-specific checks

If the app is fine locally but breaks only through the pipeline:

- Confirm the pipeline builds the **same Dockerfile** the team runs
  locally (no silent divergence between a "local" and "CI" Dockerfile).
- Confirm the pipeline **waits for health**, not just for the container to
  start, before treating a deploy as successful — `docker ps` reporting
  "Up" is not the same as the app being ready. This repo's own
  [`ci.yml`](../.github/workflows/ci.yml) polls health status explicitly
  for this reason.
- Check for environment differences: secrets/env vars present locally but
  missing in CI (or vice versa), and registry auth/rate-limit failures
  that look like build failures but are actually pull failures.

## General principles this runbook follows

1. **Logs before network before config** — cheapest signal first.
2. **Inside the container before outside it** — isolates app-level issues
   from Docker networking/orchestration issues.
3. **Read the actual resolved config** (`docker inspect`, `compose config`),
   never assume it matches the file on disk — templating, env
   substitution, and stale images are common sources of drift.
4. **Every fix gets verified**, not just applied — see each scenario's
   "Verify the fix" section for the exact command that proves it.
