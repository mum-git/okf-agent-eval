#!/usr/bin/env python3
"""Call llama-server directly, print response to stdout, token usage to stderr."""

import json
import sys
import urllib.request

LLAMA_URL = "http://127.0.0.1:1234/v1/completions"

prompt = sys.stdin.read()

payload = json.dumps({
    "model": "llama",
    "prompt": prompt,
    "max_tokens": 4096,
    "temperature": 0.6,
    "top_p": 0.95,
    "top_k": 20,
    "min_p": 0,
}).encode()

req = urllib.request.Request(LLAMA_URL, data=payload, headers={"Content-Type": "application/json"})

try:
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = json.loads(resp.read())
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)

text = data["choices"][0]["text"]
usage = data.get("usage", {})
total = usage.get("total_tokens", 0)

sys.stdout.write(text)
sys.stdout.flush()
print(f"tokens used: {total}", file=sys.stderr)
