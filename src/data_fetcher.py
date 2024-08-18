import json
from web3 import Web3
import time
from datetime import datetime, timedelta
from db_operations import DatabaseOperations
from web3.middleware import geth_poa_middleware


def load_config(filename):
    with open(filename, 'r') as f:
        return json.load(f)

def load_abi(filename):
    with open(filename, 'r') as f:
        return json.load(f)

def binary_search_block(w3, target_timestamp, left, right):
    while left <= right:
        mid = (left + right) // 2
        mid_block = w3.eth.get_block(mid)
        if mid_block['timestamp'] == target_timestamp:
            return mid
        if mid_block['timestamp'] < target_timestamp:
            left = mid + 1
        else:
            right = mid - 1
    return right

def get_block_range(w3, start_time, end_time):
    latest_block = w3.eth.get_block('latest', full_transactions=False)
    latest_block_number = latest_block['number']
    latest_timestamp = latest_block['timestamp']

    if start_time > latest_timestamp:
        return None, None  

    if end_time > latest_timestamp:
        end_time = latest_timestamp

    avg_block_time = 15
    est_start_block = latest_block_number - (latest_timestamp - start_time) // avg_block_time
    est_end_block = latest_block_number - (latest_timestamp - end_time) // avg_block_time

    start_block = binary_search_block(w3, start_time, max(0, est_start_block - 1000), min(latest_block_number, est_start_block + 1000))
    end_block = binary_search_block(w3, end_time, max(0, est_end_block - 1000), min(latest_block_number, est_end_block + 1000))

    return start_block, end_block

def setup_web3_and_contract(chain_config, contract_address, contract_abi):
    w3 = Web3(Web3.HTTPProvider(chain_config['rpc_endpoint']))
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    contract = w3.eth.contract(address=contract_address, abi=contract_abi)
    return w3, contract

def fetch_events_batch(contract, from_block, to_block):
    filled_events = contract.events.FilledV3Relay.get_logs(fromBlock=from_block, toBlock=to_block)
    deposited_events = contract.events.V3FundsDeposited.get_logs(fromBlock=from_block, toBlock=to_block)
    return filled_events, deposited_events

def print_progress(chain_id, events_count, progress, total_duration, estimated_time_left):
    print(f"Chain {chain_id}: Processed {events_count} events. Progress: {progress:.2f}%")
    print(f"Total duration: {total_duration:.2f} seconds")
    print(f"Estimated time left: {timedelta(seconds=int(estimated_time_left))}")

def fetch_events(chain_config, start_time, end_time, contract_abi):
    print(f"Start fetching. Start time: {start_time}, End time: {end_time}")
    w3, contract = setup_web3_and_contract(chain_config, chain_config['contract_address'], contract_abi)

    start_block, end_block = get_block_range(w3, start_time, end_time)
    if start_block is None or end_block is None:
        print(f"No valid block range found for chain {chain_config['chainid']}")
        return [], []

    print(f"Fetching events for chain {chain_config['chainid']} from block {start_block} to {end_block}")

    filled_events = []
    deposited_events = []
    batch_size = 1000
    total_blocks = end_block - start_block + 1
    fetch_start_time = time.time()

    for i in range(start_block, end_block + 1, batch_size):
        from_block = i
        to_block = min(i + batch_size - 1, end_block)
        
        batch_filled, batch_deposited = fetch_events_batch(contract, from_block, to_block)
        filled_events.extend(batch_filled)
        deposited_events.extend(batch_deposited)
        
        total_duration = time.time() - fetch_start_time
        progress = (to_block - start_block + 1) / total_blocks * 100
        estimated_time_left = (total_duration / progress) * (100 - progress) if progress > 0 else 0
        
        print_progress(chain_config['chainid'], len(filled_events) + len(deposited_events), progress, total_duration, estimated_time_left)
        
        time.sleep(0.1)

    total_fetch_time = time.time() - fetch_start_time
    print(f"Total fetch time for chain {chain_config['chainid']}: {total_fetch_time:.2f} seconds")
    print(f"Average time per block: {total_fetch_time / total_blocks:.4f} seconds")
    print(f"Total FilledV3Relay events fetched: {len(filled_events)}")
    print(f"Total V3FundsDeposited events fetched: {len(deposited_events)}")

    return filled_events, deposited_events

def main():
    config = load_config('config.json')
    contract_abi = load_abi('abi.json')

    db_config = {
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': 'your_new_password',
        'database': 'across_relay'
    }

    end_time = int(time.time())
    start_time = end_time - 24 * 60 * 60 * 30 

    db_ops = DatabaseOperations(db_config)

    try:
        db_ops.connect()

        total_inserted = 0
        total_processed = 0

        for chain_config in config:
            filled_events, deposited_events = fetch_events(chain_config, start_time, end_time, contract_abi)
            
            print(f"Processing {len(filled_events)} FilledV3Relay events for chain {chain_config['chainid']}")
            processed_filled, inserted_filled = db_ops.insert_fill_events(filled_events, chain_config['chainid'])
            
            print(f"Processing {len(deposited_events)} V3FundsDeposited events for chain {chain_config['chainid']}")
            processed_deposited, inserted_deposited = db_ops.insert_deposit_events(deposited_events, chain_config['chainid'])
            
            total_processed += processed_filled + processed_deposited
            total_inserted += inserted_filled + inserted_deposited

            print(f"Total rows inserted so far: {total_inserted}")

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        db_ops.close()

    print(f"Script completed. Total rows processed: {total_processed}. Total new rows inserted: {total_inserted}")

if __name__ == "__main__":
    main()