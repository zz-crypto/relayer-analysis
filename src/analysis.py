import pandas as pd

df = pd.read_csv('your_data.csv') 

df['profit_rate'] = (df['earnedAmount'] / df['inputAmount']) * 100

profitable_combinations = df.groupby(['destinationChainName', 'originChainName', 'tokenName'])\
    .agg({
        'profit_rate': ['mean', 'std', 'count'],
        'earnedAmount': 'sum',
        'inputAmount': 'sum'
    }).reset_index()

profitable_combinations.columns = ['destinationChain', 'originChain', 'token', 'avg_profit_rate', 'std_profit_rate', 'transaction_count', 'total_earned', 'total_input']

profitable_combinations['overall_profit_rate'] = (profitable_combinations['total_earned'] / profitable_combinations['total_input']) * 100

profitable_combinations_by_avg = profitable_combinations.sort_values('avg_profit_rate', ascending=False)

print("Top 10 most profitable combinations by average profit rate:")
print(profitable_combinations_by_avg[['destinationChain', 'originChain', 'token', 'avg_profit_rate', 'std_profit_rate', 'transaction_count']].head(10))

profitable_combinations_by_overall = profitable_combinations.sort_values('overall_profit_rate', ascending=False)

print("\nTop 10 most profitable combinations by overall profit rate:")
print(profitable_combinations_by_overall[['destinationChain', 'originChain', 'token', 'overall_profit_rate', 'total_earned', 'total_input', 'transaction_count']].head(10))