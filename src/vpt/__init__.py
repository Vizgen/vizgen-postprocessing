import os
from pathlib import Path

import dotenv

envPath = os.path.join(Path.home(), '.vptenv')

AWS_PROFILE_NAME_VAR = 'VPT_AWS_PROFILE'
AWS_ACCESS_KEY_VAR = 'VPT_AWS_ACCESS_KEY_ID'
AWS_SECRET_KEY_VAR = 'VPT_AWS_SECRET_ACCESS_KEY'
GCS_SERVICE_ACCOUNT_KEY_VAR = 'VPT_GCS_SERVICE_ACCOUNT_KEY'

if os.path.exists(envPath):
    dotenv.load_dotenv(envPath)
