# Scenario 2 — App works fine, but Docker reports it "unhealthy"

## Symptom

```
$ docker ps
CONTAINER ID   IMAGE          STATUS
b2c3d4e5f6a7   demo:broken2   Up 2 minutes (unhealthy)

$ curl http://localhost:8080/health
{"status": "healthy", "uptime_seconds": 118.4, ...}   # 200 OK — app is fine
```

The application itself answers correctly on the published port. Docker's
own health status disagrees. In production this is worse than an obvious
crash: orchestrators that gate traffic or restarts on the health status
(ECS target groups, Kubernetes readiness probes, Compose's
`service_healthy` condition) will cycle a working container, causing
intermittent outages that look "random" from the outside.

## Diagnosis

1. **Believe the app, question the probe.** Since curling the published
   port works, the failure has to be in how the *health check itself* is
   defined, not in the app.

2. **Read the health check Docker is actually running:**
   ```
   docker inspect demo2 --format '{{json .Config.Healthcheck}}' | python -m json.tool
   ```
   This prints the exact command Docker runs on a timer, including the URL
   — `http://127.0.0.1:5000/health`. The app is listening on `8080`, not
   `5000`.

3. **Confirm by running the probe command manually:**
   ```
   docker exec demo2 python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health', timeout=2)"
   ```
   This raises a connection error — nothing is listening on 5000 inside the
   container, exactly as the health status implies.

## Root cause

A stale `HEALTHCHECK` left pointing at Flask's historical default port
(5000) after the app was moved to 8080. Nobody re-checked the health check
when the port changed.

## Fix

```diff
  HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
      CMD python -c "import urllib.request,sys; \
-     sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:5000/health', timeout=2).status == 200 else 1)"
+     sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=2).status == 200 else 1)"
```

## Verify the fix

```
docker inspect demo2 --format '{{.State.Health.Status}}'   # now "healthy"
```

## Takeaway for clients

A container's health status is only ever as trustworthy as the check
that produces it. Always `docker inspect` the actual `Healthcheck` config
before assuming a reported "unhealthy" means the application is broken —
the two are decoupled by design, and this is where they most often drift
apart: after a port, path, or environment change that the health check
wasn't updated to match.
