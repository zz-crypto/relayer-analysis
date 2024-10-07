CREATE DATABASE IF NOT EXISTS across_relay;

USE across_relay;

CREATE TABLE IF NOT EXISTS filled_v3_relays (
    id INT AUTO_INCREMENT PRIMARY KEY,
    chain_id INT NOT NULL,
    input_token VARCHAR(42) NOT NULL,
    output_token VARCHAR(42) NOT NULL,
    input_amount DECIMAL(65,0) NOT NULL,
    output_amount DECIMAL(65,0) NOT NULL,
    repayment_chain_id INT NOT NULL,
    origin_chain_id INT NOT NULL,
    deposit_id INT NOT NULL,
    fill_deadline DATETIME NOT NULL,
    exclusivity_deadline DATETIME NOT NULL,
    exclusive_relayer VARCHAR(42) NOT NULL,
    relayer VARCHAR(42) NOT NULL,
    depositor VARCHAR(42) NOT NULL,
    recipient VARCHAR(42) NOT NULL,
    message TEXT,
    transaction_hash VARCHAR(66) NOT NULL,
    block_number INT NOT NULL,
    log_index INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_event (origin_chain_id, transaction_hash, log_index)
);

CREATE TABLE IF NOT EXISTS v3_funds_deposited (
    id INT AUTO_INCREMENT PRIMARY KEY,
    chain_id INT NOT NULL,
    block_number INT NOT NULL,
    transaction_hash VARCHAR(66) NOT NULL,
    log_index INT NOT NULL,
    input_token VARCHAR(42) NOT NULL,
    output_token VARCHAR(42) NOT NULL,
    input_amount VARCHAR(78) NOT NULL,
    output_amount VARCHAR(78) NOT NULL,
    destination_chain_id INT NOT NULL,
    deposit_id INT NOT NULL,
    quote_timestamp INT NOT NULL,
    fill_deadline INT NOT NULL,
    exclusivity_deadline INT NOT NULL,
    depositor VARCHAR(42) NOT NULL,
    recipient VARCHAR(42) NOT NULL,
    exclusive_relayer VARCHAR(42) NOT NULL,
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY `unique_event` (chain_id, transaction_hash, log_index)
);

CREATE TABLE IF NOT EXISTS transaction_details (
    id INT AUTO_INCREMENT PRIMARY KEY,
    chain_id INT NOT NULL,
    transaction_hash VARCHAR(66) NOT NULL,
    block_timestamp DATETIME NOT NULL,
    gas_used BIGINT NOT NULL,
    gas_price DECIMAL(65,0) NOT NULL,
    total_gas_fee DECIMAL(65,0) NOT NULL,
    event_type ENUM('deposit', 'fill') NOT NULL,
    UNIQUE KEY unique_transaction (chain_id, transaction_hash, event_type)
);

ALTER TABLE relay_analysis ADD COLUMN gas_fee DECIMAL(65,0);
ALTER TABLE relay_analysis 
ADD COLUMN priority_fee DECIMAL(65,0),
ADD COLUMN input_amount_usd DECIMAL(65,2),
ADD COLUMN output_amount_usd DECIMAL(65,2),
ADD COLUMN earned_amount_usd DECIMAL(65,2);

CREATE TABLE IF NOT EXISTS relay_analysis (
    id INT AUTO_INCREMENT PRIMARY KEY,
    destination_chain_id INT NOT NULL,
    origin_chain_id INT NOT NULL,
    input_token VARCHAR(42) NOT NULL,
    output_token VARCHAR(42) NOT NULL,
    input_amount DECIMAL(65,0) NOT NULL,
    output_amount DECIMAL(65,0) NOT NULL,
    deposit_id INT NOT NULL,
    relayer VARCHAR(42) NOT NULL,
    depositor VARCHAR(42) NOT NULL,
    recipient VARCHAR(42) NOT NULL,
    earned_amount DECIMAL(65,0) NOT NULL,
    UNIQUE KEY unique_relay (destination_chain_id, origin_chain_id, deposit_id)
);

CREATE TABLE IF NOT EXISTS block_details (
    id INT AUTO_INCREMENT PRIMARY KEY,
    chain_id INT NOT NULL,
    block_number INT NOT NULL,
    block_timestamp DATETIME NOT NULL,
    gas_used BIGINT NOT NULL,
    gas_limit BIGINT NOT NULL,
    base_fee_per_gas DECIMAL(65,0),
    UNIQUE KEY unique_block (chain_id, block_number)
);

CREATE TABLE IF NOT EXISTS token_prices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    token_address VARCHAR(42) NOT NULL,
    price_date DATE NOT NULL,
    price_usd DECIMAL(30, 18) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_token_price (token_address, price_date)
);

CREATE INDEX idx_token_address ON token_prices(token_address);
CREATE INDEX idx_price_date ON token_prices(price_date);

ALTER TABLE token_prices ADD COLUMN symbol VARCHAR(20) AFTER token_address;
ALTER TABLE token_prices DROP INDEX unique_token_price;
ALTER TABLE token_prices ADD UNIQUE KEY unique_token_price (token_address, symbol, price_date);
CREATE INDEX idx_symbol ON token_prices(symbol);

CREATE INDEX idx_filled_v3_relays_transaction_hash ON filled_v3_relays(transaction_hash);
CREATE INDEX idx_v3_funds_deposited_transaction_hash ON v3_funds_deposited(transaction_hash);


SELECT COUNT(*) INTO @index_exists FROM information_schema.statistics 
WHERE table_schema = DATABASE() AND table_name = 'filled_v3_relays' AND index_name = 'idx_chain_tx';
SET @sql = IF(@index_exists = 0, 'CREATE INDEX idx_chain_tx ON filled_v3_relays (chain_id, transaction_hash)', 'SELECT ''Index already exists''');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SELECT COUNT(*) INTO @index_exists FROM information_schema.statistics 
WHERE table_schema = DATABASE() AND table_name = 'filled_v3_relays' AND index_name = 'idx_deposit_id';
SET @sql = IF(@index_exists = 0, 'CREATE INDEX idx_deposit_id ON filled_v3_relays (deposit_id)', 'SELECT ''Index already exists''');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SELECT COUNT(*) INTO @index_exists FROM information_schema.statistics 
WHERE table_schema = DATABASE() AND table_name = 'filled_v3_relays' AND index_name = 'idx_chain_block';
SET @sql = IF(@index_exists = 0, 'CREATE INDEX idx_chain_block ON filled_v3_relays (chain_id, block_number)', 'SELECT ''Index already exists''');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SELECT COUNT(*) INTO @index_exists FROM information_schema.statistics 
WHERE table_schema = DATABASE() AND table_name = 'v3_funds_deposited' AND index_name = 'idx_chain_tx';
SET @sql = IF(@index_exists = 0, 'CREATE INDEX idx_chain_tx ON v3_funds_deposited (chain_id, transaction_hash)', 'SELECT ''Index already exists''');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SELECT COUNT(*) INTO @index_exists FROM information_schema.statistics 
WHERE table_schema = DATABASE() AND table_name = 'v3_funds_deposited' AND index_name = 'idx_deposit_dest';
SET @sql = IF(@index_exists = 0, 'CREATE INDEX idx_deposit_dest ON v3_funds_deposited (deposit_id, destination_chain_id)', 'SELECT ''Index already exists''');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SELECT COUNT(*) INTO @index_exists FROM information_schema.statistics 
WHERE table_schema = DATABASE() AND table_name = 'v3_funds_deposited' AND index_name = 'idx_chain_block';
SET @sql = IF(@index_exists = 0, 'CREATE INDEX idx_chain_block ON v3_funds_deposited (chain_id, block_number)', 'SELECT ''Index already exists''');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SELECT COUNT(*) INTO @index_exists FROM information_schema.statistics 
WHERE table_schema = DATABASE() AND table_name = 'transaction_details' AND index_name = 'idx_chain_tx';
SET @sql = IF(@index_exists = 0, 'CREATE INDEX idx_chain_tx ON transaction_details (chain_id, transaction_hash)', 'SELECT ''Index already exists''');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SELECT COUNT(*) INTO @index_exists FROM information_schema.statistics 
WHERE table_schema = DATABASE() AND table_name = 'relay_analysis' AND index_name = 'idx_deposit_id';
SET @sql = IF(@index_exists = 0, 'CREATE INDEX idx_deposit_id ON relay_analysis (deposit_id)', 'SELECT ''Index already exists''');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SELECT COUNT(*) INTO @index_exists FROM information_schema.statistics 
WHERE table_schema = DATABASE() AND table_name = 'block_details' AND index_name = 'idx_chain_block';
SET @sql = IF(@index_exists = 0, 'CREATE INDEX idx_chain_block ON block_details (chain_id, block_number)', 'SELECT ''Index already exists''');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SELECT COUNT(*) INTO @index_exists FROM information_schema.statistics 
WHERE table_schema = DATABASE() AND table_name = 'token_prices' AND index_name = 'idx_token_address';
SET @sql = IF(@index_exists = 0, 'CREATE INDEX idx_token_address ON token_prices (token_address)', 'SELECT ''Index already exists''');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

CREATE TABLE chain_sync_status (
    chain_id INT NOT NULL,
    last_synced_block INT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (chain_id)
);

INSERT INTO chain_sync_status (chain_id, last_synced_block)
        SELECT 
            subquery.chain_id,
            subquery.last_synced_block
        FROM (
            SELECT 
                chain_id,
                MAX(block_number) as last_synced_block
            FROM 
                filled_v3_relays
            GROUP BY 
                chain_id
        ) AS subquery
        ON DUPLICATE KEY UPDATE
            last_synced_block = subquery.last_synced_block,
            updated_at = CURRENT_TIMESTAMP;