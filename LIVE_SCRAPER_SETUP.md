# Live Lottery Scraper - Production Setup Guide

This guide explains how to set up live lottery result scraping on **DigitalOcean App Platform $5 plan** using **Cron-Job.org** (free external cron service).

---

## How It Works

```
Admin Panel (You)          Cron-Job.org (Auto)          Django App
─────────────────          ───────────────────          ──────────
1. Click "Start Live       2. Every 1-2 minutes         3. Scrapes URL
   Scraping" with URL         calls polling API            from session
   ↓                          ↓                            ↓
   Creates session in DB      Triggers scraping           Adds new prizes
   (is_active=True)                                       Skips duplicates
```

**Key Points:**
- You control which URLs to scrape via Django admin panel
- Cron-Job.org just triggers the scraping every 1-2 minutes
- Your app does the actual work (scraping, saving data)
- No background worker process needed (saves $5/month!)

---

## Prerequisites

- ✅ Django app deployed on DigitalOcean App Platform
- ✅ Free account at https://cron-job.org
- ✅ 10 minutes of setup time

---

## Step 1: Generate API Token

Generate a secure random token for authentication:

```bash
# On your local machine or in DigitalOcean console
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Example output:**
```
xK3mP9vLqW7nR2zY8tF5jH4cN6bV1aS0dG9eM7fK2wQ
```

**Save this token** - you'll need it in the next steps!

---

## Step 2: Add API Token to DigitalOcean

1. Go to https://cloud.digitalocean.com/apps
2. Select your lottery app
3. Click **Settings** → **Components** → Your web component
4. Scroll to **Environment Variables**
5. Click **Edit** → **Add Variable**
6. Add:
   - **Key:** `SCRAPER_API_TOKEN`
   - **Value:** `<paste-your-generated-token>`
   - **Type:** Secret (encrypted)
7. Click **Save**
8. Your app will automatically redeploy (takes 2-3 minutes)

---

## Step 3: Configure Cron-Job.org

### 3.1 Create Account
1. Go to https://cron-job.org
2. Click **Sign up** (free, no credit card needed)
3. Verify your email

### 3.2 Create Cron Job
1. Click **"Cronjobs"** in the top menu
2. Click **"Create cronjob"** button
3. Fill in the form:

**Basic Settings:**
- **Title:** `Lottery Live Scraper`
- **URL:** `https://YOUR-APP.ondigitalocean.app/results/api/poll-sessions/`
  - Replace `YOUR-APP` with your actual DigitalOcean app URL
  - Example: `https://sea-lion-app-begbw.ondigitalocean.app/results/api/poll-sessions/`

**Schedule:**
- **Schedule Type:** Select "Every X minutes"
- **Interval:** `2` (every 2 minutes - recommended)
  - Or select `1` for every 1 minute (more aggressive, higher load)

**Request Settings:**
- **Request Method:** `POST`
- **Request timeout:** `55` seconds

**Request Headers:**
Click **"Add header"** and add:
- **Header name:** `Authorization`
- **Header value:** `Bearer xK3mP9vLqW7nR2zY8tF5jH4cN6bV1aS0dG9eM7fK2wQ`
  - Replace with YOUR actual token from Step 1

**Notifications (Optional but Recommended):**
- **Notify me on failure:** ✅ Check this
- **Notify me on success:** ❌ Leave unchecked (too many emails)

4. Click **"Create cronjob"**

---

## Step 4: Test the Setup

### 4.1 Test Manually in Browser
You can test the endpoint using curl or a REST client:

```bash
# Replace with your actual URL and token
curl -X POST https://your-app.ondigitalocean.app/results/api/poll-sessions/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json"
```

**Expected Response (No active sessions):**
```json
{
  "success": true,
  "message": "Polling completed successfully in 0.12s",
  "timestamp": "2025-11-07T15:30:00Z"
}
```

**If you get 401 Unauthorized:**
- Check that your token matches in DigitalOcean and your request
- Make sure you included `Bearer ` before the token

### 4.2 Test with Real Session

1. Go to your Django admin panel
2. Navigate to lottery results section
3. Click **"Add Result"** or **"Start Live Scraping"**
4. Paste a Kerala lottery URL:
   ```
   https://www.keralalotteries.net/2025/11/suvarna-keralam-kerala-lottery-result-sk-26-today-07-11-2025.html
   ```
5. Click **"Start Live Scraping"**
6. Wait 1-2 minutes for Cron-Job.org to trigger
7. Check the lottery result - new prizes should appear!

### 4.3 Monitor Execution

**In Cron-Job.org Dashboard:**
- Go to **"Cronjobs"** → Select your job
- Click **"Execution history"**
- Check recent executions:
  - ✅ Green = Success (HTTP 200)
  - 🔴 Red = Failed (HTTP 4xx/5xx)
  - Click any execution to see response details

**In Django Logs:**
- Go to DigitalOcean → Your App → **Runtime Logs**
- Look for messages like:
  ```
  [INFO] Polling lock acquired
  [INFO] Starting poll cycle for active sessions
  [INFO] Polling completed successfully in 2.34 seconds
  [INFO] Polling lock released
  ```

---

## How to Use Live Scraping

### Start Scraping
1. Open Django Admin
2. Go to lottery results
3. Click "Add Result" or "Start Live Scraping"
4. Paste Kerala lottery URL
5. Click "Start"
6. Cron-Job.org will automatically scrape every 1-2 minutes

### Stop Scraping
1. Open Django Admin
2. Find the active lottery result
3. Click "Stop Live Scraping"
4. Cron-Job.org will continue calling API, but your app will skip inactive sessions

### Monitor Progress
- Refresh the lottery result page in admin
- New prizes appear automatically as they're found
- Check "Prizes Found" count and "Last Polled At" timestamp

---

## Troubleshooting

### Problem: "Unauthorized - Invalid token"

**Cause:** API token mismatch

**Solution:**
1. Check DigitalOcean environment variable: `SCRAPER_API_TOKEN`
2. Check Cron-Job.org header: `Authorization: Bearer YOUR_TOKEN`
3. Make sure they match exactly (including spaces, case)
4. Regenerate token if needed

### Problem: "Another polling is in progress" (HTTP 429)

**Cause:** Previous request still running or cron interval too short

**Solution:**
- This is normal if scraping takes >2 minutes
- Increase Cron-Job.org interval to 3 minutes
- Or ignore it - the lock will expire after 2 minutes

### Problem: "Polling timeout" (HTTP 408)

**Cause:** Scraping took longer than 45 seconds

**Solution:**
- Kerala lottery website might be slow
- Reduce number of active sessions (scrape one lottery at a time)
- Increase timeout in `admin_views.py` (line 1120): `signal.alarm(60)`

### Problem: No new prizes appearing

**Possible Causes:**
1. **Cron job not running:** Check Cron-Job.org execution history
2. **Session not active:** Verify session has `is_active=True` in database
3. **Website hasn't updated:** Kerala lottery publishes results gradually during draw
4. **Lock issue:** Check logs for "Failed to acquire lock" errors

**Solution:**
- Check Django logs for errors
- Verify URL is accessible (visit it in browser)
- Wait 2-3 minutes and check again

### Problem: Duplicate prizes

**Cause:** Database lock not working or concurrent requests

**Solution:**
- Check if multiple cron jobs are configured
- Verify database has proper unique constraints
- Look for lock errors in Django logs

---

## Safety Features

Your endpoint includes these protections:

### 1. Request Locking
- Only one polling request can run at a time
- Uses database lock (no Redis needed)
- Stale locks auto-expire after 2 minutes

### 2. Timeout Protection
- Requests timeout after 45 seconds (on Unix systems)
- Prevents long-running requests from blocking
- Returns HTTP 408 on timeout

### 3. Authentication
- Bearer token required for all requests
- Prevents unauthorized access
- Logs failed authentication attempts

### 4. Error Handling
- Graceful error responses
- Detailed logging for debugging
- Lock always released (even on error)

---

## Cost Breakdown

| Service | Cost | Purpose |
|---------|------|---------|
| **DigitalOcean App Platform** | $5/mo | Django app hosting |
| **Cron-Job.org** | FREE | Triggers scraping every 1-2 min |
| **PostgreSQL Database** | Included | Stores lottery data |
| **Total** | **$5/mo** | No extra cost! |

**Alternative (if you need more reliability):**
- Add DigitalOcean Worker component: +$5/mo
- Run `python manage.py run_live_scraper` as worker
- More reliable, no external dependencies
- **Total: $10/mo**

---

## Performance Considerations

### Recommended Settings:
- **Polling Interval:** 2 minutes (balance between speed and load)
- **Max Active Sessions:** 1-2 lotteries at a time
- **Timeout:** 45-55 seconds

### Expected Performance:
- **Scraping time:** 5-15 seconds per lottery
- **Database queries:** 5-10 per request
- **External HTTP requests:** 1 per active session
- **Server load:** Low (2-3% CPU, 50MB RAM)

### DigitalOcean $5 Plan Limits:
- **RAM:** 512 MB
- **CPU:** Shared vCPU
- **Bandwidth:** Unlimited
- **Build minutes:** Unlimited

**Your app should handle:**
- ✅ 1-2 active scraping sessions
- ✅ 30-60 polling requests/hour
- ✅ Concurrent user traffic + scraping

---

## Advanced Configuration

### Change Polling Interval

**In Cron-Job.org:**
- Edit your cron job
- Change schedule to:
  - `*/1` = Every 1 minute (aggressive)
  - `*/2` = Every 2 minutes (recommended)
  - `*/3` = Every 3 minutes (conservative)
  - `*/5` = Every 5 minutes (very light load)

### Adjust Timeout

**In `admin_views.py:1120`:**
```python
signal.alarm(45)  # Change to 60 for longer timeout
```

### Enable Monitoring

**Add UptimeRobot (free):**
1. Sign up at https://uptimerobot.com
2. Create HTTP monitor for your app URL
3. Get alerts if app goes down
4. 5-minute check interval on free plan

---

## Maintenance

### Daily Tasks:
- ✅ Check Cron-Job.org execution history (1 minute)
- ✅ Verify active sessions are scraping correctly

### Weekly Tasks:
- ✅ Review Django error logs
- ✅ Check database size (clean old sessions if needed)

### Monthly Tasks:
- ✅ Rotate API token (optional, for security)
- ✅ Review Cron-Job.org performance stats

---

## Security Best Practices

1. **Never commit API token to Git**
   - Always use environment variables
   - Add `.env` to `.gitignore`

2. **Rotate token periodically**
   - Generate new token every 3-6 months
   - Update in both DigitalOcean and Cron-Job.org

3. **Monitor authentication failures**
   - Check Django logs for unauthorized attempts
   - Rotate token if you see suspicious activity

4. **Use HTTPS only**
   - DigitalOcean provides free SSL
   - Never use HTTP for production

---

## Support

### Documentation:
- Django Docs: https://docs.djangoproject.com
- DigitalOcean Docs: https://docs.digitalocean.com/products/app-platform/
- Cron-Job.org Docs: https://cron-job.org/en/documentation/

### Logs Location:
- **DigitalOcean:** App → Runtime Logs
- **Cron-Job.org:** Cronjobs → Execution History
- **Django:** `logs/lottery_app.log` (if file logging enabled)

### Common URLs:
- **Your API:** `https://YOUR-APP.ondigitalocean.app/results/api/poll-sessions/`
- **Django Admin:** `https://YOUR-APP.ondigitalocean.app/admin/`
- **Cron-Job.org Dashboard:** https://console.cron-job.org/

---

## Quick Reference

### Generate Token:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Test Endpoint:
```bash
curl -X POST https://YOUR-APP.ondigitalocean.app/results/api/poll-sessions/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Check Active Sessions (Django shell):
```python
from results.models import LiveScrapingSession
active = LiveScrapingSession.objects.filter(is_active=True)
for session in active:
    print(f"{session.lottery_result} - {session.prizes_found_count} prizes")
```

### Clean Old Lock (if stuck):
```python
from results.models import LiveScrapingSession
LiveScrapingSession.objects.filter(scraping_url='polling_lock').delete()
```

---

**Setup complete! Your live scraper is now production-ready.**

Need help? Check the troubleshooting section or review Django logs for error details.
