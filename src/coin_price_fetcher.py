import json
import requests
import mysql.connector
from datetime import datetime
from web3 import Web3
from web3.exceptions import ContractLogicError


CMC_API_KEY = ''  
CMC_BASE_URL = 'https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest'


with open('config.json', 'r') as f:
    config = json.load(f)


web3_instances = {chain_config['chainid']: Web3(Web3.HTTPProvider(chain_config['rpc_endpoint'])) for chain_config in config}


ABI = [
    {
        "inputs": [],
        "name": "decimals",
        "outputs": [{"internalType": "uint8", "name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "symbol",
        "outputs": [{"internalType": "string", "name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "name",
        "outputs": [{"internalType": "string", "name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "totalSupply",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]


SYMBOL_MAPPING = {
    '0xe5D7C2a44FfDDf6b295A15c148167daaAf5Cf34f': 'WETH',
    '0x3355df6D4c9C3035724Fd0e3914dE96A5a83aaf4': 'USDC',
    '0x493257fD37EDB34451f62EDf8D2a0C418852bA4C': 'USDT',
    '0x5AEa5775959fBC2557Cc8789bC1bf90A239D9a91': 'WETH',
    '0x5300000000000000000000000000000000000004': 'WETH',
    '0x4300000000000000000000000000000000000004': 'WETH',
    '0xA219439258ca9da29E9Cc4cE5596924745e12B93': 'USDT',
    '0xBBeB516fb02a01611cBBE0453Fe3c580D7281011': 'WBTC',
    '0xd988097fb8612cc24eeC14542bC03424c656005f': 'USDC',
    '0x176211869cA2b568f2A7D4EE941E073a821EE1ff': 'USDC',
    '0x4300000000000000000000000000000000000003': 'USDB',
    '0x3aAB2285ddcDdaD8edf438C1bAB47e1a9D05a9b4': 'WBTC',
    '0xf0F161fDA2712DB8b566946122a5af183995e2eD': 'USDT',
    '0xac485391EB2d7D88253a7F1eF18C37f4242D1A24': 'LSK',
    '0xF7bc58b8D8f97ADC129cfC4c9f45Ce3C0E1D2692': 'WBTC',
    '0x4AF15ec2A0BD43Db75dd04E62FAA3B8EF36b00d5': 'DAI',
    '0x4B9eb6c0b6ea15176BBF62841C6B2A8a398cb656': 'DAI',
    '0xcDd475325D6F564d27247D1DddBb0DAc6fA0a5CF': 'WBTC',
    '0x06eFdBFf2a14a7c8E15944D1F4A48F9F95F663A4': 'USDC',
    '0xf55BEC9cafDbE8730f096Aa55dad6D22d44099Df': 'USDT',
    '0x3C1BCa5a656e69edCD0D4E36BEbb3FcDAcA60Cf1': 'WBTC',
    '0xCccCCccc7021b32EBb4e8C08314bD62F7c653EC4': 'USDC',
    '0x9f8F72aA9304c8B593d555F12eF6589cC3A579A2': 'MKR',
    '0xf951E335afb289353dc249e82926178EaC7DEd78': 'WETH',
    '0xD9A442856C234a39a81a089C06451EBAa4306a72': 'WETH',
    '0xbf5495Efe5DB9ce00f80364C8B423567e58d2110': 'WETH',
    '0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84': 'WETH',
    '0x582d872A1B094FC48F5DE31D3B73F2D9bE47def1': 'TON',
    '0xFAe103DC9cf190eD75350761e95403b7b8aFa6c0': 'WETH',
    '0xCd5fE23C85820F7B72D0926FC9b05b43E359b7ee': 'WETH',
    '0x6De037ef9aD2725EB40118Bb1702EBb27e4Aeb24': 'RENDER',
    '0x83F20F44975D03b1b09e64809B757c47f942BEeA': 'DAI',
    '0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA': 'USDC',
    '0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cf0DEc22': 'WETH',
    '0x2Da56AcB9Ea78330f947bD57C54119Debda7AF71': 'MOG'
}


def get_token_symbol(token_address):
    if token_address in SYMBOL_MAPPING:
        symbol = SYMBOL_MAPPING[token_address]
        print(f"Found symbol {symbol} for token {token_address} in predefined mapping")
        return symbol
    
    for chain_id, web3 in web3_instances.items():
        try:
            contract = web3.eth.contract(address=Web3.to_checksum_address(token_address), abi=ABI)
            symbol = contract.functions.symbol().call()
            print(f"Successfully got symbol {symbol} for token {token_address} on chain {chain_id}")
            return symbol
        except Exception as e:
            print(f"Failed to get symbol for token {token_address} on chain {chain_id}: {e}")
    print(f"Failed to get symbol for token {token_address} on all chains")
    return None

def get_token_price(symbol):
    headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': CMC_API_KEY,
    }
    params = {
        'symbol': symbol,
        'convert': 'USD'
    }
    
    try:
        response = requests.get(CMC_BASE_URL, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        if symbol in data['data']:
            return data['data'][symbol][0]['quote']['USD']['price']
        else:
            print(f"Symbol {symbol} not found in CMC response")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching price for {symbol}: {e}")
        return None
    except (KeyError, IndexError) as e:
        print(f"Error parsing CMC response for {symbol}: {e}")
        return None

def insert_token_price(cursor, token_address, price_date, price_usd):
    query = """
    INSERT INTO token_prices (token_address, price_date, price_usd)
    VALUES (%s, %s, %s)
    ON DUPLICATE KEY UPDATE price_usd = VALUES(price_usd)
    """
    cursor.execute(query, (token_address, price_date, price_usd))

def fetch_unique_tokens(cursor):
    print("Fetching unique token addresses")
    query = """
    SELECT DISTINCT token_address
    FROM (
        SELECT input_token AS token_address
        FROM filled_v3_relays
        UNION
        SELECT output_token AS token_address
        FROM filled_v3_relays
    ) AS all_tokens
    WHERE token_address NOT IN (
        SELECT token_address
        FROM token_prices
    )
    """
    cursor.execute(query)
    return [row[0] for row in cursor.fetchall()]

def update_token_prices(conn, cursor, price_date):
    print('Updating token prices')
    unique_tokens = fetch_unique_tokens(cursor)
    
    for token_address in unique_tokens:
        try:
            symbol = get_token_symbol(token_address)
            if symbol is None:
                continue
            price = get_token_price(symbol)
            if price is not None:
                insert_token_price(cursor, token_address, price_date, price)
        except Exception as e:
            print(f"Error processing token {token_address}: {e}")
    
    conn.commit()


db_config = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'your_new_password',
    'database': 'across_relay'
}


if __name__ == "__main__":
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    price_date = datetime.now().date()

    update_token_prices(conn, cursor, price_date)

    cursor.close()
    conn.close()