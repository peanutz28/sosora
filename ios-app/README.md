# SOSora iOS → Command

The app defaults to **http://192.168.68.80:8000**, this laptop’s LAN IPv4 address
when configured. Connect the phone and laptop to the same Wi-Fi. If DHCP changes
the address, run `ipconfig getifaddr en0` on the Mac and edit the server address in
the app’s Sync settings. A previously saved address must be changed there too.
Allow local network access when iOS asks. The demo Info.plist permits HTTP so a
numeric LAN address works without TLS. Simulator users can use
`http://127.0.0.1:8000`.

From the repository root, with backend requirements installed:

```sh
cd backend
DEMO_MODE=true uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Run the Command dashboard in `frontend/` using its normal development command.
Its API must point at the same Command process. Open the Xcode project in this
folder, choose your signing team and phone, then build and run.

Use Sync’s connection check, submit an SOS with coordinates, and check the Command
dashboard: the incident is stored in Command and broadcast over `/ws/events`, so
it appears as a map pin. Retries use `client_id` to avoid duplicate incidents.
Do not reset or seed the scenario after submitting: those actions clear incidents.
This is a demonstration app, not an emergency service.

The app uses `/api/health`, `/api/mobile/state`, `/api/road-segments`,
`POST /api/incidents`, `PATCH /api/incidents/{id}`, and `/api/road-reports`.
Command’s existing `/api/state` and incident response envelope remain available.
Road reports use catalog IDs, become responder radio evidence, and run the agent’s
segment-status, trust-rule and reachability tools on the selected road (both travel
directions where present). No language/location guessing is needed for structured
reports. A passable report is unverified and cannot reopen a blocked road. Photos
stay on the phone. Requests allow up to 120 seconds for Command processing.
