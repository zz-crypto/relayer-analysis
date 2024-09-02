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

def get_block_range(chain_id, w3, db_ops):
    latest_block = w3.eth.get_block('latest', full_transactions=False)
    latest_block_number = latest_block['number']

    start_block = db_ops.get_last_synced_block(chain_id)

    if start_block is None:
        print(f"No last synced block found for chain {chain_id}. Starting from the latest block.")
        start_block = latest_block_number
    start_block = min(start_block, latest_block_number)

    return start_block, latest_block_number

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

def fetch_events_details(chain_config, contract_abi, db_ops):
    print(f"Start fetching.")
    w3, contract = setup_web3_and_contract(chain_config, chain_config['contract_address'], contract_abi)

    start_block, end_block = get_block_range(chain_config['chainid'], w3, db_ops)
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

def fetch_block_details(w3, chain_id, block_numbers, db_ops, batch_size=100):
    total_blocks = len(block_numbers)
    processed_blocks = 0

    for i in range(0, total_blocks, batch_size):
        batch = block_numbers[i:i+batch_size]
        block_details = []
        for block_number in batch:
            try:
                block = w3.eth.get_block(block_number)
                block_details.append((
                    chain_id,
                    block_number,
                    datetime.fromtimestamp(block['timestamp']),
                    block['gasUsed'],
                    block['gasLimit'],
                    block.get('baseFeePerGas', 0) 
                ))
            except Exception as e:
                print(f"Error fetching block {block_number} for chain {chain_id}: {e}")
        
        db_ops.insert_block_details(chain_id, block_details)
        
        processed_blocks += len(batch)
        print(f"Processed {processed_blocks}/{total_blocks} blocks for chain {chain_id}")

    print(f"Finished processing all blocks for chain {chain_id}")

def main(fetch_events=True, fetch_blocks=True):
    config = load_config('config.json')
    contract_abi = load_abi('abi.json')

    end_time = int(time.time())
    start_time = end_time - 24 * 60 * 60 * 2

    db_ops = DatabaseOperations()

    try:
        db_ops.connect()

        total_inserted = 0
        total_processed = 0

        if fetch_events:
            print(f"Event fetching started.")
            for chain_config in config:
                filled_events, deposited_events = fetch_events_details(chain_config, contract_abi, db_ops)
                
                print(f"Processing {len(filled_events)} FilledV3Relay events for chain {chain_config['chainid']}")
                processed_filled, inserted_filled = db_ops.insert_fill_events(filled_events, chain_config['chainid'])
                
                print(f"Processing {len(deposited_events)} V3FundsDeposited events for chain {chain_config['chainid']}")
                processed_deposited, inserted_deposited = db_ops.insert_deposit_events(deposited_events, chain_config['chainid'])
                
                total_processed += processed_filled + processed_deposited
                total_inserted += inserted_filled + inserted_deposited

                print(f"Total rows inserted so far: {total_inserted}")

            print(f"Event fetching completed. Total rows processed: {total_processed}. Total new rows inserted: {total_inserted}")

        if fetch_blocks:
            print("Block fetching started.")
            unique_blocks = db_ops.get_unique_blocks()
            
            blocks_by_chain = {}
            for chain_id, block_number in unique_blocks:
                if chain_id not in blocks_by_chain:
                    blocks_by_chain[chain_id] = []
                blocks_by_chain[chain_id].append(block_number)

            for chain_config in config:
                chain_id = chain_config['chainid']
                if chain_id in blocks_by_chain:
                    w3, _ = setup_web3_and_contract(chain_config, chain_config['contract_address'], contract_abi)
                    fetch_block_details(w3, chain_id, blocks_by_chain[chain_id], db_ops, batch_size=100)

            print("Block fetching completed.")

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        db_ops.close()

    print("Script execution completed.")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fetch events and block details for Across protocol")
    parser.add_argument('--events', action='store_true', help='Fetch events')
    parser.add_argument('--blocks', action='store_true', help='Fetch block details')
    args = parser.parse_args()

    if not args.events and not args.blocks:
        args.events = True
        args.blocks = True

    main(fetch_events=args.events, fetch_blocks=args.blocks)