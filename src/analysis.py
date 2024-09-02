import pandas as pd
from sqlalchemy import create_engine    
from db_operations import DatabaseOperations

db_ops = DatabaseOperations()
try:
    db_ops.connect()
    db_ops.fetch_and_insert_relay_data()
finally:
    db_ops.close()

engine = create_engine('mysql+mysqlconnector://root:your_new_password@localhost:3306/across_relay')


query = "SELECT * FROM relay_analysis"
df_raw = pd.read_sql(query, engine)


df_raw.to_csv('relay_analysis_raw_data.csv', index=False)
print("Raw data from relay_analysis table has been saved to 'relay_analysis_raw_data.csv'")


df = df_raw.copy()  

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
profitable_combinations_by_overall = profitable_combinations.sort_values('overall_profit_rate', ascending=False)

profitable_combinations_by_avg[['destinationChain', 'originChain', 'token', 'avg_profit_rate', 'std_profit_rate', 'transaction_count']].to_csv('profitable_combinations_by_avg.csv', index=False)
profitable_combinations_by_overall[['destinationChain', 'originChain', 'token', 'overall_profit_rate', 'total_earned', 'total_input', 'transaction_count']].to_csv('profitable_combinations_by_overall.csv', index=False)

print("Analysis results have been saved to 'profitable_combinations_by_avg.csv' and 'profitable_combinations_by_overall.csv'")