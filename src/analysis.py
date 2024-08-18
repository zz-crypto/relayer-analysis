import pandas as pd
import mysql.connector
from sqlalchemy import create_engine    

engine = create_engine('mysql+mysqlconnector://root:your_new_password@localhost:3306/across_relay')

query = "SELECT * FROM relay_analysis"
df = pd.read_sql(query, engine)

chain_name_map = {
    1: 'Ethereum',
    10: 'Optimism',
    8453: 'Base',
    137: 'Polygon',
    42161: 'Arbitrum'    
}

df['destinationChainName'] = df['destination_chain_id'].map(chain_name_map)
df['originChainName'] = df['origin_chain_id'].map(chain_name_map)
df['tokenName'] = df['input_token']
df['profit_rate'] = (df['earned_amount'] / df['input_amount']) * 100

profitable_combinations = df.groupby(['destinationChainName', 'originChainName', 'tokenName'])\
    .agg({
        'profit_rate': ['mean', 'std', 'count'],
        'earned_amount': 'sum',
        'input_amount': 'sum'
    }).reset_index()

profitable_combinations.columns = ['destinationChain', 'originChain', 'token', 'avg_profit_rate', 'std_profit_rate', 'transaction_count', 'total_earned', 'total_input']

profitable_combinations['overall_profit_rate'] = (profitable_combinations['total_earned'] / profitable_combinations['total_input']) * 100

profitable_combinations_by_avg = profitable_combinations.sort_values('avg_profit_rate', ascending=False)

print("Top 10 most profitable combinations by average profit rate:")
print(profitable_combinations_by_avg[['destinationChain', 'originChain', 'token', 'avg_profit_rate', 'std_profit_rate', 'transaction_count']].head(10))

profitable_combinations_by_overall = profitable_combinations.sort_values('overall_profit_rate', ascending=False)

print("\nTop 10 most profitable combinations by overall profit rate:")
print(profitable_combinations_by_overall[['destinationChain', 'originChain', 'token', 'overall_profit_rate', 'total_earned', 'total_input', 'transaction_count']].head(10))