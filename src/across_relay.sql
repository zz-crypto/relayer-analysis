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

-- select * from filled_v3_relays group by relayer

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

-- select count(*) from v3_funds_deposited
-- select count(*) from filled_v3_relays

CREATE VIEW v_relay_analysis AS
SELECT 
    f.repayment_chain_id as destination_chain_id,
    d.chain_id AS origin_chain_id,
    f.input_token,
    f.output_token,
    f.input_amount,
    f.output_amount,
    f.deposit_id,
    f.relayer,
    d.depositor,
    d.recipient,
    (f.input_amount - f.output_amount) AS earned_amount
FROM 
    filled_v3_relays f
JOIN 
    v3_funds_deposited d ON f.deposit_id = d.deposit_id AND f.repayment_chain_id = d.chain_id;
    
-- select input_token from v_relay_analysis group by input_token
select input_token from v_relay_analysis group by input_token;
select output_token from v_relay_analysis group by output_token;
select destination_chain_id, count(*) from v_relay_analysis group by destination_chain_id;
select * from v_relay_analysis where destination_chain_id = 1