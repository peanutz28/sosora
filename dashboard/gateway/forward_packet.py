"""Raspberry Pi gateway HTTP forwarder example. Does not receive radio packets itself.
Set SOSORA_GATEWAY_TOKEN and SOSORA_API_URL. Call with a JSON file created by your RF receiver.
"""
import json, os, sys, urllib.request
from pathlib import Path
if len(sys.argv)!=2:
    raise SystemExit('Usage: python3 gateway/forward_packet.py packet.json')
packet=json.loads(Path(sys.argv[1]).read_text())
url=os.getenv('SOSORA_API_URL','http://127.0.0.1:8765').rstrip('/')+'/api/gateway/sos'
token=os.getenv('SOSORA_GATEWAY_TOKEN')
if not token:raise SystemExit('Set SOSORA_GATEWAY_TOKEN; never commit it to Git')
request=urllib.request.Request(url,data=json.dumps(packet).encode(),headers={
    'Content-Type':'application/json','X-Gateway-Token':token},method='POST')
with urllib.request.urlopen(request,timeout=12) as response:
    print(response.read().decode())
