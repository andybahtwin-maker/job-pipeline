
import json, io
import gspread
from google.oauth2.service_account import Credentials

def push_to_sheet(sheet_id: str, tab: str, rows: list, service_account_json: str):
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    info = json.loads(service_account_json)
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(sheet_id)
    try:
        ws = sh.worksheet(tab)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=tab, rows=1000, cols=20)

    # Prepare header + rows
    header = ["source","job_id","title","company","location","url","tags","description","posted_at"]
    values = [header]
    for j in rows:
        values.append([
            j.source, j.job_id, j.title, j.company, j.location, j.url,
            ", ".join(j.tags), j.description[:500].replace("\n"," "),
            j.posted_at.isoformat() if j.posted_at else "",
        ])

    ws.clear()
    ws.update("A1", values)
