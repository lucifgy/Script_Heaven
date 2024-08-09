import os
import time
import traceback
import requests
from random import randint
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# Environment Variables
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
TOKEN = os.getenv('TELEGRAM_TOKEN')
CIK = os.getenv('CIK')

# Constants
LAST_FILE = "last.txt"
FILING_TYPES = {'SC 13D/A', '4', 'SC 13D', '3', 'SC 13G/A'}
AMOUNT_OF_LAST_FILES = 10
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36'
BASE_SEC_URL = 'https://www.sec.gov/Archives/edgar/data/'

def send_msg(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    params = {'chat_id': CHAT_ID, 'text': msg}
    
    for attempt in range(5):
        response = requests.get(url, params=params)
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 1))
            print(f"Rate limited. Retrying in {retry_after} seconds.")
            time.sleep(retry_after)
            continue
        response.raise_for_status()
        return response.json()

    raise requests.exceptions.HTTPError("Exceeded maximum retries for sending message")

def append_to_file(content):
    with open(LAST_FILE, "w") as file:
        file.write(content + "\n")

def read_last_line():
    try:
        with open(LAST_FILE) as file:
            return file.readlines()[-1].strip()
    except FileNotFoundError:
        return ""

def get_(url):
    headers = {'User-Agent': USER_AGENT}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response

def get_filings(cik):
    url = f"https://data.sec.gov/submissions/CIK000{cik}.json"
    return get_(url).json()

def build_link(filing, i):
    return f"{BASE_SEC_URL}{filing['cik']}/{filing['filings']['recent']['accessionNumber'][i].replace('-', '')}/{filing['filings']['recent']['primaryDocument'][i]}"

def process_filings(cik):
    filings = get_filings(cik)
    last_acc_number = read_last_line()

    for i in range(AMOUNT_OF_LAST_FILES):
        accession_number = filings['filings']['recent']['accessionNumber'][i]
        form = filings['filings']['recent']['form'][i]

        if accession_number == last_acc_number:
            append_to_file(filings['filings']['recent']['accessionNumber'][0])
            break

        if form in FILING_TYPES:
            send_msg(f"New {form} Filing!\n\nLink:\n{build_link(filings, i)}")

    time.sleep(randint(5, 20))

def main():
    print("Script started. Press Ctrl + C to exit.")
    while True:
        process_filings(CIK)

if __name__ == "__main__":
    attempt = 0
    max_attempts = 4

    try:
        while attempt < max_attempts:
            try:
                main()
            except KeyboardInterrupt:
                print("Exiting...")
                exit()
            except Exception as e:
                attempt += 1
                print(f"Faulted {attempt}")
                if attempt == max_attempts - 1:
                    try:
                        send_msg("Script Faulted!")
                    except requests.exceptions.HTTPError:
                        print("Failed to send fault message due to rate limiting.")
                    with open("error.txt", "w") as logf:
                        logf.write(traceback.format_exc())
                time.sleep(5)
    except KeyboardInterrupt:
        print("Exiting...")
        exit()
