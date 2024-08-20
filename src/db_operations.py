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
        (input_token, output_token, input_amount, output_amount, repayment_chain_id, 
        origin_chain_id, deposit_id, fill_deadline, exclusivity_deadline, exclusive_relayer, 
        relayer, depositor, recipient, message, transaction_hash, 
        block_number, log_index)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                    args['inputToken'],
                    args['outputToken'],
                    str(args['inputAmount']),
                    str(args['outputAmount']),
                    str(args['repaymentChainId']),
                    str(chain_id),  
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
    def insert_deposit_events(self, events, chain_id):
        query = """
        INSERT IGNORE INTO v3_funds_deposited 
        (chain_id, block_number, transaction_hash, log_index, input_token, output_token, 
        input_amount, output_amount, destination_chain_id, deposit_id, quote_timestamp, 
        fill_deadline, exclusivity_deadline, depositor, recipient, exclusive_relayer, message)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
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
            for event in events
        ]
        
        try:
            with self.conn.cursor() as cursor:
                cursor.executemany(query, values)
            self.conn.commit()
            return len(events), cursor.rowcount
        except Exception as e:
            print(f"Error inserting V3FundsDeposited events: {e}")
            self.conn.rollback()
            return 0, 0
        
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
            WHERE td.transaction_hash IS NULL AND t.origin_chain_id = %s
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
    
    def fetch_and_insert_relay_data(self):
        create_temp_table_query = """
        CREATE TEMPORARY TABLE IF NOT EXISTS temp_filled_relays (
            deposit_id INT,
            origin_chain_id INT,
            input_token VARCHAR(42),
            output_token VARCHAR(42),
            input_amount DECIMAL(65,0),
            output_amount DECIMAL(65,0),
            relayer VARCHAR(42),
            depositor VARCHAR(42),
            transaction_hash VARCHAR(66),
            PRIMARY KEY (deposit_id, depositor)
        )
        """

        insert_temp_table_query = """
        INSERT INTO temp_filled_relays
        SELECT deposit_id, origin_chain_id, input_token, output_token, input_amount, output_amount, relayer, depositor, transaction_hash
        FROM filled_v3_relays
        """

        fetch_and_insert_query = """
        INSERT IGNORE INTO relay_analysis 
        (destination_chain_id, origin_chain_id, input_token, output_token, 
        input_amount, output_amount, deposit_id, relayer, depositor, 
        recipient, gas_fee, earned_amount)
        SELECT 
            d.destination_chain_id, d.chain_id AS origin_chain_id, 
            f.input_token, f.output_token, f.input_amount, f.output_amount, 
            d.deposit_id, f.relayer, d.depositor, d.recipient,
            COALESCE(t.total_gas_fee, 0) AS gas_fee,
            (f.input_amount - f.output_amount - COALESCE(t.total_gas_fee, 0)) AS earned_amount
        FROM 
            v3_funds_deposited d
        JOIN
            temp_filled_relays f ON d.deposit_id = f.deposit_id AND d.depositor = f.depositor
        LEFT JOIN
            transaction_details t ON f.transaction_hash = t.transaction_hash AND f.origin_chain_id = t.chain_id AND t.event_type = 'fill'
        """

        try:
            print("Creating temporary table...")
            self.cursor.execute(create_temp_table_query)
            
            print("Populating temporary table...")
            self.cursor.execute(insert_temp_table_query)
            self.conn.commit()
            
            print("Fetching and inserting data...")
            self.cursor.execute(fetch_and_insert_query)
            self.conn.commit()
            
            total_inserted = self.cursor.rowcount
            print(f"Finished processing. Total rows inserted: {total_inserted}")

        except mysql.connector.Error as err:
            print(f"Error in fetch_and_insert_relay_data: {err}")
            self.conn.rollback()
        finally:
            print("Dropping temporary table...")
            self.cursor.execute("DROP TEMPORARY TABLE IF EXISTS temp_filled_relays")
            self.conn.commit()

        return total_inserted
    
    def insert_transaction_details_zetta(self, chain_id, transaction_hash, block_timestamp, gas_used, gas_price, total_gas_fee, event_type):
        query = """
        INSERT IGNORE INTO transaction_details_zetta 
        (chain_id, transaction_hash, block_timestamp, gas_used, gas_price, total_gas_fee, event_type)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        data = (chain_id, transaction_hash, block_timestamp, gas_used, gas_price, total_gas_fee, event_type)
        
        try:
            self.cursor.execute(query, data)
            self.conn.commit()
            return self.cursor.rowcount
        except mysql.connector.Error as err:
            print(f"Error inserting Zetta transaction details: {err}")
            self.conn.rollback()
            return 0

    def get_unprocessed_transactions_zetta(self):
        query = """
        SELECT 
            CASE 
                WHEN f.transaction_hash IS NOT NULL THEN f.transaction_hash 
                ELSE d.transaction_hash 
            END AS transaction_hash,
            CASE 
                WHEN f.transaction_hash IS NOT NULL THEN 'fill' 
                ELSE 'deposit' 
            END AS event_type,
            COALESCE(d.chain_id, f.origin_chain_id) AS chain_id,
            f.repayment_chain_id
        FROM 
            v3_funds_deposited d
        FULL OUTER JOIN 
            filled_v3_relays f ON d.deposit_id = f.deposit_id
        LEFT JOIN 
            transaction_details_zetta t ON 
                (t.transaction_hash = d.transaction_hash AND t.chain_id = d.chain_id) OR
                (t.transaction_hash = f.transaction_hash AND t.chain_id = f.repayment_chain_id)
        WHERE 
            t.transaction_hash IS NULL
        """
        self.cursor.execute(query)
        return self.cursor.fetchall()
    
    def get_unique_blocks(self):
        query = """
        SELECT DISTINCT chain_id, block_number FROM (
            SELECT origin_chain_id as chain_id, block_number FROM filled_v3_relays
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