import streamlit as st
import pandas as pd
import requests
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()


database_config = {
        "database": os.environ.get('database'),
        "user": os.environ.get('user'),
        "password": os.environ.get('sql_password'),
        "host": os.environ.get('host'),
        "port": "5432"  
    }
# CoinMarketCap API Key
api_key = "5a80172e-2ab0-4b5d-a773-e606e722472d"

# Function to calculate percentage change
def calculate_percentage_change(prices):
    percentage_changes = []
    for i in range(1, len(prices)):
        change = ((prices[i] - prices[i-1]) / prices[i-1]) * 100
        percentage_changes.append(change)
    return percentage_changes

# Function to create line graph
def create_line_graph(data, title):
    timestamps = data['time_of_scrape']
    prices = data['rate']

    # Calculate percentage change
    percentage_changes = calculate_percentage_change(prices)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=timestamps, y=prices, mode='lines', name=f'{title} Price'))
    fig.update_layout(title=f'{title} Price Fluctuation',
                      xaxis_title='Time',
                      yaxis_title='Price (USD)')
    
    # Find index of highest and lowest percentage changes
    highest_increase_index = percentage_changes.index(max(percentage_changes))
    highest_decrease_index = percentage_changes.index(min(percentage_changes))
    
    # Annotate highest percentage increase
    fig.add_annotation(x=timestamps[highest_increase_index], y=prices[highest_increase_index],
                       text=f'Highest Increase: {percentage_changes[highest_increase_index]:.2f}%',
                       showarrow=True,
                       arrowhead=1)

    # Annotate highest percentage decrease
    fig.add_annotation(x=timestamps[highest_decrease_index], y=prices[highest_decrease_index],
                       text=f'Highest Decrease: {percentage_changes[highest_decrease_index]:.2f}%',
                       showarrow=True,
                       arrowhead=1)
    
    st.plotly_chart(fig)

    return percentage_changes

# Function to fetch data from PostgreSQL table
def fetch_data_from_postgresql(asset_id_base):
    connection = None  # Initialize connection variable
    try:
        connection = psycopg2.connect(
            dbname=os.environ.get('database'),
            user=os.environ.get('user'),
            password=os.environ.get('sql_password'),
            host=os.environ.get('host'),
            port="5432"
        )
        cursor = connection.cursor()

        cursor.execute(f"SELECT time_of_scrape, rate FROM student.domstable WHERE asset_id_base = '{asset_id_base}';")
        rows = cursor.fetchall()
        if rows:
            data = {'time_of_scrape': [], 'rate': []}
            for row in rows:
                data['time_of_scrape'].append(row[0])
                data['rate'].append(row[1])
            # Find highest and lowest prices
            highest_price = max(data['rate'])
            lowest_price = min(data['rate'])
            return pd.DataFrame(data), highest_price, lowest_price
        else:
            st.warning("No data found for the selected cryptocurrency.")
            return pd.DataFrame(columns=['time_of_scrape', 'rate']), None, None  
    except psycopg2.Error as e:
        st.error(f"Error fetching data from PostgreSQL: {e}")
        return pd.DataFrame(columns=['time_of_scrape', 'rate']), None, None 
    finally:
        if connection is not None:
            connection.close()  # Close connection if it's not None

# Function to fetch current price of cryptocurrency from CoinMarketCap
def fetch_current_price_from_coinmarketcap(coin_id):
    url = f"https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest?id={coin_id}"
    headers = {
        "Accepts": "application/json",
        "X-CMC_PRO_API_KEY": api_key,
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if 'data' in data and str(coin_id) in data['data']:
            return data['data'][str(coin_id)]['quote']['USD']['price']
        else:
            return None
    else:
        return None

# Main function
def main():
    st.title('Cryptocurrency Price Analysis')

    # Sidebar navigation
    page = st.sidebar.selectbox("Choose a cryptocurrency", ["Bitcoin (BTC)", "Ethereum (ETH)", "Dogecoin (DOGE)"])

    if page == "Bitcoin (BTC)":
        st.header("Bitcoin Price Analysis")
        st.image('https://upload.wikimedia.org/wikipedia/commons/4/46/Bitcoin.svg', width=100)
        coin_id = 'BTC'  # CoinMarketCap ID for Bitcoin
    elif page == "Ethereum (ETH)":
        st.header("Ethereum Price Analysis")
        st.image('https://commons.wikimedia.org/wiki/File:Ethereum_logo_2014.svg', width=100)
        coin_id = 'ETH'  # CoinMarketCap ID for Ethereum
    elif page == "Dogecoin (DOGE)":
        st.header("Dogecoin Price Analysis")
        st.image('https://upload.wikimedia.org/wikipedia/en/d/d0/Dogecoin_Logo.png', width=100)
        coin_id = 'DOGE'  # CoinMarketCap ID for Dogecoin
    else:
        st.error("Invalid page selection")
        return

    # Fetch data from PostgreSQL table
    df, highest_price, lowest_price = fetch_data_from_postgresql(coin_id)
    if not df.empty:
        st.success(f'{page.split(" ")[0]} price data loaded successfully!')
        
        # Display line graph
        create_line_graph(df, page.split(" ")[0])

        # Calculate percentage change for the entire dataset
        percentage_changes = calculate_percentage_change(df['rate'])

        # Find top 5 percentage increases and largest percentage decreases
        top_increases = sorted(range(len(percentage_changes)), key=lambda i: percentage_changes[i], reverse=True)[:5]
        top_decreases = sorted(range(len(percentage_changes)), key=lambda i: percentage_changes[i])[:5]

        # Create a DataFrame to display top increases and decreases
        top_changes_df = pd.DataFrame({
            'Timestamp': [df['time_of_scrape'][i] for i in top_increases] + [df['time_of_scrape'][i] for i in top_decreases],
            'Percentage Change': [percentage_changes[i] for i in top_increases] + [percentage_changes[i] for i in top_decreases],
            'Change Type': ['Increase'] * 5 + ['Decrease'] * 5
        })

        # Sidebar navigation for selecting the table to display
        display_table = st.sidebar.selectbox("Select Table to Display", ["Top 5 Percentage Increases", "Top 5 Largest Percentage Decreases"])

        # Display the selected table
        if display_table == "Top 5 Percentage Increases":
            st.header("Top 5 Percentage Increases")
            st.image('https://th.bing.com/th/id/OIP.IYaR-p4uEXap-PZBddnkywHaEK?rs=1&pid=ImgDetMain', width=200)
            st.table(top_changes_df[top_changes_df['Change Type'] == 'Increase'])
            st.write(f"Highest Price: {highest_price}")
        elif display_table == "Top 5 Largest Percentage Decreases":
            st.header("Top 5 Largest Percentage Decreases")
            st.image('https://th.bing.com/th/id/R.e59cdee9a55c9a96a14f1706c6d8697c?rik=2rfmfpeJkEKqZw&riu=http%3a%2f%2fimages7.memedroid.com%2fimages%2fUPLOADED333%2f5fe0de2ad6e08.jpeg&ehk=DrKflFsD3z8aD2p0%2bcZxbFOwd8mgHmBC3%2bJlwOJuy4I%3d&risl=&pid=ImgRaw&r=0', width=200)
            st.table(top_changes_df[top_changes_df['Change Type'] == 'Decrease'])
            st.write(f"Lowest Price: {lowest_price}")
        
    else:
        st.warning("No data found for the selected cryptocurrency.")

if __name__ == "__main__":
    main()
