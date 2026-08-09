#!/bin/bash
# Start the Chiron service, then open the app. Double-click this file.
#
# The app is a client: it talks to the local service over 127.0.0.1 and never
# runs Python itself. That separation is the reason the same binary runs on
# iOS, where spawning a process is not possible.
cd "$(dirname "$0")"
PORT=8765

if curl -sf "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
  echo "Chiron service already running on $PORT."
else
  echo "Starting the Chiron service on $PORT…"
  nohup python3 Chiron/service.py --port "$PORT" > /tmp/chiron-service.log 2>&1 &
  for _ in $(seq 1 20); do
    sleep 0.5
    curl -sf "http://127.0.0.1:$PORT/health" >/dev/null 2>&1 && break
  done
fi

if ! curl -sf "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
  echo "The service did not come up. Log: /tmp/chiron-service.log"
  tail -20 /tmp/chiron-service.log
  read -r -p "Press return to close."
  exit 1
fi

OPS=$(curl -s "http://127.0.0.1:$PORT/v1/capabilities" | python3 -c 'import sys,json;print(len(json.load(sys.stdin)["result"]["operations"]))')
echo "Service up: $OPS operations at http://127.0.0.1:$PORT"
echo "Opening Chiron…"
open build/Chiron.app
echo
echo "In the app: gear icon -> endpoint http://127.0.0.1:$PORT -> Done."
echo "Then use the Workbench tab."
