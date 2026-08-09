# Deployment policy

R1: timeout_ms must be between 100 and 5000 inclusive.
R2: retries must be at most 5.
R3: tls_enabled must be true.
R4: log_level must be one of info, warn, error.
R5: max_connections must be at most 4 times worker_threads.
R6: backup_interval_hours must divide 24 exactly.
R7: admin_email must end with @corp.example.
