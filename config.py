import os
from pathlib import Path

class Config:
    """Application configuration"""
    
    # Security
    API_KEY = os.getenv('API_KEY', '39bf160a-775d-4408-babb-5098cd3e4353')
    SECRET_KEY = os.getenv('SECRET_KEY', os.urandom(32).hex())
    
    # Database
    BASE_DIR = Path(__file__).parent
    DATABASE = os.getenv('DATABASE_PATH', str(BASE_DIR / 'jobs.db'))
    
    # Job settings
    MAX_JOB_AGE_HOURS = int(os.getenv('MAX_JOB_AGE_HOURS', '24'))
    JOB_CLEANUP_INTERVAL = int(os.getenv('JOB_CLEANUP_INTERVAL', '3600'))  # 1 hour
    
    # SSH settings
    SSH_TIMEOUT = int(os.getenv('SSH_TIMEOUT', '30'))
    SSH_MAX_RETRIES = int(os.getenv('SSH_MAX_RETRIES', '15'))
    
    # Installation timeout (seconds)
    INSTALL_TIMEOUT = int(os.getenv('INSTALL_TIMEOUT', '900'))  # 15 minutes
    
    # Logging
    LOG_DIR = Path(os.getenv('LOG_DIR', '/tmp/vps-provisioner'))
    LOG_DIR.mkdir(exist_ok=True)
    
    # Supported apps
    SUPPORTED_APPS = ['n8n', 'wireguard', 'outline', 'vaultwarden', '3x-ui', 'seafile', 'filebrowser']
    
    @classmethod
    def validate(cls):
        """Validate configuration"""
        if cls.API_KEY == 'CHANGE-ME-IN-PRODUCTION-XkP9mL2vQ8':
            print("⚠️  WARNING: Using default API_KEY! Set API_KEY environment variable!")
        
        return True
