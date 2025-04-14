import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import altair as alt
import plotly.express as px
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
import datetime

st.markdown("""
    <style>
    .stButton > button {
        width: 100%;
    }
    </style>
""", unsafe_allow_html=True)

USERNAME = "kCCeTyfqG4q97x6.root"
PASSWORD = "O5K4JarXblpcn7gg"
HOST = "gateway01.ap-southeast-1.prod.aws.tidbcloud.com"  
PORT = 4000  
DATABASE = "stock_analysis"

#Create SQLAlchemy Engine
@st.cache_resource  
def get_engine():
    return create_engine(f"mysql+mysqlconnector://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}")

engine = get_engine()

#get volatility data

@st.cache_data  # Cache data to avoid repeated queries
def get_volatility_data():
    query = """
    SELECT 
        Ticker, 
        volatility
    FROM volatility 
    ORDER BY volatility DESC 
    LIMIT 10 
    """
    return pd.read_sql(query, engine)

# sector wise avg return
@st.cache_data  
def get_sector_avg_return():
    query = """
    SELECT 
        sector,
        AVG(total_return_pct) as avg_return,
        COUNT(Ticker) as stock_count
    FROM sector_yearly_return
    GROUP BY sector
    ORDER BY avg_return DESC
    """
    return pd.read_sql(query, engine)

#correlation matrix
@st.cache_data  
def get_corr_matrix():
    corr_query = """
    SELECT 
    Ticker,
    tran_date,
    close_price
    FROM cumulative_return
    WHERE tran_date >= '2018-01-01'
    """
    return pd.read_sql(corr_query, engine)

# method for monthly return
@st.cache_data  
def get_monthly_return():
    monthly_returns = """
    SELECT 
    Ticker,
    yr_mon,
    returns_monthly
    FROM monthly_return
    """
    return pd.read_sql(monthly_returns, engine)


# streamlit visualization
if st.sidebar.button("About Project"):
     st.header("Data Driven Stock Analysis")
     justified_text="""<p style='text-align: justify;'> The Stock Performance Dashboard aims to provide a comprehensive 
     visualization and analysis of the Nifty 50 stocks' performance over the past year. The project will analyze daily stock data, 
     including open, close, high, low, and volume values. Clean and process the data, generate key performance insights, 
     and visualize the top-performing stocks in terms of price changes, as well as average stock metrics. 
              </p>
     """
     st.markdown(justified_text, unsafe_allow_html=True)


st.sidebar.header("Business Use Cases:")


#--------Top 10 Most Volatile Stocks-----------
if st.sidebar.button("Top 10 Most Volatile Stocks"):
    st.subheader("Top 10 Most Volatile Stocks:")
    df_volatility = get_volatility_data()
    if not df_volatility.empty:
    # Create styled bar chart
        fig, ax = plt.subplots(figsize=(10, 5))
     
        bars = ax.bar(
            x=df_volatility['Ticker'],
            height=df_volatility['volatility'],
            alpha=0.8
        )
        
        ax.bar_label(bars, fmt='%.2f', padding=3)
        ax.set_ylabel("Annualized Volatility")
        ax.set_xlabel("Stock Ticker")
        ax.set_title("Top 10 Highest Volatile Stocks", pad=20)
        ax.grid(axis='y', linestyle='--', alpha=0.4)
        plt.xticks(rotation=45, ha='right')
        st.pyplot(fig)

#--------Top 5 cumulative returns line chart-----------
if st.sidebar.button("Top 5 Performing Stocks"):
    st.subheader("Top 5 Performing Stocks:")

    top_query = """
    SELECT 
        ticker, 
        MAX(cumulative_return) as final_return
    FROM cumulative_return
    GROUP BY ticker
    ORDER BY final_return DESC
    LIMIT 5
    """
    top_five_stocks = pd.read_sql(top_query, engine)['ticker'].tolist()

    data_query = f"""
    SELECT 
        ticker,
        tran_date as date,
        cumulative_return
    FROM cumulative_return
    WHERE ticker IN {tuple(top_five_stocks) if len(top_five_stocks) > 1 else f"('{top_five_stocks[0]}')"}
    ORDER BY tran_date
    """
    df_top_five_cumulative_return= pd.read_sql(data_query, engine, parse_dates=['date'])

    if not df_top_five_cumulative_return.empty:

        fig, ax = plt.subplots(figsize=(14, 7))
        
        # Color palette
        colors = plt.cm.tab10.colors
        
        # Plot each stock
        for i, ticker in enumerate(df_top_five_cumulative_return['ticker'].unique()):
            stock_data = df_top_five_cumulative_return[df_top_five_cumulative_return['ticker'] == ticker]
            ax.plot(stock_data['date'], 
                    stock_data['cumulative_return'], 
                    label=ticker,
                    color=colors[i % 10],
                    linewidth=2.5,
                    marker='o',
                    markersize=4,
                    markevery=15)
        
        ax.set_title(f"Cumulative Returns", 
                    fontsize=16, pad=20)
        ax.set_xlabel("Date", fontsize=12)
        ax.set_ylabel("Cumulative Return", fontsize=12)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.0%}"))
        ax.grid(True, linestyle='--', alpha=0.4)
        plt.legend(fontsize=10, bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.xticks(rotation=45)
        plt.tight_layout()
        st.pyplot(fig)

if st.sidebar.button("Sector Return"):
    st.subheader("Sector Performance:")

    df_sector_avg_return=get_sector_avg_return()

    fig = px.bar(
    df_sector_avg_return,
    x='sector',
    y='avg_return',
    color='avg_return',
    color_continuous_scale='Bluered',
    title=f"Average Yearly Return by Sector",
    labels={'avg_return': 'Avg. Return (%)', 'sector': 'Sector'},
    hover_data=['stock_count']
    )
    fig.update_layout(
        hovermode='x unified',
        xaxis_tickangle=-45
    )
    st.plotly_chart(fig, use_container_width=True)

if st.sidebar.button("Correlation Coefficient"):
    st.subheader("Correlation Coefficient:")

    df_corr = get_corr_matrix()
    pivot_df = df_corr.pivot(index='tran_date', columns='Ticker', values='close_price')
    correlation_matrix = pivot_df.corr()

    fig = px.imshow(correlation_matrix, labels=dict(x="Stock Ticker", y="Stock Ticker", color="Correlation"),
                        x=correlation_matrix.columns, y=correlation_matrix.columns, color_continuous_scale='RdBu',
                        title="Stock Price Correlation Heatmap")

    fig.update_layout(
            width=1000, 
            height=800,  
            xaxis_title="Stock Ticker",
            yaxis_title="Stock Ticker",
            title={'text': "Stock Price Correlation Heatmap", 'y': 0.95, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'}
        )
    st.plotly_chart(fig)

if st.sidebar.button("Monthly Performance"):
        st.subheader("Monthly Performance:")

        @st.cache_data
        def load_data():
            df = get_monthly_return()
            df['yr_mon'] = pd.to_datetime(df['yr_mon'], errors='coerce')
            df = df.dropna(subset=['yr_mon'])
            df['month'] = df['yr_mon'].dt.month
            df['year'] = df['yr_mon'].dt.year
            df['year_month'] = df['yr_mon'].dt.to_period('M')
            df['returns_monthly'] = pd.to_numeric(df['returns_monthly'], errors='coerce')
            return df

        df_monthly_return = load_data()

        # Get sorted unique periods
        unique_periods = sorted(df_monthly_return['year_month'].unique())

        if not unique_periods:
            st.error("No valid date periods found in the data!")
        else:
            for period in unique_periods:
                year = period.year
                month = period.month
                month_name = period.strftime('%B')
                
                with st.expander(f"{month_name} {year}", expanded=True):
                    st.write(f"### 📅 {month_name} {year}")
                    
                    # Filter data
                    monthly_data = df_monthly_return[
                        (df_monthly_return['year'] == year) & 
                        (df_monthly_return['month'] == month)
                    ].copy()
                    
                    if not monthly_data.empty:
                        monthly_data['monthly_return'] = monthly_data['returns_monthly']
                        
                        # Get last return for each ticker (assuming multiple entries per month)
                        last_monthly_returns = monthly_data.groupby('Ticker')['monthly_return'].last()
                        
                        # Get top and bottom performers
                        top_5 = last_monthly_returns.nlargest(5)
                        bottom_5 = last_monthly_returns.nsmallest(5)
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if not top_5.empty:
                                fig = px.bar(
                                    top_5.reset_index(), 
                                    x='Ticker', 
                                    y='monthly_return',
                                    title=f'🏆 Top 5 Performers - {month_name} {year}',
                                    labels={'monthly_return': 'Return'},
                                    color_discrete_sequence=['green']
                                )
                                fig.update_traces(texttemplate='%{y:.2f}', textposition='outside')
                                st.plotly_chart(fig, use_container_width=True)
                        
                        with col2:
                            if not bottom_5.empty:
                                fig = px.bar(
                                    bottom_5.reset_index(), 
                                    x='Ticker', 
                                    y='monthly_return',
                                    title=f'⚠️ Bottom 5 Performers - {month_name} {year}',
                                    labels={'monthly_return': 'Return'},
                                    color_discrete_sequence=['red']
                                )
                                fig.update_traces(texttemplate='%{y:.2f}', textposition='outside')
                                st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning(f"No data available for {month_name} {year}")
                    
                    st.markdown("---")