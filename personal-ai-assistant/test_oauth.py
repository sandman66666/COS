import os
from urllib.parse import urlencode

# Your current credentials
client_id = "177991573576-no5amofsosfbqkrn5sump22vuks25jip.apps.googleusercontent.com"
redirect_uri = "http://localhost:8080/login/google/authorized"

# Construct manual OAuth URL
params = {
    'client_id': client_id,
    'redirect_uri': redirect_uri,
    'scope': 'openid email profile',
    'response_type': 'code',
    'access_type': 'offline'
}

oauth_url = f"https://accounts.google.com/o/oauth2/auth?{urlencode(params)}"
print("Manual OAuth URL:")
print(oauth_url)
