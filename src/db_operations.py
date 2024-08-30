import mysql.connector
from datetime import datetime

class DatabaseOperations:
    def __init__(self, db_config):
        self.db_config = db_config
        self.conn = None
        self.cursor = None

    def connect(self):
        self.conn = mysql.connector.connect(**self.db_config)
        self.cursor = self.conn.cursor()

    def close(self):
        if self.cursor:
            self.cursor.close()
        if self.conn and self.conn.is_connected():
            self.conn.close()
            print("MySQL connection is closed")

    
    def insert_fill_events(self, events, chain_id):
        insert_query = """
        INSERT IGNORE INTO filled_v3_relays 
        (chain_id, input_token, output_token, input_amount, output_amount, repayment_chain_id, 
        origin_chain_id, deposit_id, fill_deadline, exclusivity_deadline, exclusive_relayer, 
        relayer, depositor, recipient, message, transaction_hash, 
        block_number, log_index)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        total_inserted = 0
        total_processed = 0
        batch_size = 100

        try:
            for index, event in enumerate(events, 1):
                args = event['args']
                fill_deadline = datetime.fromtimestamp(args['fillDeadline'])
                exclusivity_deadline = datetime.fromtimestamp(args['exclusivityDeadline'])
                
                data = (
                    str(chain_id), 
                    args['inputToken'],
                    args['outputToken'],
                    str(args['inputAmount']),
                    str(args['outputAmount']),
                    str(args['repaymentChainId']),
                    str(args['originChainId']), 
                    str(args['depositId']),
                    fill_deadline,
                    exclusivity_deadline,
                    args['exclusiveRelayer'],
                    args['relayer'],
                    args['depositor'],
                    args['recipient'],
                    args['message'].hex(),
                    event['transactionHash'].hex(),
                    event['blockNumber'],
                    event['logIndex']
                )
                self.cursor.execute(insert_query, data)
                total_processed += 1

                if index % batch_size == 0:
                    self.conn.commit()
                    total_inserted += self.cursor.rowcount
                    print(f"Processed {batch_size} rows. Newly inserted: {self.cursor.rowcount}. Total processed: {total_processed}")

            
            self.conn.commit()
            total_inserted += self.cursor.rowcount
            print(f"Finished processing chain {chain_id}. Newly inserted: {self.cursor.rowcount}. Total processed: {total_processed}")

        except mysql.connector.Error as err:
            print(f"MySQL Error: {err}")
            self.conn.rollback()
            raise

        return total_processed, total_inserted
    
    def insert_deposit_events(self, events, chain_id, batch_size=100):
        query = """
        INSERT IGNORE INTO v3_funds_deposited 
        (chain_id, block_number, transaction_hash, log_index, input_token, output_token, 
        input_amount, output_amount, destination_chain_id, deposit_id, quote_timestamp, 
        fill_deadline, exclusivity_deadline, depositor, recipient, exclusive_relayer, message)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        total_events = len(events)
        total_inserted = 0
        
        for i in range(0, total_events, batch_size):
            batch = events[i:i+batch_size]
            values = [
                (
                    chain_id,
                    event['blockNumber'],
                    event['transactionHash'].hex(),
                    event['logIndex'],
                    event['args']['inputToken'],
                    event['args']['outputToken'],
                    str(event['args']['inputAmount']),
                    str(event['args']['outputAmount']),
                    event['args']['destinationChainId'],
                    event['args']['depositId'],
                    event['args']['quoteTimestamp'],
                    event['args']['fillDeadline'],
                    event['args']['exclusivityDeadline'],
                    event['args']['depositor'],
                    event['args']['recipient'],
                    event['args']['exclusiveRelayer'],
                    event['args']['message'].hex()
                )
                for event in batch
            ]
            
            try:
                with self.conn.cursor() as cursor:
                    cursor.executemany(query, values)
                self.conn.commit()
                inserted = cursor.rowcount
                total_inserted += inserted
                print(f"Inserted {inserted} out of {len(batch)} events in this batch. Total inserted: {total_inserted}/{total_events}")
            except Exception as e:
                print(f"Error inserting batch of V3FundsDeposited events: {e}")
                self.conn.rollback()
        
        return total_events, total_inserted
        
    def insert_transaction_details(self, chain_id, transaction_hash, block_timestamp, gas_used, gas_price, total_gas_fee, event_type):
        query = """
        INSERT IGNORE INTO transaction_details 
        (chain_id, transaction_hash, block_timestamp, gas_used, gas_price, total_gas_fee, event_type)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        data = (chain_id, transaction_hash, block_timestamp, gas_used, gas_price, total_gas_fee, event_type)
        
        try:
            self.cursor.execute(query, data)
            self.conn.commit()
            return self.cursor.rowcount
        except mysql.connector.Error as err:
            print(f"Error inserting transaction details: {err}")
            self.conn.rollback()
            return 0

    def get_unprocessed_transactions(self, table_name, chain_id):
        if table_name == 'filled_v3_relays':
            query = """
            SELECT DISTINCT t.transaction_hash
            FROM filled_v3_relays t
            LEFT JOIN transaction_details td ON t.transaction_hash = td.transaction_hash AND td.chain_id = %s
            WHERE td.transaction_hash IS NULL AND t.chain_id = %s
            """
        elif table_name == 'v3_funds_deposited':
            query = """
            SELECT DISTINCT t.transaction_hash
            FROM v3_funds_deposited t
            LEFT JOIN transaction_details td ON t.transaction_hash = td.transaction_hash AND td.chain_id = %s
            WHERE td.transaction_hash IS NULL AND t.chain_id = %s
            """
        else:
            raise ValueError(f"Unknown table name: {table_name}")

        self.cursor.execute(query, (chain_id, chain_id))
        return [row[0] for row in self.cursor.fetchall()]
    
    def fetch_and_insert_relay_data(self, batch_size=1000):
        get_deposit_ids_query = """
        SELECT DISTINCT f.deposit_id
        FROM filled_v3_relays f
        LEFT JOIN relay_analysis ra ON f.deposit_id = ra.deposit_id
        WHERE ra.deposit_id IS NULL
        ORDER BY f.deposit_id
        """
        
        self.cursor.execute(get_deposit_ids_query)
        all_deposit_ids = [row[0] for row in self.cursor.fetchall()]
        
        total_inserted = 0
        
        for i in range(0, len(all_deposit_ids), batch_size):
            batch_deposit_ids = all_deposit_ids[i:i+batch_size]
            
            insert_query = """
            INSERT IGNORE INTO relay_analysis 
            (destination_chain_id, origin_chain_id, input_token, output_token, 
            input_amount, output_amount, deposit_id, relayer, depositor, 
            recipient, gas_fee, earned_amount, priority_fee, input_amount_usd, output_amount_usd, earned_amount_usd)
            SELECT 
                d.destination_chain_id, f.origin_chain_id, 
                f.input_token, f.output_token, f.input_amount, f.output_amount, 
                f.deposit_id, f.relayer, f.depositor, d.recipient,
                COALESCE(t.total_gas_fee, 0) AS gas_fee,
                (f.input_amount - f.output_amount - COALESCE(t.total_gas_fee, 0)) AS earned_amount,
                GREATEST(0, t.gas_price - b.base_fee_per_gas) * t.gas_used AS priority_fee,
                f.input_amount * COALESCE(p1.price_usd, 1) AS input_amount_usd,
                f.output_amount * COALESCE(p2.price_usd, 1) AS output_amount_usd,
                (f.input_amount * COALESCE(p1.price_usd, 1) - f.output_amount * COALESCE(p2.price_usd, 1) - COALESCE(t.total_gas_fee, 0)) AS earned_amount_usd
            FROM 
                filled_v3_relays f
            JOIN
                v3_funds_deposited d ON f.deposit_id = d.deposit_id AND f.chain_id = d.destination_chain_id
            JOIN
                transaction_details t ON f.transaction_hash = t.transaction_hash AND f.chain_id = t.chain_id
            JOIN
                block_details b ON t.chain_id = b.chain_id AND b.block_number = f.block_number
            JOIN
                (SELECT token_address, price_usd FROM token_prices) p1 
                ON f.input_token = p1.token_address
            JOIN
                (SELECT token_address, price_usd FROM token_prices) p2 
                ON f.output_token = p2.token_address
            WHERE f.deposit_id IN ({})
            """
            
            formatted_query = insert_query.format(','.join(['%s'] * len(batch_deposit_ids)))
            
            try:
                print(f"Processing batch {i//batch_size + 1}, deposit_ids {batch_deposit_ids[0]} to {batch_deposit_ids[-1]}")
                self.cursor.execute(formatted_query, batch_deposit_ids)
                self.conn.commit()
                inserted = self.cursor.rowcount
                total_inserted += inserted
                print(f"Inserted {inserted} rows in this batch. Total inserted: {total_inserted}")
            except mysql.connector.Error as err:
                print(f"Error processing batch: {err}")
                self.conn.rollback()
        
        print(f"Finished processing. Total rows inserted: {total_inserted}")
        return total_inserted
    def get_unique_blocks(self):
        query = """
        SELECT DISTINCT chain_id, block_number FROM (
            SELECT chain_id, block_number FROM filled_v3_relays
            UNION
            SELECT chain_id, block_number FROM v3_funds_deposited
        ) as combined
        WHERE (chain_id, block_number) NOT IN (
            SELECT chain_id, block_number FROM block_details
        )
        """
        self.cursor.execute(query)
        return self.cursor.fetchall()
    
    def insert_block_details(self, chain_id, block_details):
        insert_query = """
        INSERT IGNORE INTO block_details 
        (chain_id, block_number, block_timestamp, gas_used, gas_limit, base_fee_per_gas)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        try:
            self.cursor.executemany(insert_query, block_details)
            self.conn.commit()
            print(f"Inserted {self.cursor.rowcount} block details for chain {chain_id}")
        except Exception as e:
            print(f"Error inserting block details for chain {chain_id}: {e}")
            self.conn.rollback()