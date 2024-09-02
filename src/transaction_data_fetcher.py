import json
from web3 import Web3
from datetime import datetime
from db_operations import DatabaseOperations
from web3.middleware import geth_poa_middleware

def load_config(filename):
    with open(filename, 'r') as f:
        return json.load(f)

def setup_web3(rpc_endpoint):
    w3 = Web3(Web3.HTTPProvider(rpc_endpoint))
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    return w3

def fetch_transaction_details(w3, transaction_hash, chain_id, event_type, db_ops):
    try:
        tx = w3.eth.get_transaction(transaction_hash)
        tx_receipt = w3.eth.get_transaction_receipt(transaction_hash)
        block = w3.eth.get_block(tx['blockNumber'])
        
        block_timestamp = datetime.fromtimestamp(block['timestamp'])
        gas_used = tx_receipt['gasUsed']
        gas_price = tx['gasPrice']
        total_gas_fee = gas_used * gas_price

        inserted = db_ops.insert_transaction_details(
            chain_id,
            transaction_hash,
            block_timestamp,
            gas_used,
            gas_price,
            total_gas_fee,
            event_type
        )
        
        if not inserted:
            print(f"Failed to insert transaction details for {transaction_hash}")            
    
    except Exception as e:
        print(f"Error fetching transaction details for {transaction_hash}: {e}")

def process_transactions(db_ops, chain_config):
    w3 = setup_web3(chain_config['rpc_endpoint'])
    chain_id = chain_config['chainid']

    fill_txs = db_ops.get_unprocessed_transactions('filled_v3_relays', chain_id)
    deposit_txs = db_ops.get_unprocessed_transactions('v3_funds_deposited', chain_id)

    print(f"Processing {len(fill_txs)} fill transactions for chain {chain_id}")
    for tx_hash in fill_txs:
        fetch_transaction_details(w3, tx_hash, chain_id, 'fill', db_ops)

    print(f"Processing {len(deposit_txs)} deposit transactions for chain {chain_id}")
    for tx_hash in deposit_txs:
        fetch_transaction_details(w3, tx_hash, chain_id, 'deposit', db_ops)

def main():
    config = load_config('config.json')

    db_ops = DatabaseOperations()

    try:
        db_ops.connect()

        for chain_config in config:
            process_transactions(db_ops, chain_config)

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        db_ops.close()

    print("Transaction details fetching completed.")

if __name__ == "__main__":
    main()