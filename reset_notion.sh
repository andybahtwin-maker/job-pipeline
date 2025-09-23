#!/usr/bin/env bash
set -euo pipefail
ROOT=~/applypilot
VENV=$ROOT/.venv-applypilot
ENVFILE=$ROOT/.env

. "$VENV/bin/activate"
python -m pip install --quiet --upgrade notion-client python-dotenv pandas

export $(grep -E '^(NOTION_TOKEN|NOTION_PAGE_ID)=' "$ENVFILE" | xargs)

python3 - <<'PY'
import os
import pandas as pd
from notion_client import Client
from dotenv import load_dotenv
from pathlib import Path

ROOT = Path.home()/"applypilot"
load_dotenv(ROOT/".env", override=True)

tok = os.environ["NOTION_TOKEN"]
pid = os.environ["NOTION_PAGE_ID"]

cli = Client(auth=tok)

# 1. Create (or reuse) a database under the page
db = cli.databases.create(
    parent={"type":"page_id","page_id":pid},
    title=[{"type":"text","text":{"content":"Job Listings"}}],
    properties={
        "Title":{"title":{}},
        "Company":{"rich_text":{}},
        "Location":{"rich_text":{}},
        "Source":{"rich_text":{}},
        "Date":{"date":{}},
    },
)
print("[ok] Database created:", db["id"])
print("👉 Save this as NOTION_DATABASE_ID in applypilot/.env")
PY
