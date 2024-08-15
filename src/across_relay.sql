CREATE DATABASE IF NOT EXISTS across_relay;

USE across_relay;

CREATE TABLE IF NOT EXISTS filled_v3_relays (
    id INT AUTO_INCREMENT PRIMARY KEY,
    destination_chain_id INT,
    relayer VARCHAR(42),
    input_token VARCHAR(42),
    output_token VARCHAR(42),
    input_amount DECIMAL(65,0),
    output_amount DECIMAL(65,0),
    deposit_id INT,
    fill_deadline DATETIME,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

select relayer from filled_v3_relays group by relayer

ALTER TABLE filled_v3_relays
ADD UNIQUE KEY unique_deposit (deposit_id, destination_chain_id);

-- drop table filled_v3_relays


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


select count(*) from v3_funds_deposited