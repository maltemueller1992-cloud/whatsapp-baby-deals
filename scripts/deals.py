import os
import json
from datetime import datetime
import pytz

import gspread
from google.oauth2.service_account import Credentials

# ============================================================
# PHASE 1 (ohne Amazon API):
# Trage hier deine Deals ein (Titel + Preis + Affiliate-Link).
# Der Bot schreibt fertige WhatsApp-Texte in dein Google Sheet.
# ============================================================
DEALS_SOURCE = [
    {
        "title": "Pampers Baby-Dry Monatspaket Gr. 3",
        "price": "45,49€",
        "old_price": "",   # optional, z.B. "59,99€"
        "discount": "",    # optional, z.B. "-24%"
        "link": "https://amzn.to/4sE7IBl"
    },
]

POST_FOOTER_LINE = "📦 Für Baby & Kinderartikel"


def build_post(deal: dict) -> str:
    title = deal.get("title", "").strip()
    price = deal.get("price", "").strip()
    old_price = deal.get("old_price", "").strip()
    discount = deal.get("discount", "").strip()
    link = deal.get("link", "").strip()

    lines = []
    lines.append("👶 Baby-Deal")

    if discount:
        lines.append(f"🔥 {discount} auf {title}")
    else:
        lines.append(f"🔥 {title}")

    if old_price:
        lines.append(f"💰 Jetzt {price} (statt {old_price})")
    else:
        lines.append(f"💰 Jetzt {price}")

    lines.append("")
    lines.append(f"👉 {link}")
    lines.append("")
    lines.append(POST_FOOTER_LINE)

    return "\n".join(lines)


def get_berlin_datetime_str() -> str:
    tz = pytz.timezone("Europe/Berlin")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M")


def open_worksheet():
    sheet_id = os.environ["SHEET_ID"]
    worksheet_name = os.environ.get("WORKSHEET_NAME", "").strip()

    sa_json = os.environ["GOOGLE_SA_JSON"]
    info = json.loads(sa_json)

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    client = gspread.authorize(creds)

    sh = client.open_by_key(sheet_id)
    if worksheet_name:
        return sh.worksheet(worksheet_name)
    return sh.sheet1


def ensure_header(ws):
    header = ["Datum", "Produktname", "Rabatt", "Preis", "Link", "WhatsApp-Text", "ASIN", "Gepostet?"]
    first_row = ws.row_values(1)
    if first_row != header:
        ws.update("A1:H1", [header])


def get_existing_links(ws) -> set:
    values = ws.col_values(5)  # Spalte E = Link
    return set(v.strip() for v in values[1:] if v.strip())


def append_deals(ws, deals):
    existing_links = get_existing_links(ws)
    now_str = get_berlin_datetime_str()

    rows = []
    for d in deals:
        link = d.get("link", "").strip()
        if not link or link in existing_links:
            continue

        title = d.get("title", "").strip()
        discount = d.get("discount", "").strip()
        price = d.get("price", "").strip()
        text = build_post(d)

        rows.append([now_str, title, discount, price, link, text, "", ""])

    if rows:
        ws.append_rows(rows, value_input_option="RAW")
        print(f"✅ {len(rows)} neue Deals ins Sheet geschrieben.")
    else:
        print("ℹ️ Keine neuen Deals (oder alles Duplikate).")


def main():
    ws = open_worksheet()
    ensure_header(ws)
    append_deals(ws, DEALS_SOURCE)


if __name__ == "__main__":
    main()
