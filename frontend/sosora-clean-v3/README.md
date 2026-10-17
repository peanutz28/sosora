# SOSora — final preview v2 (hackathon simulation)

**Not an emergency service.** No real dispatch. Road geometry is illustrative, not a navigable/safety-verified road network. The ML service is not yet connected. Radio hardware is not implemented in this package.

## Run on Mac

Double-click `Start SOSora.command`. If macOS blocks it, right-click → Open; or in Terminal run `bash "Start SOSora.command"`.

Alternatively:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m uvicorn backend.app:app --host 127.0.0.1 --port 8765
```

Dashboard: http://127.0.0.1:8765/  | Resident: http://127.0.0.1:8765/resident  | API docs: http://127.0.0.1:8765/docs

## Gateway contract (for Ria)

The Raspberry Pi **radio receiver code is separate**. When it receives and validates an RF packet, it should durably queue it, then forward to `POST /api/gateway/sos` when it can reach the server. Requests require `X-Gateway-Token` equal to the `SOSORA_GATEWAY_TOKEN` environment variable on the server. The same token must be configured on the gateway. Do not publish the token or expose the service to the public internet without TLS and stronger authentication/rate limiting.

```sh
# Terminal A: run server with a temporary DEMO token
export SOSORA_GATEWAY_TOKEN='replace-with-a-long-random-private-token'
python3 -m uvicorn backend.app:app --host 127.0.0.1 --port 8765

# Terminal B: forward a mock packet as if the radio receiver had received it
export SOSORA_GATEWAY_TOKEN='replace-with-a-long-random-private-token'
python3 gateway/forward_packet.py gateway/example_packet.json
```

The server returns an idempotent acknowledgment; repeat sends with the same `client_id` do not create duplicate incidents. `GET /api/deliveries/{client_id}` returns **server-side receipt**, not proof of RF delivery. Browser SOS and radio SOS are explicitly labeled as different transports. The frontend refreshes incident list periodically.

## Remaining work before public launch

- Real OSMnx road graph and graph-constrained routes; closure review workflow.
- ML service integration against Ria's existing `/ml/*` API (not included here).
- Real ESP32/Pi RF receiver firmware, packet integrity, acknowledgments and queue persistence.
- Secure deployment, authentication, durable production database, rate limits and abuse prevention.
- End-to-end browser/hardware testing on target devices.


## v3 design update
- Compact incident list, larger map, contextual details drawer closed by default.
- Click an incident or Details to reveal its information; close to return to the map.
- All incidents, closures, and candidate routes are simulated.
- SECURITY: This local preview is NOT access-controlled. Do not publish it or enter real SOS details.
- To start: `cd ~/Downloads/sosora-clean-v3 && python3 -m pip install -r requirements.txt && python3 run.py`
- Open http://127.0.0.1:3000/ ; resident page is /resident.
