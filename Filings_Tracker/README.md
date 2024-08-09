This is a filings tracking bot that uses Telegram Bot to send message to given chat id whenever there is new specified filing.

## Setup

1. (Optional)Create a virtual environment and activate it:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`

2. Install dependencies:
    ```bash
    pip install -r requirements.txt

3. Create a .env file next to tracker.py and add the following variables:
    ```python
    TELEGRAM_CHAT_ID='chat_id_of_the_chat'
    TELEGRAM_TOKEN='bot_token'
    CIK=111111
    ```
    * ID can be found from IDBot(@username_to_id_bot) in Telegram
    * Bot can be created from BotFather(@BotFather) in Telegram
    * CIK is the CIK of the company you want to track(From [Edgar](https://www.sec.gov/), without the first 000)

4. Adjust the FILING_TYPES constant as needed:
    ```python
    FILING_TYPES = {'SC 13D/A', '4', 'SC 13D', '3', 'SC 13G/A'}

5. Run the bot
    ```bash
    python tracker.py