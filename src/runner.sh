#!/bin/bash

mkdir -p backup

while true; do
    if [ -f "script_output.log" ]; then
        backup_file="backup/script_output_$(date +%Y%m%d_%H%M%S).log"
        mv script_output.log "$backup_file"
        echo "Backed up previous log to $backup_file"
    fi

    OUTPUT_FILE="script_output.log"

    > $OUTPUT_FILE

    start_time=$(date +%s)

    echo "Starting event_data_fetcher.py at $(date)" >> $OUTPUT_FILE
    python3 event_data_fetcher.py --events --blocks >> $OUTPUT_FILE 2>&1
    echo "Finished event_data_fetcher.py at $(date)" >> $OUTPUT_FILE
    echo "" >> $OUTPUT_FILE

    echo "Starting transaction_data_fetcher.py at $(date)" >> $OUTPUT_FILE
    python3 transaction_data_fetcher.py >> $OUTPUT_FILE 2>&1
    echo "Finished transaction_data_fetcher.py at $(date)" >> $OUTPUT_FILE
    echo "" >> $OUTPUT_FILE

    echo "Starting clean_up.py at $(date)" >> $OUTPUT_FILE
    python3 clean_up.py >> $OUTPUT_FILE 2>&1
    echo "Finished clean_up.py at $(date)" >> $OUTPUT_FILE
    echo "" >> $OUTPUT_FILE

    echo "Starting fee_fetcher_hourly.py at $(date)" >> $OUTPUT_FILE
    python3 fee_fetcher_hourly.py >> $OUTPUT_FILE 2>&1
    echo "Finished fee_fetcher_hourly.py at $(date)" >> $OUTPUT_FILE
    echo "" >> $OUTPUT_FILE

    end_time=$(date +%s)

    runtime=$((end_time - start_time))

    echo "Total runtime: $runtime seconds" >> $OUTPUT_FILE

    echo "Total runtime: $runtime seconds"

    echo "Output has been saved to $OUTPUT_FILE"

    sleep_time=$((3600 - $(date +%s) % 3600))
    echo "Sleeping for $sleep_time seconds until next hour"
    sleep $sleep_time
done