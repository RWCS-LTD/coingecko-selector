# 🚀 CoinGecko Token Ranking Dashboard 🔍

This project is a **Streamlit-based dashboard** that ranks cryptocurrency tokens based on custom metrics using data from the **CoinGecko API**. The rankings are organized by market capitalization tiers, and tokens are scored based on metrics that assess trading volume, price activity, and potential undervaluation.

## Features

- Rank tokens in **three tiers** based on market capitalization:
  - **Tier 1**: Tokens ranked 1-1000
  - **Tier 2**: Tokens ranked 1001-2000
  - **Tier 3**: Tokens ranked 2001-3000
- Custom scoring based on the following metrics:
  1. **Price-Volume Ratio (PVR)**
  2. **Relative Volume (RVOL)**
  3. **Momentum**
  4. **PVR Deviation (PVRD)**
  5. **Volume Score Index (VSI)**
- **Additional metrics** such as:
  - Potential Gains from All-Time High (ATH)
  - 7-Day Price Change
  - Market Cap to Volume Ratio (MC/Vol)
- **Visualization** of the top-ranked tokens based on final scores and additional metrics using **Matplotlib** and **Seaborn**.

## Installation

1. **Clone the repository**:

    ```bash
    git clone https://github.com/yourusername/coingecko-ranking-dashboard.git
    cd coingecko-ranking-dashboard
    ```

2. **Install the required dependencies** using `pip`:

    ```bash
    pip install -r requirements.txt
    ```

3. **Run the Streamlit app**:

    ```bash
    streamlit run app.py
    ```

## Requirements

The following Python packages are required and are listed in `requirements.txt`:

- `streamlit`: To create the dashboard interface.
- `requests`: For making API calls to CoinGecko.
- `pandas`: To handle data manipulation.
- `matplotlib`: For visualizing token rankings.
- `seaborn`: For enhanced data visualization.
- `pycoingecko`: For convenient access to CoinGecko's API.

## Usage

- Run the app using the Streamlit command mentioned above.
- You can select the tier to rank tokens (Tier 1, Tier 2, Tier 3) or rank all tiers (Top 3000).
- The dashboard will display the top 30 ranked tokens based on the final score.
- Additional metrics, such as Potential Gains, 7-Day Price Change, and Market Cap to Volume Ratio, are also available for deeper insights.

## CoinGecko API

This app fetches data from the [CoinGecko API](https://www.coingecko.com/en/api). Ensure that you respect the API's rate limits. A rate-limiting mechanism has been implemented in the `fetch_with_rate_limit()` function to handle `429 Too Many Requests` errors.

## License

This project is licensed under the MIT License. See the `LICENSE` file for more details.
