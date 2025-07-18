import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import os

base_dir = os.path.dirname(os.path.abspath(__file__))
SERVICE_ACCOUNT_FILE = os.path.join(base_dir, 'creds', 'dauntless-water-409404-a2aaae9a477f.json')

def safe_decode_unicode(text):
    if isinstance(text, str) and r'\u' in text:
        try:
            return text.encode().decode('unicode_escape')
        except:
            return text
    return text


def get_google_sheet():
    SERVICE_ACCOUNT_FILE = 'dauntless-water-409404-a2aaae9a477f.json'
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"  # ← 추가
    ]
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)
    spreadsheet = client.open("마약성 진통제 PK 정리본")
    worksheet = spreadsheet.worksheet("그래프데이터")
    data = worksheet.get_all_values()
    df = pd.DataFrame(data[1:], columns=data[0])  # 첫 줄은 컬럼명으로
    df['drug_name'] = df['drug_name'].apply(safe_decode_unicode)

    return df




