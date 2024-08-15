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
        (destination_chain_id, relayer, input_token, output_token, input_amount, output_amount, deposit_id, fill_deadline)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        total_inserted = 0
        total_processed = 0
        batch_size = 100

        try:
            for index, event in enumerate(events, 1):
                args = event['args']
                fill_deadline = datetime.fromtimestamp(args['fillDeadline'])
                
                data = (
                    str(chain_id),
                    args['relayer'],
                    args['inputToken'],
                    args['outputToken'],
                    str(args['inputAmount']),
                    str(args['outputAmount']),
                    str(args['depositId']),
                    fill_deadline
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