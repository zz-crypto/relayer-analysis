import requests
from datetime import datetime
import mysql.connector
from mysql.connector import Error
import logging
import time
import json


logging.basicConfig(
    filename="fee_data_fetch.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


with open("database_config.json") as f:
    db_config = json.load(f)


API_URL = "https://app.across.to/api/suggested-fees"


def convert_datetime_to_timestamp(dt_str):
    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
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


def insert_fee_data(cursor, data, timestamp, params, deposit_id):
    sql = """INSERT INTO fee_data 
             (timestamp, input_token, output_token, origin_chain_id, destination_chain_id, amount,
              total_relay_fee_pct, relayer_capital_fee_pct, relayer_gas_fee_pct, lp_fee_pct,
              quote_block, min_deposit, max_deposit, max_deposit_instant, max_deposit_short_delay, 
              recommended_deposit_instant, deposit_id) 
             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
    values = (
        timestamp,
        params["inputToken"],
        params["outputToken"],
        params["originChainId"],
        params["destinationChainId"],
        params["amount"],
        data["totalRelayFee"]["pct"],
        data["relayerCapitalFee"]["pct"],
        data["relayerGasFee"]["pct"],
        data["lpFee"]["pct"],
        data["quoteBlock"],
        data["limits"]["minDeposit"],
        data["limits"]["maxDeposit"],
        data["limits"]["maxDepositInstant"],
        data["limits"]["maxDepositShortDelay"],
        data["limits"]["recommendedDepositInstant"],
        deposit_id,
    )

    cursor.execute(sql, values)


def get_token_pairs(cursor):
    cursor.execute("truncate table fee_data")
    query = """
        SELECT r.origin_chain_id, r.destination_chain_id, r.input_token, r.output_token, r.deposit_block_time, f.output_amount, r.deposit_id
            FROM relay_analysis_results r 
            JOIN filled_v3_relays f ON f.origin_chain_id = r.origin_chain_id 
                AND f.chain_id = r.destination_chain_id 
                AND f.input_token = r.input_token 
                AND f.output_token = r.output_token 
                AND f.deposit_id = r.deposit_id
            JOIN target_combo tc ON r.origin_chain_id = tc.origin_chain_id
                AND r.destination_chain_id = tc.destination_chain_id
                AND r.input_symbol = tc.input_symbol
                AND r.output_symbol = tc.output_symbol
            WHERE DATE(r.fill_block_time) >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
            AND (
                (tc.amount_range = '1k-10k' AND r.output_amount_usd > 1000 AND r.output_amount_usd < 10000)
                OR
                (tc.amount_range = '10k-100k' AND r.output_amount_usd > 10000 AND r.output_amount_usd < 100000)
            )
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
                (
                    origin_chain_id,
                    destination_chain_id,
                    input_token,
                    output_token,
                    deposit_block_time,
                    output_amount,
                    deposit_id,
                ) = pair

                quote_timestamp = convert_datetime_to_timestamp(
                    deposit_block_time.strftime("%Y-%m-%d %H:%M:%S")
                )

                params = {
                    "inputToken": input_token,
                    "outputToken": output_token,
                    "originChainId": origin_chain_id,
                    "destinationChainId": destination_chain_id,
                    "amount": str(int(output_amount)),
                    "quoteTimestamp": quote_timestamp,
                }
                data = fetch_fee_data(params)
                if data:
                    try:
                        insert_fee_data(
                            cursor, data, deposit_block_time, params, deposit_id
                        )
                        connection.commit()
                        logging.info(
                            f"Data inserted for {deposit_block_time} - {input_token} to {output_token}"
                        )
                    except Error as e:
                        logging.error(
                            f"Error inserting data for {deposit_block_time} - {input_token} to {output_token}: {e}"
                        )
                        connection.rollback()
                else:
                    logging.warning(
                        f"No data fetched for {deposit_block_time} - {input_token} to {output_token}"
                    )

    except Error as e:
        logging.error(f"Database error: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            logging.info("MySQL connection is closed")


if __name__ == "__main__":
    main()
