from analysis_helper import DatabaseOperations
import csv

def write_to_csv(data, filename):
    if not data:
        print(f"No data to write to {filename}")
        return
    
    fieldnames = data[0].keys()
    
    try:
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in data:
                writer.writerow(row)
        print(f"Data has been successfully written to {filename}")
    except IOError as e:
        print(f"Error writing to CSV file {filename}: {e}")

db_ops = DatabaseOperations()
try:
    db_ops.connect()
    db_ops.insert_relay_data()
    
    target_combo = db_ops.process_target_combo()
    target_relayer_combo = db_ops.process_target_relayer_combo()

    if target_combo:
        write_to_csv(target_combo, 'target_combo.csv')
        print("Data from target_combo has been saved to 'target_combo.csv'")
    else:
        print("No data processed for target_combo table")

    if target_relayer_combo:
        write_to_csv(target_relayer_combo, 'target_relayer_combo.csv')
        print("Data from target_relayer_combo has been saved to 'target_relayer_combo.csv'")
    else:
        print("No data processed from target_relayer_combo table")


finally:
    db_ops.close()