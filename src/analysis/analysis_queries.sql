CREATE TABLE IF NOT EXISTS relay_analysis_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    deposit_id INT NOT NULL,
    destination_chain_id INT NOT NULL,
    origin_chain_id INT NOT NULL,
    input_token VARCHAR(42) NOT NULL,
    output_token VARCHAR(42) NOT NULL,
    relayer VARCHAR(42) NOT NULL,
    depositor VARCHAR(42) NOT NULL,
    recipient VARCHAR(42) NOT NULL,
    input_amount DECIMAL(65, 18) NOT NULL,
    output_amount DECIMAL(65, 18) NOT NULL,
    input_amount_usd DECIMAL(65, 18) NOT NULL,
    output_amount_usd DECIMAL(65, 18) NOT NULL,
    input_symbol VARCHAR(10) NOT NULL,
    output_symbol VARCHAR(10) NOT NULL,
    gas_fee DECIMAL(65, 18) NOT NULL,
    priority_fee DECIMAL(65, 18) NOT NULL,
    base_fee_per_gas DECIMAL(65, 9) NOT NULL,
    gas_used BIGINT NOT NULL,
    priority_fee_per_gas DECIMAL(65, 9) NOT NULL,
    relay_time INT NOT NULL,
    deposit_block_time DATETIME NOT NULL,
    fill_block_time DATETIME NOT NULL,
    transaction_hash varchar(66),
    exclusive_relayer varchar(42),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS target_combo (
    id INT AUTO_INCREMENT PRIMARY KEY,
    origin_chain_id INT NOT NULL,
    destination_chain_id INT NOT NULL,
    input_symbol VARCHAR(10) NOT NULL,
    output_symbol VARCHAR(10) NOT NULL,
    amount_range VARCHAR(20) NOT NULL,
    UNIQUE KEY unique_combo (origin_chain_id, destination_chain_id, input_symbol, output_symbol, amount_range)
);

TRUNCATE TABLE target_combo;

INSERT INTO target_combo (origin_chain_id, destination_chain_id, input_symbol, output_symbol, amount_range)
WITH combo_stats AS (
    WITH daily_stats AS (
        SELECT 
            DATE(fill_block_time) AS date,
            origin_chain_id, destination_chain_id, input_symbol, output_symbol,
            SUM(output_amount_usd) AS daily_volume_usd,
            SUM(input_amount_usd - output_amount_usd - gas_fee * 2700) AS daily_profit_usd,
            CASE 
                WHEN input_amount_usd < 1000 THEN '0-1k'
                WHEN input_amount_usd < 10000 THEN '1k-10k'
                WHEN input_amount_usd < 100000 THEN '10k-100k'
                ELSE '100k+'
            END AS amount_range,
            COUNT(*) as transaction_count,
            AVG(relay_time) AS avg_relay_time_seconds,
            MAX(input_amount_usd) AS max_transaction_size_usd
        FROM relay_analysis_results
        GROUP BY DATE(fill_block_time), origin_chain_id, destination_chain_id, input_symbol, output_symbol, amount_range
    )
    SELECT 
        origin_chain_id, 
        destination_chain_id, 
        input_symbol, output_symbol, 
        amount_range,
        AVG(daily_volume_usd) AS avg_daily_volume_usd,
        AVG(daily_profit_usd) AS avg_daily_profit_usd,
        AVG(daily_profit_usd) / AVG(daily_volume_usd) AS daily_roi,
        AVG(daily_profit_usd) / AVG(daily_volume_usd) * 365 AS annual_roi,
        AVG(transaction_count) AS avg_daily_transaction_count,
        AVG(avg_relay_time_seconds) AS avg_relay_time_seconds,
        MAX(max_transaction_size_usd) AS max_transaction_size_usd
    FROM daily_stats
    GROUP BY origin_chain_id, destination_chain_id, input_symbol, output_symbol, amount_range
),
optimal_allocation AS (
    SELECT 
        *,
        CASE
            WHEN avg_daily_volume_usd > 0 THEN
                GREATEST(
                    avg_daily_volume_usd,  
                    max_transaction_size_usd
                )
            ELSE 0
        END AS suggested_allocation_usd,
        avg_daily_transaction_count * avg_relay_time_seconds AS daily_capital_usage_time,
        avg_daily_volume_usd / NULLIF(GREATEST(avg_daily_volume_usd, max_transaction_size_usd), 0) AS daily_capital_turnover
    FROM combo_stats
)
SELECT DISTINCT
    origin_chain_id,
    destination_chain_id,
    input_symbol,
    output_symbol,
    amount_range
FROM optimal_allocation
WHERE annual_roi > 0 
  AND amount_range != '100k+' 
  AND avg_daily_transaction_count > 10
  AND avg_daily_volume_usd > 100000
ORDER BY annual_roi DESC;

--Detailed analysis for priority fee rules and target amount range
select r.relayer, r.input_amount_usd, r.output_amount_usd, r.gas_fee * 2700 as gas_fee_usd, r.fill_block_time, r.relay_time , 
r.priority_fee * 2700 as priority,
r.priority_fee * 2700 / (r.input_amount_usd - r.output_amount_usd) as priority_fee_ratio,
f.exclusive_relayer,
f.transaction_hash
from relay_analysis_results r 
join filled_v3_relays f on r.deposit_id = f.deposit_id
where r.origin_chain_id = '8453' and r.destination_chain_id = 1 and r.input_symbol = 'WETH'
and r.output_amount_usd > 20000 and r.output_amount_usd < 100000 
order by DATE(r.fill_block_time) desc, priority_fee_ratio desc;


-- target relayer combo
DROP TABLE IF EXISTS target_relayer_combo;

CREATE TABLE target_relayer_combo AS
WITH combo_totals AS (
    SELECT 
        tc.origin_chain_id,
        tc.destination_chain_id,
        tc.input_symbol,
        tc.output_symbol,
        tc.amount_range,
        COUNT(*) AS total_transactions
    FROM 
        target_combo tc
    JOIN 
        relay_analysis_results rar ON 
            tc.origin_chain_id = rar.origin_chain_id AND
            tc.destination_chain_id = rar.destination_chain_id AND
            tc.input_symbol = rar.input_symbol AND
            tc.output_symbol = rar.output_symbol AND
            tc.amount_range = CASE 
                WHEN rar.input_amount_usd < 1000 THEN '0-1k'
                WHEN rar.input_amount_usd < 10000 THEN '1k-10k'
                WHEN rar.input_amount_usd < 100000 THEN '10k-100k'
                ELSE '100k+'
            END
    GROUP BY 
        tc.origin_chain_id,
        tc.destination_chain_id,
        tc.input_symbol,
        tc.output_symbol,
        tc.amount_range
)
SELECT 
    tc.origin_chain_id,
    tc.destination_chain_id,
    tc.input_symbol,
    tc.output_symbol,
    tc.amount_range,
    rar.relayer,
    COUNT(*) AS transaction_count,
    (COUNT(*) * 100.0 / ct.total_transactions) AS transaction_percentage,
    AVG(rar.input_amount_usd - rar.output_amount_usd - rar.gas_fee * 2700) as avg_profit_usd,
    SUM(rar.input_amount_usd - rar.output_amount_usd - rar.gas_fee * 2700) as total_profit_usd,
    AVG(rar.input_amount_usd - rar.output_amount_usd - rar.gas_fee * 2700) / AVG(rar.output_amount_usd) AS avg_profit_ratio,
    SUM(rar.input_amount_usd - rar.output_amount_usd - rar.gas_fee * 2700)/ SUM(rar.output_amount_usd) AS total_profit_ratio
FROM 
    target_combo tc
JOIN 
    relay_analysis_results rar ON 
        tc.origin_chain_id = rar.origin_chain_id AND
        tc.destination_chain_id = rar.destination_chain_id AND
        tc.input_symbol = rar.input_symbol AND
        tc.output_symbol = rar.output_symbol AND
        tc.amount_range = CASE 
            WHEN rar.input_amount_usd < 1000 THEN '0-1k'
            WHEN rar.input_amount_usd < 10000 THEN '1k-10k'
            WHEN rar.input_amount_usd < 100000 THEN '10k-100k'
            ELSE '100k+'
        END
JOIN
    combo_totals ct ON
        tc.origin_chain_id = ct.origin_chain_id AND
        tc.destination_chain_id = ct.destination_chain_id AND
        tc.input_symbol = ct.input_symbol AND
        tc.output_symbol = ct.output_symbol AND
        tc.amount_range = ct.amount_range
GROUP BY 
    tc.origin_chain_id,
    tc.destination_chain_id,
    tc.input_symbol,
    tc.output_symbol,
    tc.amount_range,
    rar.relayer,
    ct.total_transactions
HAVING 
    SUM(rar.input_amount_usd - rar.output_amount_usd - rar.gas_fee * 2700) > 300
ORDER BY 
    tc.origin_chain_id,
    tc.destination_chain_id,
    tc.input_symbol,
    tc.output_symbol,
    tc.amount_range,
    total_profit_usd DESC;


CREATE TABLE fee_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    timestamp DATETIME,
    input_token VARCHAR(255),
    output_token VARCHAR(255),
    origin_chain_id INT,
    destination_chain_id INT,
    amount DECIMAL(65,0),
    total_relay_fee_pct DECIMAL(65,0),
    relayer_capital_fee_pct DECIMAL(65,0),
    relayer_gas_fee_pct DECIMAL(65,0),
    lp_fee_pct DECIMAL(65,0),
    quote_block INT,
    min_deposit DECIMAL(65,0),
    max_deposit DECIMAL(65,0),
    max_deposit_instant DECIMAL(65,0),
    max_deposit_short_delay DECIMAL(65,0),
    recommended_deposit_instant DECIMAL(65,0),
    deposit_id VARCHAR(255)
);

CREATE TABLE fee_data_hourly (
    id INT AUTO_INCREMENT PRIMARY KEY,
    timestamp DATETIME,
    input_token VARCHAR(255),
    output_token VARCHAR(255),
    origin_chain_id INT,
    destination_chain_id INT,
    amount DECIMAL(65,0),
    total_relay_fee_pct DECIMAL(65,0),
    relayer_capital_fee_pct DECIMAL(65,0),
    relayer_gas_fee_pct DECIMAL(65,0),
    lp_fee_pct DECIMAL(65,0),
    quote_block INT,
    min_deposit DECIMAL(65,0),
    max_deposit DECIMAL(65,0),
    max_deposit_instant DECIMAL(65,0),
    max_deposit_short_delay DECIMAL(65,0),
    recommended_deposit_instant DECIMAL(65,0)
);