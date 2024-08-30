#!/bin/bash

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

echo "Starting analysis.py at $(date)" >> $OUTPUT_FILE
python3 analysis.py >> $OUTPUT_FILE 2>&1
echo "Finished analysis.py at $(date)" >> $OUTPUT_FILE
echo "" >> $OUTPUT_FILE

end_time=$(date +%s)

runtime=$((end_time - start_time))

echo "Total runtime: $runtime seconds" >> $OUTPUT_FILE

echo "Total runtime: $runtime seconds"

echo "Output has been saved to $OUTPUT_FILE"