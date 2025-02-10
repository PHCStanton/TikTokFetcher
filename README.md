DEVELOPMENT_MODE=false
TIKTOK_BASE_DOMAIN=tiktokrescue.online
TIKTOK_REDIRECT_URI=https://api.tiktokrescue.online/auth/tiktok/callback
```

### Development Mode

1. Set `DEVELOPMENT_MODE=false` in your environment variables to use TikTok's test endpoints
2. In development mode:
   - The app uses `open-api-test.tiktok.com` endpoints
   - Default callback URL is `https://fetchtok.replit.dev/callback`
   - Domain verification is not required

### Production Mode

For production deployment, you have two options:

1. **Custom Domain (Recommended)**:
   - Use your verified domain (tiktokrescue.online)
   - Set `DEVELOPMENT_MODE=false`
   - Ensure all URLs match the verified domain

2. **Replit Domain**:
   - Due to TikTok's domain verification requirements, using `*.replit.app` domains may not work in production
   - Consider using development mode for testing or get a custom domain

### Environment Variables

Required environment variables:
- `TIKTOK_CLIENT_KEY`: Your TikTok API client key
- `TIKTOK_CLIENT_SECRET`: Your TikTok API client secret
- `TIKTOK_REDIRECT_URI`: Your callback URL
- `DEVELOPMENT_MODE`: Set to 'true' for development, 'false' for production
- `TIKTOK_BASE_DOMAIN`: Your verified domain (e.g., tiktokrescue.online)

## Usage

1. Run the application:
```bash
python main.py