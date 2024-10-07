import mysql.connector
import json

class DatabaseOperations:
    general_performance_query = """
            WITH combo_stats AS (
                WITH daily_stats AS (
                    SELECT 
                        DATE(fill_block_time) AS date,
                        origin_chain_id, destination_chain_id, input_symbol, output_symbol,
                        SUM(output_amount_usd) AS daily_volume_usd,
                        SUM(input_amount_usd - output_amount_usd - gas_fee * 2700) AS daily_profit_usd,
                        CASE 
                            WHEN input_amount_usd < 1000 THEN '0-1k'
                            WHEN input_amount_usd < 10000 THEN '1k-10k'
                            WHEN input_amount_usd < 100000 THEN '10k-100k'
                            ELSE '100k+'
                        END AS amount_range,
                        COUNT(*) as transaction_count,
                        AVG(relay_time) AS avg_relay_time_seconds,
                        MAX(input_amount_usd) AS max_transaction_size_usd
                    FROM relay_analysis_results
                    GROUP BY DATE(fill_block_time), origin_chain_id, destination_chain_id, input_symbol, output_symbol, amount_range
                )
                SELECT 
                    origin_chain_id, 
                    destination_chain_id, 
                    input_symbol, output_symbol, 
                    amount_range,
                    AVG(daily_volume_usd) AS avg_daily_volume_usd,
                    AVG(daily_profit_usd) AS avg_daily_profit_usd,
                    AVG(daily_profit_usd) / AVG(daily_volume_usd) AS daily_roi,
                    AVG(daily_profit_usd) / AVG(daily_volume_usd) * 365 AS annual_roi,
                    AVG(transaction_count) AS avg_daily_transaction_count,
                    AVG(avg_relay_time_seconds) AS avg_relay_time_seconds,
                    MAX(max_transaction_size_usd) AS max_transaction_size_usd
                FROM daily_stats
                GROUP BY origin_chain_id, destination_chain_id, input_symbol, output_symbol, amount_range
            ),
            optimal_allocation AS (
                SELECT 
                    *,
                    CASE
                        WHEN avg_daily_volume_usd > 0 THEN
                            GREATEST(
                                avg_daily_volume_usd,  
                                max_transaction_size_usd
                            )
                        ELSE 0
                    END AS suggested_allocation_usd,
                    avg_daily_transaction_count * avg_relay_time_seconds AS daily_capital_usage_time,
                    avg_daily_volume_usd / NULLIF(GREATEST(avg_daily_volume_usd, max_transaction_size_usd), 0) AS daily_capital_turnover
                FROM combo_stats
            )
            SELECT 
                origin_chain_id,
                destination_chain_id,
                input_symbol, output_symbol,
                amount_range,
                suggested_allocation_usd as estimated_allocation_needed,
                annual_roi,
                suggested_allocation_usd * daily_capital_turnover * annual_roi AS estimated_annual_profit_usd,
                daily_capital_usage_time / 86400 AS daily_capital_usage_ratio,
                daily_capital_turnover,
                avg_daily_volume_usd,
                avg_daily_profit_usd,
                avg_daily_transaction_count,
                avg_daily_volume_usd / avg_daily_transaction_count as avg_daily_volume_per_trx,
                avg_relay_time_seconds
            FROM optimal_allocation
            WHERE annual_roi > 0 AND amount_range != '100k+' AND avg_daily_transaction_count > 5 AND avg_daily_volume_usd > 100000
            ORDER BY annual_roi DESC;
        """
    general_daily_data_query = """
        SELECT 
            DATE(fill_block_time) AS date,
            origin_chain_id, destination_chain_id, input_symbol, output_symbol,
            SUM(output_amount_usd) AS daily_volume_usd,
            SUM(input_amount_usd - output_amount_usd - gas_fee * 2700) AS daily_total_profit_usd,
            CASE 
                WHEN input_amount_usd < 1000 THEN '0-1k'
                WHEN input_amount_usd < 10000 THEN '1k-10k'
                WHEN input_amount_usd < 100000 THEN '10k-100k'
                ELSE '100k+'
            END AS amount_range,
            COUNT(*) as transaction_count,
            AVG(relay_time) AS avg_relay_time_seconds,
            MAX(input_amount_usd) AS max_transaction_size_usd,
            SUM(input_amount_usd - output_amount_usd - gas_fee * 2700) / SUM(input_amount_usd) as daily_roi
        FROM relay_analysis_results
        GROUP BY DATE(fill_block_time), origin_chain_id, destination_chain_id, input_symbol, output_symbol, amount_range
    """
    target_combo_query = """
        INSERT INTO target_combo (origin_chain_id, destination_chain_id, input_symbol, output_symbol, amount_range)
        WITH combo_stats AS (
            WITH daily_stats AS (
                SELECT 
                    DATE(fill_block_time) AS date,
                    origin_chain_id, destination_chain_id, input_symbol, output_symbol,
                    SUM(output_amount_usd) AS daily_volume_usd,
                    SUM(input_amount_usd - output_amount_usd - gas_fee * 2700) AS daily_profit_usd,
                    CASE 
                        WHEN input_amount_usd < 1000 THEN '0-1k'
                        WHEN input_amount_usd < 10000 THEN '1k-10k'
                        WHEN input_amount_usd < 100000 THEN '10k-100k'
                        ELSE '100k+'
                    END AS amount_range,
                    COUNT(*) as transaction_count,
                    AVG(relay_time) AS avg_relay_time_seconds,
                    MAX(input_amount_usd) AS max_transaction_size_usd
                FROM relay_analysis_results
                WHERE DATE(fill_block_time) >= DATE_SUB(CURDATE() - 1, INTERVAL 7 DAY)
                GROUP BY DATE(fill_block_time), origin_chain_id, destination_chain_id, input_symbol, output_symbol, amount_range
            )
            SELECT 
                origin_chain_id, 
                destination_chain_id, 
                input_symbol, output_symbol, 
                amount_range,
                AVG(daily_volume_usd) AS avg_daily_volume_usd,
                AVG(daily_profit_usd) AS avg_daily_profit_usd,
                AVG(daily_profit_usd) / AVG(daily_volume_usd) AS daily_roi,
                AVG(daily_profit_usd) / AVG(daily_volume_usd) * 365 AS annual_roi,
                AVG(transaction_count) AS avg_daily_transaction_count,
                AVG(avg_relay_time_seconds) AS avg_relay_time_seconds,
                MAX(max_transaction_size_usd) AS max_transaction_size_usd
            FROM daily_stats
            GROUP BY origin_chain_id, destination_chain_id, input_symbol, output_symbol, amount_range
        ),
        optimal_allocation AS (
            SELECT 
                *,
                CASE
                    WHEN avg_daily_volume_usd > 0 THEN
                        GREATEST(
                            avg_daily_volume_usd,  
                            max_transaction_size_usd
                        )
                    ELSE 0
                END AS suggested_allocation_usd,
                avg_daily_transaction_count * avg_relay_time_seconds AS daily_capital_usage_time,
                avg_daily_volume_usd / NULLIF(GREATEST(avg_daily_volume_usd, max_transaction_size_usd), 0) AS daily_capital_turnover
            FROM combo_stats
        )
        SELECT DISTINCT
            origin_chain_id,
            destination_chain_id,
            input_symbol,
            output_symbol,
            amount_range
        FROM optimal_allocation
        WHERE annual_roi > 0 
        AND amount_range != '100k+' 
        AND avg_daily_volume_usd > 100000
        ORDER BY annual_roi DESC;
    """
    target_relayer_combo_query = """
        CREATE TABLE target_relayer_combo AS                    
            WITH combo_totals AS (
                SELECT 
                    tc.origin_chain_id,
                    tc.destination_chain_id,
                    tc.input_symbol,
                    tc.output_symbol,
                    tc.amount_range,
                    SUM(rar.output_amount_usd) AS total_volume_usd,
                    COUNT(*) AS total_transactions
                FROM 
                    target_combo tc
                JOIN 
                    relay_analysis_results rar ON 
                        tc.origin_chain_id = rar.origin_chain_id AND
                        tc.destination_chain_id = rar.destination_chain_id AND
                        tc.input_symbol = rar.input_symbol AND
                        tc.output_symbol = rar.output_symbol AND
                        tc.amount_range = CASE 
                            WHEN rar.input_amount_usd < 1000 THEN '0-1k'
                            WHEN rar.input_amount_usd < 10000 THEN '1k-10k'
                            WHEN rar.input_amount_usd < 100000 THEN '10k-100k'
                            ELSE '100k+'
                        END
                WHERE rar.fill_block_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                GROUP BY 
                    tc.origin_chain_id,
                    tc.destination_chain_id,
                    tc.input_symbol,
                    tc.output_symbol,
                    tc.amount_range
            )
            SELECT 
                tc.origin_chain_id,
                tc.destination_chain_id,
                tc.input_symbol,
                tc.output_symbol,
                tc.amount_range,
                rar.relayer,
                COUNT(*) AS transaction_count,
                (COUNT(*) * 100.0 / ct.total_transactions) AS transaction_percentage,
                ct.total_volume_usd,
                ct.total_volume_usd / 7 AS daily_volume_usd,
                AVG(rar.input_amount_usd - rar.output_amount_usd - rar.gas_fee * 2700) as avg_profit_usd,
                SUM(rar.input_amount_usd - rar.output_amount_usd - rar.gas_fee * 2700) as total_profit_usd,
                AVG(rar.input_amount_usd - rar.output_amount_usd - rar.gas_fee * 2700) / AVG(rar.output_amount_usd) AS avg_profit_ratio,
                SUM(rar.input_amount_usd - rar.output_amount_usd - rar.gas_fee * 2700) / SUM(rar.output_amount_usd) AS total_profit_ratio,
                AVG(rar.input_amount_usd - rar.output_amount_usd - rar.gas_fee * 2700 - rar.output_amount_usd * fd.lp_fee_pct / 1e18) as avg_net_profit_usd,
                SUM(rar.input_amount_usd - rar.output_amount_usd - rar.gas_fee * 2700 - rar.output_amount_usd * fd.lp_fee_pct / 1e18) as total_net_profit_usd,
                AVG(rar.input_amount_usd - rar.output_amount_usd - rar.gas_fee * 2700 - rar.output_amount_usd * fd.lp_fee_pct / 1e18) / AVG(rar.output_amount_usd) AS avg_net_profit_ratio,
                SUM(rar.input_amount_usd - rar.output_amount_usd - rar.gas_fee * 2700 - rar.output_amount_usd * fd.lp_fee_pct / 1e18) / SUM(rar.output_amount_usd) AS total_net_profit_ratio,
                AVG(rar.relay_time) as avg_relay_time,
                AVG(rar.priority_fee * 2700) as avg_priority_fee
            FROM 
                target_combo tc
            JOIN 
                relay_analysis_results rar ON 
                    tc.origin_chain_id = rar.origin_chain_id AND
                    tc.destination_chain_id = rar.destination_chain_id AND
                    tc.input_symbol = rar.input_symbol AND
                    tc.output_symbol = rar.output_symbol AND
                    tc.amount_range = CASE 
                        WHEN rar.input_amount_usd < 1000 THEN '0-1k'
                        WHEN rar.input_amount_usd < 10000 THEN '1k-10k'
                        WHEN rar.input_amount_usd < 100000 THEN '10k-100k'
                        ELSE '100k+'
                    END
            JOIN
                combo_totals ct ON
                    tc.origin_chain_id = ct.origin_chain_id AND
                    tc.destination_chain_id = ct.destination_chain_id AND
                    tc.input_symbol = ct.input_symbol AND
                    tc.output_symbol = ct.output_symbol AND
                    tc.amount_range = ct.amount_range
            JOIN
                fee_data fd ON
                    rar.deposit_id = fd.deposit_id AND
                    rar.origin_chain_id = fd.origin_chain_id AND
                    rar.destination_chain_id = fd.destination_chain_id
            WHERE rar.fill_block_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            GROUP BY 
                tc.origin_chain_id,
                tc.destination_chain_id,
                tc.input_symbol,
                tc.output_symbol,
                tc.amount_range,
                rar.relayer,
                ct.total_transactions
            HAVING 
                SUM(rar.input_amount_usd - rar.output_amount_usd - rar.gas_fee * 2700) > 30
            ORDER BY 
                tc.origin_chain_id,
                tc.destination_chain_id,
                tc.input_symbol,
                tc.output_symbol,
                tc.amount_range,
                total_net_profit_usd DESC;
    """
    
    def __init__(self):
        self.db_config = self.get_db_config()
        self.conn = None
        self.cursor = None

    def get_db_config(self):
        try:
            with open('database_config.json', 'r') as config_file:
                config = json.load(config_file)
                return config['database']
        except FileNotFoundError:
            print("Error: config.json file not found.")
            return None
        except json.JSONDecodeError:
            print("Error: config.json is not a valid JSON file.")
            return None
        except KeyError:
            print("Error: 'database' key not found in config.json.")
            return None
    
    def connect(self):
        self.conn = mysql.connector.connect(**self.db_config)
        self.cursor = self.conn.cursor()

    def close(self):
        if self.cursor:
            self.cursor.close()
        if self.conn and self.conn.is_connected():
            self.conn.close()
            print("MySQL connection is closed")

    def execute_query(self, query): 
        try:
            print("Executing query...")
            self.cursor.execute(query)
            self.conn.commit()
        except mysql.connector.Error as err:
            if "Commands out of sync" in str(err):
                self.conn.rollback()
                self.cursor.close()
                self.cursor = self.conn.cursor()
                self.cursor.execute(query)  
                results = self.cursor.fetchall()  
                self.conn.commit()
            else:
                print(f"An error occurred: {err}")
        
    def insert_relay_data(self, batch_size=1000):
        get_existing_combinations_query = """
        SELECT DISTINCT deposit_id, destination_chain_id FROM relay_analysis_results
        """
        
        get_new_combinations_query = """
        SELECT DISTINCT f.deposit_id, f.chain_id AS destination_chain_id
        FROM filled_v3_relays f
        LEFT JOIN relay_analysis_results r ON f.deposit_id = r.deposit_id AND f.chain_id = r.destination_chain_id
        WHERE r.deposit_id IS NULL
        ORDER BY f.deposit_id, f.chain_id
        """
        
        insert_query = """
        INSERT INTO relay_analysis_results (
            deposit_id, destination_chain_id, origin_chain_id, input_token, output_token,
            relayer, depositor, recipient, input_amount, output_amount, input_amount_usd,
            output_amount_usd, input_symbol, output_symbol, gas_fee, priority_fee,
            base_fee_per_gas, gas_used, priority_fee_per_gas, relay_time, deposit_block_time, fill_block_time, transaction_hash, exclusive_relayer
        )
        SELECT 
            f.deposit_id,
            f.chain_id AS destination_chain_id,
            d.chain_id AS origin_chain_id,
            f.input_token,
            f.output_token,
            f.relayer,
            f.depositor,
            d.recipient,
            CASE 
                WHEN pi.symbol IN ('WETH', 'ETH') THEN f.input_amount / 1e18
                WHEN pi.symbol = 'WBTC' THEN f.input_amount / 1e8
                WHEN pi.symbol IN ('USDT', 'USDC') THEN f.input_amount / 1e6
                WHEN pi.symbol = 'DAI' THEN f.input_amount / 1e18
                ELSE f.input_amount
            END AS input_amount,
            CASE 
                WHEN po.symbol IN ('WETH', 'ETH') THEN f.output_amount / 1e18
                WHEN po.symbol = 'WBTC' THEN f.output_amount / 1e8
                WHEN po.symbol IN ('USDT', 'USDC') THEN f.output_amount / 1e6
                WHEN po.symbol = 'DAI' THEN f.output_amount / 1e18
                ELSE f.output_amount
            END AS output_amount,
            CASE 
                WHEN pi.symbol IN ('WETH', 'ETH') THEN (f.input_amount / 1e18) * COALESCE(pi.price_usd, 1)
                WHEN pi.symbol = 'WBTC' THEN (f.input_amount / 1e8) * COALESCE(pi.price_usd, 1)
                WHEN pi.symbol IN ('USDT', 'USDC') THEN (f.input_amount / 1e6) * COALESCE(pi.price_usd, 1)
                WHEN pi.symbol = 'DAI' THEN (f.input_amount / 1e18) * COALESCE(pi.price_usd, 1)
                ELSE f.input_amount * COALESCE(pi.price_usd, 1)
            END AS input_amount_usd,
            CASE 
                WHEN po.symbol IN ('WETH', 'ETH') THEN (f.output_amount / 1e18) * COALESCE(po.price_usd, 1)
                WHEN po.symbol = 'WBTC' THEN (f.output_amount / 1e8) * COALESCE(po.price_usd, 1)
                WHEN po.symbol IN ('USDT', 'USDC') THEN (f.output_amount / 1e6) * COALESCE(po.price_usd, 1)
                WHEN po.symbol = 'DAI' THEN (f.output_amount / 1e18) * COALESCE(po.price_usd, 1)
                ELSE f.output_amount * COALESCE(po.price_usd, 1)
            END AS output_amount_usd,
            pi.symbol as input_symbol,
            po.symbol as output_symbol,
            COALESCE(t.total_gas_fee, 0) / 1e18 AS gas_fee,
            GREATEST(0, t.gas_price - b.base_fee_per_gas) * t.gas_used / 1e18 AS priority_fee,
            b.base_fee_per_gas / 1e9 AS base_fee_per_gas,
            t.gas_used,
            GREATEST(0, t.gas_price - b.base_fee_per_gas) / 1e9 AS priority_fee_per_gas,
            TIMESTAMPDIFF(SECOND, bd.block_timestamp, bf.block_timestamp) AS relay_time,
            bd.block_timestamp AS deposit_block_time, 
            bf.block_timestamp AS fill_block_time,
            f.transaction_hash,
            f.exclusive_relayer            
        FROM 
            filled_v3_relays f
        JOIN
            v3_funds_deposited d ON f.deposit_id = d.deposit_id AND f.origin_chain_id = d.chain_id
        JOIN
            transaction_details t ON f.transaction_hash = t.transaction_hash AND f.chain_id = t.chain_id
        JOIN
            block_details b ON t.chain_id = b.chain_id AND b.block_number = f.block_number
        JOIN
            block_details bf ON f.chain_id = bf.chain_id AND bf.block_number = f.block_number
        JOIN
            block_details bd ON d.chain_id = bd.chain_id AND bd.block_number = d.block_number
        JOIN
            (SELECT token_address, price_usd, symbol FROM token_prices) pi ON f.input_token = pi.token_address
        JOIN
            (SELECT token_address, price_usd, symbol FROM token_prices) po ON f.output_token = po.token_address
        WHERE (f.deposit_id, f.chain_id) IN ({})
        AND (pi.token_address IN (
            '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2',
            '0x2260fac5e5542a773aa44fbcfedf7c193bc2c599',
            '0x6b175474e89094c44da98b954eedeac495271d0f',
            '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48',
            '0xdac17f958d2ee523a2206206994597c13d831ec7',
            '0x4200000000000000000000000000000000000006',
            '0x68f180fcce6836688e9084f035309e29bf0a2095',
            '0xda10009cbd5d07dd0cecc66161fc93d7c9000da1',
            '0x0b2c639c533813f4aa9d7837caf62653d097ff85',
            '0x94b008aa00579c1307b0ef2c499ad98a8ce58e58',
            '0x4200000000000000000000000000000000000006',
            '0x50c5725949a6f0c72e6c4a641f24049a917db0cb',
            '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913',
            '0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2',
            '0x7ceb23fd6bc0add59e62ac25578270cff1b9f619',
            '0x1BFD67037B42Cf73acF2047067bd4F2C47D9BfD6',
            '0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063',
            '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174',
            '0xc2132d05d31c914a87c6611c10748aeb04b58e8f',
            '0x82af49447d8a07e3bd95bd0d56f35241523fbab1',
            '0x2f2a2543b76a4166549f7aab2e75bef0aefc5b0f',
            '0xda10009cbd5d07dd0cecc66161fc93d7c9000da1',
            '0xaf88d065e77c8cc2239327c5edb3a432268e5831',
            '0xfd086bc7cd5c481dcc9c85ebe478a1c0b69fcbb9'
        ) AND po.token_address IN (
            '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2',
            '0x2260fac5e5542a773aa44fbcfedf7c193bc2c599',
            '0x6b175474e89094c44da98b954eedeac495271d0f',
            '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48',
            '0xdac17f958d2ee523a2206206994597c13d831ec7',
            '0x4200000000000000000000000000000000000006',
            '0x68f180fcce6836688e9084f035309e29bf0a2095',
            '0xda10009cbd5d07dd0cecc66161fc93d7c9000da1',
            '0x0b2c639c533813f4aa9d7837caf62653d097ff85',
            '0x94b008aa00579c1307b0ef2c499ad98a8ce58e58',
            '0x4200000000000000000000000000000000000006',
            '0x50c5725949a6f0c72e6c4a641f24049a917db0cb',
            '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913',
            '0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2',
            '0x7ceb23fd6bc0add59e62ac25578270cff1b9f619',
            '0x1BFD67037B42Cf73acF2047067bd4F2C47D9BfD6',
            '0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063',
            '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174',
            '0xc2132d05d31c914a87c6611c10748aeb04b58e8f',
            '0x82af49447d8a07e3bd95bd0d56f35241523fbab1',
            '0x2f2a2543b76a4166549f7aab2e75bef0aefc5b0f',
            '0xda10009cbd5d07dd0cecc66161fc93d7c9000da1',
            '0xaf88d065e77c8cc2239327c5edb3a432268e5831',
            '0xfd086bc7cd5c481dcc9c85ebe478a1c0b69fcbb9'
        ))
        """
        
        try:
            # Get existing combinations
            print("Fetching existing deposit_id and destination_chain_id combinations...")
            self.cursor.execute(get_existing_combinations_query)
            existing_combinations = set((row[0], row[1]) for row in self.cursor.fetchall())
            
            # Get new combinations
            print("Fetching new deposit_id and destination_chain_id combinations...")
            self.cursor.execute(get_new_combinations_query)
            new_combinations = [row for row in self.cursor.fetchall()]
            
            total_inserted = 0
            
            # Process in batches
            for i in range(0, len(new_combinations), batch_size):
                batch_combinations = new_combinations[i:i+batch_size]
                
                formatted_query = insert_query.format(','.join(['(%s,%s)'] * len(batch_combinations)))
                flattened_combinations = [item for sublist in batch_combinations for item in sublist]
                
                try:
                    print(f"Processing batch {i//batch_size + 1}, combinations {batch_combinations[0]} to {batch_combinations[-1]}")
                    self.cursor.execute(formatted_query, flattened_combinations)
                    self.conn.commit()
                    inserted = self.cursor.rowcount
                    total_inserted += inserted
                    print(f"Inserted {inserted} rows in this batch. Total inserted: {total_inserted}")
                except mysql.connector.Error as err:
                    print(f"Error processing batch: {err}")
                    self.conn.rollback()
            
            print(f"Finished processing. Total new rows inserted: {total_inserted}")
            return total_inserted
        
        except mysql.connector.Error as err:
            print(f"Error in insert_relay_data: {err}")
            self.conn.rollback()
            return 0
    
    def get_data(self, query):
        try:
            self.cursor.execute(query)
            results = self.cursor.fetchall()
            columns = [col[0] for col in self.cursor.description]
            return [dict(zip(columns, row)) for row in results]

        except mysql.connector.Error as err:
            print(f"Error getting data: {err}" + query)
            return []
        
    def analyze_relay_performance(self):
        return self.get_data(self.general_performance_query)
    
    def get_daily_data(self):
        return self.get_data(self.general_daily_data_query)
    
    def process_target_combo(self):
        self.execute_query("truncate table target_combo")
        self.execute_query(self.target_combo_query)
        return self.get_data("""SELECT * FROM target_combo""")
    
    def process_target_relayer_combo(self):
        self.execute_query("DROP TABLE IF EXISTS target_relayer_combo;")
        self.execute_query(self.target_relayer_combo_query)
        return self.get_data("""SELECT * FROM target_relayer_combo""")
    
