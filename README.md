tiktok-developers-site-verification=Hl2FLqA7XY2ryMlN8E6Fv8vtwqJCflZR
```

## Production Deployment

### Environment Variables
Required for production:
```
TIKTOK_CLIENT_KEY=your_client_key
TIKTOK_CLIENT_SECRET=your_client_secret
TIKTOK_BASE_DOMAIN=app.tiktokrescue.online
DEVELOPMENT_MODE=false
```

### Deployment Steps
1. **Domain Setup**:
   - Add the TXT record shown above to your domain's DNS configuration
   - Wait for DNS propagation (can take up to 48 hours)
   - Verify the domain in TikTok Developer Portal

2. **Application Setup**:
   - Set all required environment variables
   - Ensure callback URL in TikTok Developer Portal matches:
     `https://app.tiktokrescue.online/auth/tiktok/callback`

3. **Start Application**:
   ```bash
   python server.py