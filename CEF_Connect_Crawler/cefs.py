from requests import utils, get
from bs4 import BeautifulSoup
from time import sleep
import pandas as pd
import gspread
from gspread_dataframe import set_with_dataframe
from os import listdir
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from datetime import datetime, timedelta

# Constants
USER_AGENT = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0'
BASE_URL = "https://www.cefconnect.com"
HEADERS = utils.default_headers()
HEADERS.update({'User-Agent': USER_AGENT})
SPREADSHEET = "CEFs"

MAX_WORKERS = 10  # Adjust based on the rate limit and your system capabilities
# HTML IDs
PRICING_HTML_ID = "ContentPlaceHolder1_cph_main_cph_main_SummaryGrid"
LEVERAGE_HTML_ID = "ContentPlaceHolder1_cph_main_cph_main_ucFundBasics_dvLeverage"
Z_SCORE_HTML_ID = "ContentPlaceHolder1_cph_main_cph_main_ucPricing_ZScoreGridView"
CATEGORY_HTML_ID = "ContentPlaceHolder1_cph_main_cph_main_ucFundBasics_dvFB2"
# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

def get_soup(page_content):
    return BeautifulSoup(page_content, "lxml")


def extract_info(soup, key):
    """Extracts the required information from the soup based on the provided key."""
    pricing = soup.find(id=PRICING_HTML_ID).find_next('tr')
    current = pricing.find_next('tr')
    avg = current.find_next('tr')
    high = avg.find_next('tr')
    low = high.find_next('tr')

    leverage_info = soup.find(id=LEVERAGE_HTML_ID)
    try:
        trs = leverage_info.find_all_next('tr')
        target_tr = trs[4]
        leveraged = target_tr.find(class_='right-align').text
    except Exception:
        leveraged = "0.0%"

    z_score = soup.find(id=Z_SCORE_HTML_ID)
    z_score_3m = z_score.find_next(class_='right-align').find_next(class_='right-align')
    z_score_6m = z_score_3m.find_next(class_='right-align')
    z_score_1y = z_score_6m.find_next(class_='right-align')

    category = soup.find(id=CATEGORY_HTML_ID).find(class_='right-align').text

    info_mapping = {
        'Current_SP': current.find_all()[1].text,
        'Current_NAV': current.find_all()[2].text,
        'Current_DP': current.find_all()[3].text,
        'Average_SP': avg.find_all()[1].text,
        'Average_NAV': avg.find_all()[2].text,
        'Average_DP': avg.find_all()[3].text,
        'High_SP': high.find_all()[1].text,
        'High_NAV': high.find_all()[2].text,
        'High_DP': high.find_all()[3].text,
        'Low_SP': low.find_all()[1].text,
        'Low_NAV': low.find_all()[2].text,
        'Low_DP': low.find_all()[3].text,
        'Leveraged': leveraged,
        'Z_Score_3m': z_score_3m.text,
        'Z_Score_6m': z_score_6m.text,
        'Z_Score_1y': z_score_1y.text,
        'Category': category
    }
    return info_mapping.get(key, "")


def fetch_page_content(url):
    """Fetches content of the given URL."""
    try:
        response = get(url, headers=HEADERS)
        response.raise_for_status()
        return response
    except Exception as e:
        logging.error(f"Error fetching URL {url}: {e}")
        return None


def get_page(ticker):
    """Fetches the page content for a given ticker."""
    url = f"{BASE_URL}/fund/{ticker}"
    return fetch_page_content(url)


def get_prev(ticker):
    """Fetches the previous data for a given ticker."""
    url = f"{BASE_URL}/api/v3/pricinghistory/{ticker}/1Y"
    response = fetch_page_content(url)
    return response.json() if response else None


def get_dividend(ticker):
    """Fetches the dividend data for a given ticker."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    url = f"{BASE_URL}/api/v3/distributionhistory/fund/{ticker}/{start_date.strftime('%m-%d-%Y')}/{end_date.strftime('%m-%d-%Y')}"
    response = fetch_page_content(url)
    if response and response.json().get('Data'):
        return response.json()['Data'][0]['TotDiv'], len(response.json()['Data'])
    return "-", 0


def get_tickers():
    """Fetches all available tickers."""
    url = f"{BASE_URL}/api/v3/search/funds"
    response = fetch_page_content(url)
    if response:
        ticker_json = response.json()
        return sorted([item["Ticker"] for item in ticker_json])
    return []


def process_ticker(ticker):
    """Processes a single ticker to fetch and extract required data."""
    page = get_page(ticker)
    if not page:
        return ticker, None
    
    prev_data = get_prev(ticker)
    soup = get_soup(page.content)
    
    data = {
        'Current_SP': extract_info(soup, 'Current_SP'),
        'Current_NAV': extract_info(soup, 'Current_NAV'),
        'Current_DP': extract_info(soup, 'Current_DP'),
        'Average_SP': extract_info(soup, 'Average_SP'),
        'Average_NAV': extract_info(soup, 'Average_NAV'),
        'Average_DP': extract_info(soup, 'Average_DP'),
        'High_SP': extract_info(soup, 'High_SP'),
        'High_NAV': extract_info(soup, 'High_NAV'),
        'High_DP': extract_info(soup, 'High_DP'),
        'Low_SP': extract_info(soup, 'Low_SP'),
        'Low_NAV': extract_info(soup, 'Low_NAV'),
        'Low_DP': extract_info(soup, 'Low_DP'),
        'Leveraged': extract_info(soup, 'Leveraged'),
        'Z_Score_3m': extract_info(soup, 'Z_Score_3m'),
        'Z_Score_6m': extract_info(soup, 'Z_Score_6m'),
        'Z_Score_1y': extract_info(soup, 'Z_Score_1y'),
        'Category': extract_info(soup, 'Category')
    }

    try:
        data['Prev_SP'] = prev_data['Data']['PriceHistory'][-2]['Data']
    except (KeyError, IndexError, TypeError):
        data['Prev_SP'] = "0"

    try:
        data['Prev_NAV'] = prev_data['Data']['PriceHistory'][-2]['NAVData']
    except (KeyError, IndexError, TypeError):
        data['Prev_NAV'] = "0"

    div_amount, quantity = get_dividend(ticker)
    data['Div_Amount'] = div_amount
    if div_amount != "-" and data['Current_SP'] != "":
        try:
            current_sp = float(data['Current_SP'].replace('$', '').replace(',', ''))
            data['Current_Yield'] = float(div_amount) * quantity / current_sp
        except ValueError:
            data['Current_Yield'] = "-"
    else:
        data['Current_Yield'] = "-"

    return ticker, data


def export_cefs_to_sheet(sh):
    """Exports CEF data to the given Google Sheet."""
    tickers = get_tickers()
    results = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_ticker = {executor.submit(process_ticker, ticker): ticker for ticker in tickers}
        for future in as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            try:
                result_ticker, result_data = future.result()
                if result_data:
                    results.append((result_ticker, result_data))
                logging.info(f"Processed {result_ticker}")
            except Exception as e:
                logging.error(f"Error processing ticker {ticker}: {e}")
                continue
            sleep(0.1)  # Sleep to prevent rate limiting

    # Sort results by ticker
    results.sort(key=lambda x: x[0])

    # Prepare data dictionary
    data = {key: [] for key in ["Current_SP", "Current_NAV", "Current_DP", "Average_SP", "Average_NAV", "Average_DP",
                                "High_SP", "High_NAV", "High_DP", "Low_SP", "Low_NAV", "Low_DP", "Leveraged",
                                "Z_Score_3m", "Z_Score_6m", "Z_Score_1y", "Category", "Prev_SP", "Prev_NAV",
                                "Div_Amount", "Current_Yield"]}

    tickers_sorted = []
    for ticker, result_data in results:
        tickers_sorted.append(ticker)
        for key in data.keys():
            data[key].append(result_data[key])

    df = pd.DataFrame(data, index=tickers_sorted)
    df.sort_index(inplace=True)
    set_with_dataframe(sh.sheet1, df, include_index=True)
    sh.sheet1.update_acell('A1', 'Tickers')
    return df


def main():
    try:
        gc = gspread.service_account(filename=[x for x in listdir() if x.endswith('.json')][-1])
        sh = gc.open(SPREADSHEET)
        export_cefs_to_sheet(sh)
    except Exception:
        with open("error.txt", "w") as logf:
            logf.write(traceback.format_exc())
        logging.error("Error saved to file! Exiting.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Process interrupted by user. Exiting.")