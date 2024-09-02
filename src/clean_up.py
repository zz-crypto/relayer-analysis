from db_operations import DatabaseOperations

db_ops = DatabaseOperations()
db_ops.connect()
rows_affected = db_ops.update_chain_sync_status()
db_ops.close()