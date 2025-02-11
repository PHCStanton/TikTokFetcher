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
- `BYPASS_AUTH`: Set to 'true' during initial deployment for domain verification

## Domain Verification Process

1. **Initial Deployment Setup**:
   - Set `BYPASS_AUTH=true` in your environment variables
   - Deploy your application to Replit
   - Note down your application's URL (e.g., `https://your-app.replit.dev`)

2. **TikTok Developer Portal Configuration**:
   - Go to [TikTok Developer Portal](https://developers.tiktok.com)
   - Add your application's callback URL
   - Get the TXT record for domain verification

3. **DNS Configuration**:
   - Access your domain provider's DNS settings
   - Add the TXT record provided by TikTok
   - Wait for DNS propagation (24-48 hours)

4. **Complete Verification**:
   - Verify domain in TikTok Developer Portal
   - Set `BYPASS_AUTH=false`
   - Add `TIKTOK_CLIENT_KEY` and `TIKTOK_CLIENT_SECRET` to Replit Secrets
   - Restart your application

## Usage

1. Run the application:
```bash
python main.py