# Scenario 1 — Container is "Up" but unreachable from the host

## Symptom

```
$ docker build -f broken-deployment/scenario-1-unreachable-app/Dockerfile.broken -t demo:broken1 .
$ docker run -d -p 8080:8080 --name demo1 demo:broken1
$ docker ps
CONTAINER ID   IMAGE          STATUS         PORTS
a1b2c3d4e5f6   demo:broken1   Up 5 seconds   0.0.0.0:8080->8080/tcp

$ curl http://localhost:8080/health
curl: (56) Recv failure: Connection reset by peer
```

The container is reported healthy and running by Docker, the port mapping
looks correct, but every request from the host times out or is reset. This
is the single most common "it deployed fine but nothing works" ticket in
this kind of engagement.

## Diagnosis

1. **Confirm the process is actually running inside the container** — rule
   out a crash:
   ```
   docker logs demo1
   docker exec demo1 ps aux
   ```
   The app process is present and shows no errors. So it's not a crash —
   it's a networking problem.

2. **Test from inside the container itself:**
   ```
   docker exec demo1 curl -s http://localhost:8080/health
   ```
   This **succeeds**. That's the key diagnostic signal: the app works when
   reached from its own network namespace, but not from outside it. That
   narrows the problem to which interface the process is bound to.

3. **Check what the process is actually listening on:**
   ```
   docker exec demo1 python -c "import socket; print(socket.gethostbyname(socket.gethostname()))"
   docker exec demo1 ss -tlnp
   ```
   `ss -tlnp` shows the process bound to `127.0.0.1:8080`, not `0.0.0.0:8080`.
   That's the root cause: Docker's `-p 8080:8080` maps the host port to the
   container's external interface, but a process listening only on the
   loopback interface (`127.0.0.1`) never receives traffic that arrives via
   that mapping — only traffic that originates *inside* the container's own
   network namespace (like the `docker exec curl` above) reaches it.

## Root cause

`app.run(host='127.0.0.1', port=8080)` in the broken Dockerfile's `CMD`
binds Flask's dev server to the loopback interface only.

## Fix

Bind to `0.0.0.0` so the process accepts connections on every interface,
including the one Docker's port mapping forwards to:

```diff
- CMD ["python", "-c", "from app import app; app.run(host='127.0.0.1', port=8080)"]
+ CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "app:app"]
```

(The production `Dockerfile` in the repo root already does this — see
`app/app.py`'s own comment on the same mistake.)

## Verify the fix

```
docker exec demo1 ss -tlnp | grep 8080     # now shows 0.0.0.0:8080
curl http://localhost:8080/health          # now returns 200
```

## Takeaway for clients

"It's listening on the wrong interface" and "it crashed" produce an
identical symptom from the outside (nothing answers). The fast way to tell
them apart is always the same: check from *inside* the container first.
