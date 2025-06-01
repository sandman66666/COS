# Gmail Integration Troubleshooting Guide

## Overview
This guide helps resolve common issues with Gmail email ingestion and insights generation in the AI Chief of Staff application.

## Common Issues and Solutions

### 1. "OAuth token issue detected" Error

**Symptoms:**
- Error message: "OAuth token issue detected. The token may be expired or invalid."
- Unable to fetch emails after previously working

**Solutions:**
1. **Re-authenticate:**
   - Visit http://127.0.0.1:8080/logout
   - Visit http://127.0.0.1:8080/login
   - Complete the OAuth flow again
   - Ensure you see Gmail permissions in the consent screen

2. **Check token expiry:**
   - OAuth tokens expire after 1 hour
   - The app should auto-refresh, but if not working, re-login

### 2. "Gmail API access not properly configured" Error

**Symptoms:**
- Error during email sync
- Cannot connect to Gmail API

**Solutions:**
1. **Enable Gmail API in Google Cloud Console:**
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Select your project
   - Go to "APIs & Services" > "Library"
   - Search for "Gmail API"
   - Click "Enable"

2. **Configure OAuth Consent Screen:**
   - In Google Cloud Console, go to "APIs & Services" > "OAuth consent screen"
   - Fill out all required fields
   - Add your email as a test user if app is in testing mode
   - Add the following scopes:
     - `openid`
     - `email`
     - `profile`
     - `https://www.googleapis.com/auth/gmail.readonly`

3. **Verify Redirect URIs:**
   - In "APIs & Services" > "Credentials"
   - Click on your OAuth 2.0 Client ID
   - Add these Authorized redirect URIs:
     - `http://127.0.0.1:8080/login/google/authorized`
     - `http://localhost:8080/login/google/authorized`

### 3. No Emails Found / Empty Insights

**Symptoms:**
- Sync completes but no emails are shown
- Insights page shows empty results

**Solutions:**
1. **Check email date range:**
   - Default is 30 days back
   - Change in Settings page if needed
   - Ensure your Gmail has emails in that timeframe

2. **Verify Gmail permissions:**
   - During login, ensure you granted Gmail read access
   - Check the consent screen shows Gmail permissions

3. **Check email fetching:**
   ```python
   # Run test_gmail_integration.py to verify basic connectivity
   python3 test_gmail_integration.py
   ```

### 4. Claude Integration Issues

**Symptoms:**
- Emails fetch successfully but no insights generated
- Error in insight generation

**Solutions:**
1. **Verify Claude API key:**
   ```bash
   # Check if ANTHROPIC_API_KEY is set
   echo $ANTHROPIC_API_KEY | wc -c
   # Should show > 100 characters
   ```

2. **Check Claude model availability:**
   - Current model: `claude-3-opus-20240229`
   - May need to update if model deprecated

3. **Rate limiting:**
   - Claude has rate limits
   - Wait a few minutes and try again

## Debugging Steps

### 1. Enable Debug Logging
```bash
export FLASK_ENV=development
export FLASK_DEBUG=1
python3 backend/main.py
```

### 2. Test Gmail Connection Manually
```python
# Create test_token.txt with your access token
# Then run:
python3 debug_gmail_oauth.py
```

### 3. Check Browser Console
- Open Developer Tools (F12)
- Check Console tab for JavaScript errors
- Check Network tab for failed API calls

### 4. Verify Environment Variables
```bash
# All should return values
echo $ANTHROPIC_API_KEY
echo $GOOGLE_CLIENT_ID
echo $GOOGLE_CLIENT_SECRET
```

### 5. Test with Fresh Session
```bash
# Clear Flask session
rm -rf flask_session/*

# Restart app
python3 backend/main.py

# Login fresh
```

## Code Fixes

### Issue: Token Not Refreshing
If tokens aren't auto-refreshing, use the improved Gmail connector:

```python
# Replace in backend/core/claude_integration/email_intelligence.py
from backend.integrations.gmail.gmail_connector_improved import ImprovedGmailConnector

# Update initialization to pass full token data
gmail = ImprovedGmailConnector(session['google_oauth_token'])
```

### Issue: Better Error Messages
The improved connector provides:
- Detailed error messages
- Success/failure status
- Email statistics
- Processing metadata

## Verification Tests

### 1. Basic Connectivity Test
```bash
python3 test_gmail_integration.py
```
Expected output:
- ✓ All environment variables set
- ✓ Claude client initialized
- ✓ GmailConnector imported
- ✓ EmailIntelligence initialized

### 2. OAuth Flow Test
```bash
python3 test_oauth.py
```
Should display OAuth URL with correct scopes

### 3. Full Integration Test
1. Start the app: `python3 backend/main.py`
2. Login at http://127.0.0.1:8080/login
3. Check Settings page shows "Gmail Connected"
4. Click "Sync Emails"
5. Check progress updates
6. View insights at Email Insights page

## Contact Support
If issues persist after trying these solutions:
1. Check logs in `backend/logs/` directory
2. Save error messages and timestamps
3. Note which step fails in the process
4. Check if issue is consistent or intermittent 