# Live Scraper Quick Setup Checklist

**Goal:** Enable live lottery scraping on DigitalOcean $5 plan using Cron-Job.org

---

## ✅ Setup Checklist (10 minutes)

### Step 1: Generate API Token (1 minute)
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```
- [ ] Copy the generated token
- [ ] Save it somewhere safe (you'll need it twice)

---

### Step 2: Add Token to DigitalOcean (3 minutes)
1. [ ] Go to https://cloud.digitalocean.com/apps
2. [ ] Select your app
3. [ ] Settings → Components → Web component
4. [ ] Environment Variables → Edit → Add Variable
5. [ ] Key: `SCRAPER_API_TOKEN`
6. [ ] Value: `<paste-your-token>`
7. [ ] Type: Secret
8. [ ] Click Save (app will redeploy)

---

### Step 3: Deploy Code Changes (2 minutes)
1. [ ] Commit and push the code changes:
   ```bash
   git add .
   git commit -m "Add live scraper polling endpoint"
   git push origin main
   ```
2. [ ] DigitalOcean will auto-deploy (takes 2-3 minutes)

---

### Step 4: Setup Cron-Job.org (4 minutes)
1. [ ] Go to https://cron-job.org and sign up (free)
2. [ ] Verify email
3. [ ] Click "Create cronjob"
4. [ ] Fill in:
   - **Title:** `Lottery Live Scraper`
   - **URL:** `https://YOUR-APP.ondigitalocean.app/results/api/poll-sessions/`
   - **Schedule:** Every 2 minutes
   - **Method:** POST
   - **Timeout:** 55 seconds
   - **Add Header:**
     - Name: `Authorization`
     - Value: `Bearer YOUR_TOKEN_HERE`
   - **Notify on failure:** ✅ Check
5. [ ] Click "Create cronjob"

---

### Step 5: Test (2 minutes)
1. [ ] Go to Django admin panel
2. [ ] Start live scraping with a test URL:
   ```
   https://www.keralalotteries.net/2025/11/suvarna-keralam-kerala-lottery-result-sk-26-today-07-11-2025.html
   ```
3. [ ] Wait 2 minutes
4. [ ] Check if new prizes appear
5. [ ] Check Cron-Job.org execution history (should show green ✅)

---

## ✅ Verification Checklist

- [ ] API endpoint responds: `curl -X POST https://YOUR-APP.ondigitalocean.app/results/api/poll-sessions/ -H "Authorization: Bearer YOUR_TOKEN"`
- [ ] Cron-Job.org shows successful executions (green)
- [ ] Django logs show: "Polling completed successfully"
- [ ] New prizes appear in database when you start live scraping
- [ ] Sessions can be started/stopped from admin panel

---

## 🎯 You're Done!

**Your live scraper is now running in production!**

**Cost:** $5/month (DigitalOcean only, Cron-Job.org is free)

**How to use:**
1. Open Django admin
2. Paste Kerala lottery URL
3. Click "Start Live Scraping"
4. Cron-Job.org scrapes every 2 minutes automatically
5. Click "Stop" when done

---

## 📚 Full Documentation

See `LIVE_SCRAPER_SETUP.md` for:
- Detailed troubleshooting
- Performance tuning
- Security best practices
- Advanced configuration

---

## 🆘 Quick Help

**Not working?**
1. Check DigitalOcean logs: App → Runtime Logs
2. Check Cron-Job.org: Cronjobs → Execution History
3. Verify token matches in both places
4. See troubleshooting section in full docs

**Common issues:**
- 401 Unauthorized → Token mismatch
- 429 Too Many Requests → Normal, ignore it
- 408 Timeout → Kerala lottery site slow, wait and retry
- No prizes → Website hasn't published results yet
