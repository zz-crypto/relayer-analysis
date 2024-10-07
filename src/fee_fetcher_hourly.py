import requests
from datetime import datetime
import mysql.connector
from mysql.connector import Error
import logging
import time
import json

logging.basicConfig(filename='fee_data_fetch_hourly.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


with open("database_config.json") as f:
    db_config = json.load(f)


API_URL = "https://app.across.to/api/suggested-fees"

def convert_datetime_to_timestamp(dt_str):
    dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
    return int(time.mktime(dt.timetuple()))

def fetch_fee_data(params):
    try:
        url = f"{API_URL}?inputToken={params['inputToken']}&outputToken={params['outputToken']}&destinationChainId={params['destinationChainId']}&originChainId={params['originChainId']}&amount={params['amount']}&quoteTimestamp={params['quoteTimestamp']}&skipAmountLimit=true"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logging.error(f"Error fetching data: {e}")
        return None

def insert_fee_data(cursor, data, timestamp, params):
    sql = """INSERT INTO fee_data_hourly 
             (timestamp, input_token, output_token, origin_chain_id, destination_chain_id, amount,
              total_relay_fee_pct, relayer_capital_fee_pct, relayer_gas_fee_pct, lp_fee_pct,
              quote_block, min_deposit, max_deposit, max_deposit_instant, max_deposit_short_delay, 
              recommended_deposit_instant) 
             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
    values = (timestamp,
              params['inputToken'],
              params['outputToken'],
              params['originChainId'],
              params['destinationChainId'],
              params['amount'],
              data['totalRelayFee']['pct'],
              data['relayerCapitalFee']['pct'],
              data['relayerGasFee']['pct'],
              data['lpFee']['pct'],
              data['quoteBlock'],
              data['limits']['minDeposit'],
              data['limits']['maxDeposit'],
              data['limits']['maxDepositInstant'],
              data['limits']['maxDepositShortDelay'],
              data['limits']['recommendedDepositInstant'])

    cursor.execute(sql, values)

def get_token_pairs(cursor):
    query = """
    WITH normalized_amounts AS (
    SELECT 
        *,
        CASE 
            WHEN output_symbol IN ('WETH', 'ETH', 'DAI') THEN output_amount * 1e18
            WHEN output_symbol = 'WBTC' THEN output_amount * 1e8
            WHEN output_symbol IN ('USDT', 'USDC') THEN output_amount * 1e6
            ELSE output_amount
        END AS original_output_amount
    FROM relay_analysis_results
    ),
    ranges AS (
    SELECT 
        destination_chain_id,
        origin_chain_id,
        output_token,
        input_token,
        CASE 
            WHEN output_amount_usd < 1000 THEN '0-1k'
            WHEN output_amount_usd < 10000 THEN '1k-10k'
            WHEN output_amount_usd < 100000 THEN '10k-100k'
            ELSE '100k+'
        END AS amount_range,
        POWER(10, FLOOR(LOG10(original_output_amount))) AS output_amount_range
    FROM normalized_amounts
    )
    SELECT 
        destination_chain_id,
        origin_chain_id,
        output_token,
        input_token,
        POWER(10, FLOOR(LOG10(AVG(output_amount_range)))) as output_amount         
    FROM ranges
    GROUP BY 
        destination_chain_id,
        origin_chain_id,
        output_token,
        input_token,
        amount_range
    ORDER BY 
        destination_chain_id,
        origin_chain_id,
        output_token,
        input_token,
        amount_range;
    """
    cursor.execute(query)
    return cursor.fetchall()

def main():
    try:
        connection = mysql.connector.connect(**db_config)
        if connection.is_connected():
            cursor = connection.cursor()
            
            token_pairs = get_token_pairs(cursor)
            
            for pair in token_pairs:
                destination_chain_id, origin_chain_id, output_token, input_token, output_amount = pair
                
                
                current_time = datetime.now()
                quote_timestamp = int(current_time.timestamp())
                
                
                output_amount = int(output_amount)
                
                params = {
                    'inputToken': input_token,
                    'outputToken': output_token,
                    'originChainId': origin_chain_id,
                    'destinationChainId': destination_chain_id,
                    'amount': str(output_amount),
                    'quoteTimestamp': quote_timestamp
                }
                data = fetch_fee_data(params)
                if data:
                    try:
                        insert_fee_data(cursor, data, current_time, params)
                        connection.commit()
                        logging.info(f"Data inserted for {current_time} - {input_token} to {output_token}")
                    except Error as e:
                        logging.error(f"Error inserting data for {current_time} - {input_token} to {output_token}: {e}")
                        connection.rollback()
                else:
                    logging.warning(f"No data fetched for {current_time} - {input_token} to {output_token}")
            
    except Error as e:
        logging.error(f"Database error: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            logging.info("MySQL connection is closed")

if __name__ == "__main__":
    main()