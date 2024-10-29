import requests
import pandas as pd
import streamlit as st
import time
import matplotlib.pyplot as plt
import seaborn as sns

# Function to handle API rate limits
def fetch_with_rate_limit(url, params=None):
    response = requests.get(url, params=params)
    
    # If we hit the rate limit, wait and retry
    if response.status_code == 429:
        print("Rate limit exceeded, sleeping for 60 seconds...")
        time.sleep(60)  # Wait for 60 seconds and retry
        response = requests.get(url, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching data: {response.status_code}")
        return None

# Fetch global market data for VSI calculation
def get_global_data():
    global_data = fetch_with_rate_limit("https://api.coingecko.com/api/v3/global")
    
    if global_data and 'data' in global_data:
        return global_data['data']
    else:
        print("Unexpected response structure for global data:", global_data)
        return None

# Fetch market data for a specific tier (1000 tokens per page)
def get_top_tokens(page):
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 1000,  # Get up to 1000 tokens
        "page": page,  # Specify which page to fetch (1 = top 1-1000, 2 = 1001-2000, etc.)
        "sparkline": False,
        "price_change_percentage": "7d,30d"
    }
    tokens = fetch_with_rate_limit("https://api.coingecko.com/api/v3/coins/markets", params=params)
    
    if tokens:
        # Filter out stablecoins and tokens you want to exclude by checking both name and symbol (all lowercase)
        stablecoins = [
            "usdt", "usdc", "dai", "busd", "ust", "first digital usd", 
            "lido staked ether", "weth", "l2 standard bridged weth (base)", 
            "arbitrum bridged weth (arbitrum one)", "arbitrum bridged wbtc (arbitrum one)", 
            "coinbase wrapped btc", "kelp dao restaked eth", "ethereumpow", 
            "ether.fi staked eth", "wrapped steth", "swell ethereum", "jupiter staked sol",
            "bitcoin avalanche bridged (btc.b)", "lombard staked btc", "bridged usdc (polygon pos bridge)",
            "usual usd", "usdd", "paypal usd", "trueusd", "usdb", "marinade staked sol", "wrapped bitcoin",
            "solv protocol solvbtc", "binance staked sol", "solayer staked sol", "cwbtc", "polygon bridged wbtc (polygon pos)",
            "ether.fi staked btc", "tbtc", "usdx.money usdx", "binance-peg dogecoin"
        ]
        
        # Normalize symbols and names to lowercase for comparison
        tokens = [
            token for token in tokens 
            if token['symbol'].lower() not in stablecoins and token['name'].lower() not in stablecoins
        ]
    
    return tokens

# Function to calculate metrics for each token
def calculate_metrics(token, global_data):
    # Calculate PVR (Price-to-Volume Ratio)
    pvr = token['total_volume'] / token['current_price'] if token['current_price'] > 0 else 0
    
    # Ensure that price_change_percentage_7d is not None; use 0 if it's missing or None
    price_change_percentage_7d = token.get('price_change_percentage_7d_in_currency') or 0
    
    # Calculate RVOL (Relative Volume over 7 days)
    rvol = token['total_volume'] / token['market_cap'] if token['market_cap'] > 0 else 0
    
    # Calculate Momentum (Price Momentum over 7 days)
    momentum = price_change_percentage_7d / 100  # Since it's given as a percentage
    
    # Calculate VSI (Volume Share Index)
    global_volume = global_data['total_volume']['usd']
    vsi = token['total_volume'] / global_volume if global_volume > 0 else 0
    
    return {
        'token': token['name'],
        'pvr': pvr,
        'rvol': rvol,
        'momentum': momentum,
        'vsi': vsi
    }

# Function to calculate potential gains from ATH, 7-day price change, and MC/Vol ratio
def calculate_additional_metrics(token):
    # Ensure valid data for all fields, avoid division by zero
    current_price = token['current_price'] if token['current_price'] > 0 else 1
    ath_price = token['ath'] if token['ath'] > 0 else 1
    total_volume = token['total_volume'] if token['total_volume'] > 0 else 1
    market_cap = token['market_cap'] if token['market_cap'] > 0 else 1

    # Calculate Potential Gains (e.g., x2, x5, etc.)
    potential_gains = ath_price / current_price
 
    # 7-Day Price Change
    price_change_7d = token.get('price_change_percentage_7d_in_currency', 0)
 
    # Market Cap to Volume Ratio
    mc_vol_ratio = market_cap / total_volume
 
    return potential_gains, price_change_7d, mc_vol_ratio

# Function to rank tokens based on their metrics
def rank_tokens(tokens_metrics):
    df = pd.DataFrame(tokens_metrics)
    
    # Calculate the average PVR for PVRD (Price-to-Volume Ratio Deviation)
    df['pvrd'] = (df['pvr'] - df['pvr'].mean()) / df['pvr'].mean()
    
    # Scoring system based on SQL query logic
    df['pvr_score'] = df['pvr'].apply(lambda x: 1 if x < df['pvr'].mean() else -1)
    df['rvol_score'] = df['rvol'].apply(lambda x: 1 if x > df['rvol'].mean() else -1)
    df['momentum_score'] = df['momentum'].apply(lambda x: 1 if x < df['momentum'].mean() else -1)
    df['pvrd_score'] = df['pvrd'].apply(lambda x: 1 if x < 0 else -1)
    df['vsi_score'] = df['vsi'].apply(lambda x: 1 if x > df['vsi'].mean() else -1)
    
    # Final score is the sum of individual scores
    df['final_score'] = df[['pvr_score', 'rvol_score', 'momentum_score', 'pvrd_score', 'vsi_score']].sum(axis=1)
    
    # Rank by final score
    df = df.sort_values(by='final_score', ascending=False).head(30)
    
    return df

# Function to visualize the top 30 ranked tokens
def visualize_rankings(ranked_tokens):
    st.write("### Visualization of Top 30 Ranked Tokens")
    
    # Sort by ranking for visualization
    ranked_tokens_sorted = ranked_tokens.sort_values(by="final_score", ascending=False)
    
    # Create a bar plot using Seaborn
    plt.figure(figsize=(10, 6))
    sns.barplot(
        data=ranked_tokens_sorted, 
        x='final_score', 
        y='token', 
        palette='coolwarm'
    )
    
    plt.title("Top 30 Tokens by Final Score")
    plt.xlabel("Final Score")
    plt.ylabel("Token")
    
    # Show the plot in Streamlit
    st.pyplot(plt)

# Main Streamlit app function
def main():
    st.title("🚀 CoinGecko: Final Selector 🔍 | Token Ranking Dashboard 🔥")

    # Add a horizontal line to separate
    st.markdown("---")

    if st.button('Rank All Tiers (Top 3000)'):
        rank_all_tiers()

    # Add a horizontal line to separate
    st.markdown("---")

    # Create 3 buttons for each tier (1-3)
    if st.button('Tier 1 (Top 1-1000)'):
        rank_tier(1)
    if st.button('Tier 2 (1001-2000)'):
        rank_tier(2)
    if st.button('Tier 3 (2001-3000)'):
        rank_tier(3)

    # Add a horizontal line to separate
    st.markdown("---")

    st.title("📊 Token Metrics Overview and Ranking Breakdown 🚀")

    # Explanation for Token Ranking
    with st.expander("📊 What is Final Score?"):
        st.markdown("""
        ### How Are the Tokens Ranked for Final Score?
        This ranking system uses key trading and volume metrics to evaluate tokens across three market cap tiers (Top 1-1000, 1001-2000, and 2001-3000). Each tier of 1000 tokens is analyzed independently, and the top 30 tokens from each tier are ranked based on metrics that emphasize market activity and potential undervaluation.

        1. **Categorizing Tokens by Market Cap**:
           - Tokens are categorized based on their **Market Cap** as provided by CoinGecko. Stablecoins and wrapped assets are excluded.
           - **Tier 1**: Top 1000 tokens by market cap.
           - **Tier 2**: Tokens ranked 1001-2000 by market cap.
           - **Tier 3**: Tokens ranked 2001-3000 by market cap.

        2. **Ranking the Top 30 Tokens**:
           - From each 1000-token tier, we rank the top 30 tokens based on five key metrics that highlight trading activity, momentum, and the relationship between price and volume. These metrics are designed to help identify tokens that may be **undervalued** or experiencing increased interest and market activity.

        ### How Does the Scoring System Work?
        The scoring system combines five key metrics to assess the performance of each token:

        #### 1. **Price-Volume Ratio (PVR)** 
           - **What It Is**: The Price-Volume Ratio (PVR) compares a token's price to its trading volume, indicating how actively a token is traded relative to its price.
           - **Why It Matters**: A **lower PVR** suggests that a token is being traded at higher volumes than its price would suggest, potentially indicating that the token is undervalued. A low PVR score (+1) can signal that the token is actively traded and may present an opportunity for investors looking for undervalued assets.

        #### 2. **Relative Volume (RVOL)**
           - **What It Is**: This metric compares the token's trading volume over the last 24 hours to its average volume over the past 7 days.
           - **Why It Matters**: **Higher RVOL** means that the token has seen increased trading activity compared to its historical average, suggesting growing interest and momentum in the market. A token with an RVOL score of +1 indicates that it is gaining market attention and may be primed for further price action.

        #### 3. **Momentum**
           - **What It Is**: This metric measures price changes over the past 3 days, capturing the short-term momentum of the token.
           - **Why It Matters**: **Positive momentum** indicates that a token's price has been rising, suggesting bullish sentiment. A token with positive momentum (+1) may continue to see upward price movement if interest and demand remain strong.

        #### 4. **PVR Deviation (PVRD)**
           - **What It Is**: PVR Deviation measures how much the token's PVR deviates from the average PVR of all tokens in the tier.
           - **Why It Matters**: A **negative PVRD** score means the token’s PVR is lower than the average, suggesting it is trading more actively relative to its price than its peers. A low PVRD score (+1) highlights tokens that could be undervalued based on their trading activity compared to their price.

        #### 5. **Volume Score Index (VSI)**
           - **What It Is**: VSI measures the token's trading volume in the last 24 hours relative to its historical average volume.
           - **Why It Matters**: A **high VSI** indicates that the token is seeing significantly more trading activity than usual, signaling increasing demand and market attention. A high VSI score (+1) may suggest that the token is positioned for price growth as more traders engage with it.

        ### How to Interpret the Final Score:
        - Each token is scored across these five metrics, resulting in a **composite score** that ranges from **-5** to **+5**.
        - A **+5 score** indicates that the token is performing strongly across all metrics (low PVR, high RVOL, positive momentum, low PVRD, and high VSI), suggesting it may be a highly undervalued or highly active asset.
        - A **negative score** (closer to -5) suggests the token is underperforming across most metrics, which may indicate lower trading interest or weaker market activity.
    
        ### Does This Help Identify Undervalued Assets?
        Yes, this ranking system is designed to highlight tokens that may be **undervalued** based on the relationship between **price** and **trading volume** (via PVR and PVRD). By identifying tokens with **low PVR** and **high trading volume relative to historical averages (RVOL, VSI)**, the system seeks to surface tokens that are seeing increased market attention but may not yet have seen a corresponding increase in price.
    
        This scoring method is particularly useful for traders seeking to discover tokens with rising market interest and activity, as these factors often precede price increases. However, these metrics should be used alongside other forms of analysis to make informed investment decisions.
        """)

    # Additional Dropdown Description for the Additional Metrics
    with st.expander("📊 Explanation of Additional Metrics"):
        st.markdown("""
        ### Additional Metrics Explained
        These additional metrics provide deeper insights into token performance, helping traders identify tokens with strong upside potential, recent momentum, and favorable trading conditions. Here's a breakdown of the metrics:

        #### 1. **Potential Gains from ATH**
        - **What It Is**: Potential Gains is a measure of how far a token's current price is from its **All-Time High (ATH)**.
        - **How It Works**: This metric calculates the multiple by which the current price would need to increase to reach its ATH. For example, a token with a potential gain of **x5** means its current price would need to increase fivefold to reach its ATH.
        - **Why It Matters**: Tokens that are significantly below their ATH may represent **recovery opportunities**, particularly if other metrics (like volume and momentum) are showing strength. Traders often look for tokens with large potential gains as they can signal **undervalued** assets with room for upward price movement.

        #### 2. **7-Day Price Change**
        - **What It Is**: The **7-Day Price Change** measures how much a token's price has fluctuated over the past week.
        - **How It Works**: A positive percentage indicates that the token's price has risen over the past 7 days, while a negative percentage means the price has fallen.
        - **Why It Matters**: Tokens with strong price momentum over a short period can indicate **bullish sentiment** and **increasing demand**. Tracking recent price changes helps traders identify tokens that are gaining attention in the market.

        #### 3. **Market Cap to Volume Ratio (MC/Vol Ratio)**
        - **What It Is**: The **MC/Vol Ratio** compares a token's **market capitalization** (total value of all circulating tokens) to its **trading volume** over the past 24 hours.
        - **How It Works**: A **lower MC/Vol Ratio** means that the token is being traded heavily relative to its market cap, which may indicate strong market interest and liquidity. A higher ratio, on the other hand, suggests lower trading volume compared to market cap, which can signal reduced trading activity.
        - **Why It Matters**: Traders typically prefer tokens with a **low MC/Vol Ratio**, as these tokens are more actively traded relative to their market cap. This could indicate **high liquidity** and **market interest**, which are crucial for short-term trading and price movements.

        #### 4. **Final Score**
        - **What It Is**: The **Final Score** is an aggregated score derived from key metrics such as **PVR**, **RVOL**, **Momentum**, **PVRD**, and **VSI**.
        - **How It Works**: Each of the key metrics contributes to the overall final score. Tokens with a **positive Final Score** indicate they are performing well across multiple dimensions, such as trading volume, price momentum, and potential undervaluation relative to their trading activity.
        - **Why It Matters**: The Final Score provides a **comprehensive view** of a token's overall performance, helping traders identify tokens that may be well-positioned for growth. Tokens with high final scores are likely experiencing strong demand, favorable trading conditions, and may represent **good trading opportunities**.

        ### How to Use These Metrics for Trading Decisions:
        - **Recovery Opportunities**: Look for tokens with high **Potential Gains** from ATH. These may represent recovery opportunities, especially when combined with high volume or momentum.
        - **Momentum Plays**: Tokens with positive **7-Day Price Change** and high **Final Scores** are often trending upward in the market, making them attractive for momentum-based trades.
        - **Liquidity**: Focus on tokens with a **low MC/Vol Ratio**, as these are typically more liquid, meaning there is higher trading activity relative to market cap, making it easier to enter and exit positions.
        - **Multi-Metric Opportunities**: Tokens that appear in multiple categories (e.g., Potential Gains, Price Change, MC/Vol Ratio, and Final Score) may offer the best overall opportunities, as they combine recovery potential, current market interest, and strong trading metrics.

        Together, these metrics give traders a well-rounded perspective on token performance, helping to identify both **short-term opportunities** (e.g., momentum and liquidity) and **long-term potential** (e.g., recovery from ATH).
        """)

# Function to rank a specific tier and calculate additional metrics for all tokens
def rank_tier(tier_number):
    st.write(f"### Ranking Tier {tier_number} (Tokens {tier_number * 1000 - 999} to {tier_number * 1000})")
    
    # Fetch global data for VSI calculation
    global_data = get_global_data()
    
    if global_data:
        # Fetch tokens for the selected tier and calculate metrics
        top_tokens = get_top_tokens(page=tier_number)
        if top_tokens:
            # Calculate main metrics (PVR, RVOL, etc.) for all tokens in the tier
            tokens_metrics = [calculate_metrics(token, global_data) for token in top_tokens]
            
            # Rank tokens based on calculated metrics
            ranked_tokens = rank_tokens(tokens_metrics)
            
            st.write(f"### Top 30 Ranked Tokens for Tier {tier_number} by Final Score")
            st.write(ranked_tokens)
            
            # Visualize the final score ranking for top 30 tokens
            visualize_rankings(ranked_tokens)

            # Now, calculate additional metrics for **all tokens** in the tier
            additional_metrics = []
            for token in top_tokens:  # Loop through all tokens, not just the top 30
                potential_gains, price_change_7d, mc_vol_ratio = calculate_additional_metrics(token)
                additional_metrics.append({
                    "Token": token['name'],
                    "Potential Gains (x)": potential_gains,
                    "7-Day Price Change (%)": price_change_7d,
                    "MC/Volume Ratio": mc_vol_ratio
                })
                    
            # Convert to DataFrame for easy display and visualization
            additional_df = pd.DataFrame(additional_metrics)
            st.write(f"### Tokens with Additional Metrics for Tier {tier_number}")
            st.write(additional_df)

            # Visualize the additional metrics (Top 30 for each metric), now passing both additional_df and ranked_tokens
            visualize_additional_metrics(additional_df, ranked_tokens)  # Ensure both arguments are passed here

        else:
            st.write(f"Failed to fetch token data for Tier {tier_number}.")
    else:
        st.write("Failed to fetch global market data.")

# Function to rank all tiers and calculate additional metrics
def rank_all_tiers():
    st.write(f"### Ranking Top 3000 Tokens (Combining Tier 1, Tier 2, and Tier 3)")

    # Fetch global data for VSI calculation
    global_data = get_global_data()
    
    if global_data:
        all_tokens = []

        # Fetch tokens from Tier 1
        top_tokens_1 = get_top_tokens(page=1)
        if top_tokens_1:
            all_tokens.extend(top_tokens_1)

        # Fetch tokens from Tier 2
        top_tokens_2 = get_top_tokens(page=2)
        if top_tokens_2:
            all_tokens.extend(top_tokens_2)

        # Fetch tokens from Tier 3
        top_tokens_3 = get_top_tokens(page=3)
        if top_tokens_3:
            all_tokens.extend(top_tokens_3)

        if all_tokens:
            # Calculate metrics for all 3000 tokens
            tokens_metrics = [calculate_metrics(token, global_data) for token in all_tokens]
            
            # Rank tokens based on calculated metrics (from 3000 tokens, pick top 30)
            ranked_tokens = rank_tokens(tokens_metrics)
            
            st.write("### Top 30 Ranked Tokens from 3000 Tokens by Final Score")
            st.write(ranked_tokens)
            
            # Now, calculate additional metrics for **all tokens**
            additional_metrics = []
            for token in all_tokens:  # Calculate for all tokens, not just top 30
                potential_gains, price_change_7d, mc_vol_ratio = calculate_additional_metrics(token)
                additional_metrics.append({
                    "Token": token['name'],
                    "Potential Gains (x)": potential_gains,
                    "7-Day Price Change (%)": price_change_7d,
                    "MC/Volume Ratio": mc_vol_ratio
                })
                    
            # Convert to DataFrame for easy display and visualization
            additional_df = pd.DataFrame(additional_metrics)
            st.write("### Additional Metrics for Top 3000 Tokens")
            st.write(additional_df)

            # Now visualize the top 30 tokens for each additional metric separately
            visualize_additional_metrics(additional_df, ranked_tokens)  # Pass both arguments

        else:
            st.write("Failed to fetch token data from one or more tiers.")
    else:
        st.write("Failed to fetch global market data.")

# Function to visualize additional metrics like Potential Gains, 7-Day Price Change, and MC/Vol Ratio
def visualize_additional_metrics(df, ranked_tokens):
    # Plot Potential Gains
    df_sorted = df.sort_values(by="Potential Gains (x)", ascending=False).head(30)
    st.write("### Top 30 Tokens by Potential Gains from Current Price to ATH")
    fig, ax = plt.subplots(figsize=(10, 12))
    sns.barplot(
        data=df_sorted, 
        x="Potential Gains (x)", 
        y="Token", 
        palette='Greens_d',  # Use 'Greens_d' for a darker green gradient
        hue='Token',  
        legend=False
    )
    ax.set_xlabel("Potential Gains (x)")
    ax.set_ylabel("Token")
    ax.set_title("Top 30 Tokens by Potential Gains (x) from Current Price to ATH")
    st.pyplot(fig)

    # Plot Price Change Over 7 Days
    df_sorted_7d = df.sort_values(by="7-Day Price Change (%)", ascending=False).head(30)
    st.write("### Top 30 Tokens by 7-Day Price Change")
    fig_7d, ax_7d = plt.subplots(figsize=(10, 12))
    sns.barplot(
        data=df_sorted_7d, 
        x="7-Day Price Change (%)", 
        y="Token", 
        palette='Blues_d',  # Use 'Blues_d' for a darker blue gradient
        hue='Token',  
        legend=False
    )
    ax_7d.set_xlabel("7-Day Price Change (%)")
    ax_7d.set_ylabel("Token")
    ax_7d.set_title("Top 30 Tokens by 7-Day Price Change")
    st.pyplot(fig_7d)

    # Plot Market Cap to Volume Ratio (Lowest is Best)
    df_sorted_mc_vol = df.sort_values(by="MC/Volume Ratio", ascending=True).head(30)  # Already ascending
    st.write("### Top 30 Tokens by Market Cap to Volume Ratio (Lower is Better)")
    fig_mc_vol, ax_mc_vol = plt.subplots(figsize=(10, 12))
    sns.barplot(
        data=df_sorted_mc_vol, 
        x="MC/Volume Ratio", 
        y="Token", 
        palette='Oranges_d',  # Use 'Oranges_d' for a darker orange gradient
        hue='Token',  
        legend=False
    )
    ax_mc_vol.set_xlabel("MC/Volume Ratio")
    ax_mc_vol.set_ylabel("Token")
    ax_mc_vol.set_title("Top 30 Tokens by Market Cap to Volume Ratio (Lower is Better)")
    ax_mc_vol.invert_yaxis()  # This will show lowest values at the top
    st.pyplot(fig_mc_vol)

    # Now, include Final Score in the selection considerations
    df_sorted_final_score = ranked_tokens.sort_values(by="final_score", ascending=False).head(30)

    # 1. **Tokens appearing in all four categories**
    tokens_in_all_four = (
        set(df_sorted["Token"]).intersection(df_sorted_7d["Token"])
        .intersection(df_sorted_mc_vol["Token"]).intersection(df_sorted_final_score["token"])
    )

    if tokens_in_all_four:
        st.write("### Final Selection Consideration: Tokens Appearing in All Four Categories")
        st.write(f"These tokens appear in the top 30 of Potential Gains, Price Change, MC/Vol Ratio, and Final Score.")
        st.write(tokens_in_all_four)
    else:
        st.write("No tokens appeared in all four categories.")

    # 2. **Tokens appearing in any three of the four categories**
    tokens_in_three = (
        (set(df_sorted["Token"]).intersection(df_sorted_7d["Token"]).intersection(df_sorted_mc_vol["Token"]))
        .union(set(df_sorted["Token"]).intersection(df_sorted_7d["Token"]).intersection(df_sorted_final_score["token"]))
        .union(set(df_sorted_7d["Token"]).intersection(df_sorted_mc_vol["Token"]).intersection(df_sorted_final_score["token"]))
        .union(set(df_sorted["Token"]).intersection(df_sorted_mc_vol["Token"]).intersection(df_sorted_final_score["token"]))
    ).difference(tokens_in_all_four)

    if tokens_in_three:
        st.write("### Tokens Appearing in Three of the Four Categories")
        st.write(f"These tokens appear in the top 30 of any three of the four categories.")
        st.write(tokens_in_three)
    else:
        st.write("No tokens appeared in three categories.")

    # 3. **Tokens appearing in any two of the four categories**
    tokens_in_two = (
        (set(df_sorted["Token"]).intersection(df_sorted_7d["Token"]))
        .union(set(df_sorted["Token"]).intersection(df_sorted_mc_vol["Token"]))
        .union(set(df_sorted["Token"]).intersection(df_sorted_final_score["token"]))
        .union(set(df_sorted_7d["Token"]).intersection(df_sorted_mc_vol["Token"]))
        .union(set(df_sorted_7d["Token"]).intersection(df_sorted_final_score["token"]))
        .union(set(df_sorted_mc_vol["Token"]).intersection(df_sorted_final_score["token"]))
    ).difference(tokens_in_all_four).difference(tokens_in_three)

    if tokens_in_two:
        st.write("### Tokens Appearing in Two of the Four Categories")
        st.write(f"These tokens appear in the top 30 of any two of the four categories.")
        st.write(tokens_in_two)
    else:
        st.write("No tokens appeared in two categories.")

if __name__ == "__main__":
    main()
