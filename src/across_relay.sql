CREATE DATABASE IF NOT EXISTS across_relay;

USE across_relay;

CREATE TABLE IF NOT EXISTS filled_v3_relays (
    id INT AUTO_INCREMENT PRIMARY KEY,
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