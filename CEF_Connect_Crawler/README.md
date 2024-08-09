This is a web crawler for cefconnect made to update data for CEF-Paradise.

## Setup

1. (Optional)Create a virtual environment and activate it:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`

2. Install dependencies:
    ```bash
    pip install -r requirements.txt

3. Setup Google service account:
    * Go to [Google Cloud](https://console.cloud.google.com).
    * And create your own project with your own API keys: [Documentation](https://cloud.google.com/iam/docs/service-accounts-create).
    * It needs Google Sheets API and Google Drive API.
    * Place the .json file next to cefs.py.

4. Setup Google Spreadsheet:
    * Add service account's email to the Spreadsheet as editor.
    * Change the constant "SPREADSHEET" in cefs.py from "CEFs" to whatever your spreadsheet is called.
    ```python
    SPREADSHEET = "CEFs"

5. Run the bot
    ```bash
    python cefs.py