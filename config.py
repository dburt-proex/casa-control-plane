import os

# Environment Configuration
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
POLICY_FILE = os.getenv("POLICY_FILE", "policy.json")
LEDGER_PATH = os.getenv("LEDGER_PATH", "CASA/ledger.log")

# API Security
CASA_API_KEY = os.getenv("CASA_API_KEY", "casa-default-key-change-me")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")

# Risk Classification Matrix
RISK_MATRIX = {
    "read_database": "LOW",
    "send_email": "LOW",
    "write_database": "HIGH",
    "delete_database": "CRITICAL"
}
