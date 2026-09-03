# Scenario 3 — Container crash-loops on startup

## Symptom

```
$ docker compose -f broken-deployment/scenario-3-crash-loop/docker-compose.broken.yml up
task-tracker-1  | Traceback (most recent call last):
task-tracker-1  |   ...
task-tracker-1  | ValueError: invalid literal for int() with base 10: '8080/tcp'
task-tracker-1 exited with code 1
task-tracker-1  | Traceback (most recent call last):
...
```

The container starts, immediately crashes with a Python traceback, gets
restarted by the `restart` policy, crashes again, and repeats — the
textbook crash loop. `docker ps` shows status cycling between `Restarting`
and `Exited`.

## Diagnosis

1. **A crash loop means the process is dying, not hanging** — so the first
   move is always the logs, not the network:
   ```
   docker compose -f broken-deployment/scenario-3-crash-loop/docker-compose.broken.yml logs task-tracker
   ```
   The traceback is right there: `ValueError: invalid literal for int()
   with base 10: '8080/tcp'`, raised while parsing the `PORT` environment
   variable.

2. **Check what value is actually being injected:**
   ```
   docker compose -f broken-deployment/scenario-3-crash-loop/docker-compose.broken.yml config | grep -A2 environment
   ```
   `PORT` is set to the string `"8080/tcp"` — not a plain port number. That
   string shape (`<port>/tcp`) is exactly what `docker inspect` and
   `docker ps` print for exposed ports, which is a strong sign someone
   copy-pasted a value from inspecting a running container into an
   environment variable, rather than reading the actual port number.

## Root cause

`app/app.py` does `int(os.environ.get("PORT", 8080))`. When `PORT` is set
to the malformed string `"8080/tcp"`, that cast raises `ValueError` before
the app can even start listening — so every restart fails identically.

## Fix

```diff
  environment:
-   PORT: "8080/tcp"
+   PORT: "8080"
```

More defensively, the app itself could fail more clearly on a bad `PORT`
value with a one-line validation and an explicit startup error naming the
bad env var — worth calling out to a client as a small hardening follow-up
even after the immediate fix ships.

## Verify the fix

```
docker compose -f broken-deployment/scenario-3-crash-loop/docker-compose.broken.yml up   # after the fix, stays Up
docker compose -f broken-deployment/scenario-3-crash-loop/docker-compose.broken.yml ps    # status: running, not restarting
```

## Takeaway for clients

Crash loops are diagnosed from the logs outward, never the network inward
— `docker logs` (or `compose logs`) first, always. And whenever a
misconfigured value looks suspiciously like it was copied from *output*
(inspect, ps, describe) rather than typed as *input* (a config file, an
env var definition), that's usually exactly what happened.
