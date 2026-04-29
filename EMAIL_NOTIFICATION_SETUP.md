# Email Notification Setup Guide

This guide shows you how to set up email notifications for your daily workflow runs.

## Option 1: GitHub Built-in Notifications (Easiest - No Setup Required)

GitHub automatically sends email notifications for workflow runs, but you need to enable them:

### Steps:

1. **Go to GitHub Settings:**
   - Click your profile picture (top right) → **Settings**
   - Or go to: `https://github.com/settings/notifications`

2. **Enable Workflow Notifications:**
   - Scroll to **"Actions"** section
   - Check **"Email"** under "Workflow runs"
   - Choose when to receive emails:
     - ✅ **Always** - Get emails for every workflow run
     - ✅ **Only on failure** - Only get emails when workflow fails
     - ✅ **Never** - No email notifications

3. **Save Settings:**
   - Your preferences are saved automatically

**Pros:**
- ✅ No additional setup required
- ✅ Works immediately
- ✅ No external services needed

**Cons:**
- ⚠️ Limited customization
- ⚠️ Basic email format
- ⚠️ Only sends on workflow completion/failure

---

## Option 2: Custom Email Notifications (More Control)

The workflow now includes a custom email notification step using SMTP. This gives you more control over the email content and timing.

### Setup Steps:

#### Step 1: Choose an Email Service

You can use any SMTP service. Here are popular options:

**Gmail (Free):**
- SMTP Server: `smtp.gmail.com`
- Port: `465` (SSL) or `587` (TLS)
- Requires: App Password (see below)

**Outlook/Hotmail (Free):**
- SMTP Server: `smtp-mail.outlook.com`
- Port: `587`
- Requires: App Password

**SendGrid (Free tier available):**
- SMTP Server: `smtp.sendgrid.net`
- Port: `587`
- Requires: API Key

**Mailgun (Free tier available):**
- SMTP Server: `smtp.mailgun.org`
- Port: `587`
- Requires: API Key

#### Step 2: Get SMTP Credentials

**For Gmail:**

1. Enable 2-Factor Authentication on your Google account
2. Go to: `https://myaccount.google.com/apppasswords`
3. Create an "App Password" for "Mail"
4. Copy the 16-character password (you'll use this as `EMAIL_PASSWORD`)

**For Outlook:**

1. Enable 2-Factor Authentication
2. Go to: `https://account.microsoft.com/security`
3. Create an App Password
4. Copy the password

**For SendGrid/Mailgun:**

1. Sign up for an account
2. Get your SMTP credentials from the dashboard
3. Use your API key as the password

#### Step 3: Add Secrets to GitHub Repository

1. **Go to your repository on GitHub**
2. **Navigate to:** Settings → Secrets and variables → Actions
3. **Click "New repository secret"** and add these secrets:

   **Required Secrets:**
   - `EMAIL_USERNAME`: Your email address (e.g., `yourname@gmail.com`)
   - `EMAIL_PASSWORD`: Your app password or API key
   - `EMAIL_TO`: Recipient email address (can be same as username)

   **Optional (if using different SMTP server):**
   - `EMAIL_SMTP_SERVER`: SMTP server address (default: `smtp.gmail.com`)
   - `EMAIL_SMTP_PORT`: SMTP port (default: `465`)

#### Step 4: Customize Email Content (Optional)

Edit `.github/workflows/daily_yahoo_finance.yml` to customize the email:

```yaml
- name: Send email notification
  uses: dawidd6/action-send-mail@v3
  with:
    subject: "Your Custom Subject"
    body: |
      Your custom email content here.
      You can include workflow details: ${{ github.run_id }}
```

#### Step 5: Test the Workflow

1. Go to Actions tab
2. Click "Run workflow" to test
3. Check your email inbox

---

## Option 3: Alternative Email Services

### Using SendGrid Action (Alternative)

If you prefer SendGrid's action:

```yaml
- name: Send email via SendGrid
  uses: sendgrid/sendgrid-nodejs@main
  env:
    SENDGRID_API_KEY: ${{ secrets.SENDGRID_API_KEY }}
  run: |
    # Custom email sending script
```

### Using Mailgun Action

```yaml
- name: Send email via Mailgun
  uses: mailgun/mailgun-js@v1
  env:
    MAILGUN_API_KEY: ${{ secrets.MAILGUN_API_KEY }}
    MAILGUN_DOMAIN: ${{ secrets.MAILGUN_DOMAIN }}
```

---

## Troubleshooting

### Email Not Received

1. **Check Spam Folder:**
   - Emails might be filtered as spam
   - Mark as "Not Spam" to whitelist

2. **Verify Secrets:**
   - Go to repository Settings → Secrets
   - Ensure all required secrets are set correctly
   - Check for typos in secret names

3. **Check Workflow Logs:**
   - Go to Actions tab → Latest run
   - Check the "Send email notification" step
   - Look for error messages

4. **Test SMTP Credentials:**
   - Try sending a test email using the same credentials
   - Verify the SMTP server and port are correct

### Gmail "Less Secure App" Error

If using Gmail and getting authentication errors:
- You **must** use an App Password (not your regular password)
- Enable 2-Factor Authentication first
- Generate App Password from: `https://myaccount.google.com/apppasswords`

### Workflow Fails on Email Step

- The email step uses `if: always()` so it runs even if previous steps fail
- If email step fails, check:
  - SMTP credentials are correct
  - SMTP server and port are correct
  - Firewall/network restrictions

---

## Email Content Customization

You can customize the email to include more information:

```yaml
body: |
  <h2>Daily Yahoo Finance Data Collection</h2>
  <p><strong>Status:</strong> ${{ job.status }}</p>
  <p><strong>Date:</strong> ${{ github.run_date }}</p>
  <p><strong>Repository:</strong> ${{ github.repository }}</p>
  <p><strong>Workflow Run:</strong> <a href="${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}">View Details</a></p>
  
  <h3>Summary:</h3>
  <ul>
    <li>Gainers data collected</li>
    <li>Losers data collected</li>
    <li>Database files updated</li>
  </ul>
```

---

## Recommended Setup

For most users, I recommend:

1. **Start with Option 1** (GitHub built-in notifications)
   - Quick and easy
   - No additional setup

2. **Upgrade to Option 2** if you need:
   - Custom email content
   - More control over when emails are sent
   - Multiple recipients
   - HTML formatted emails

---

## Security Notes

⚠️ **Important:**
- Never commit email passwords or API keys to your repository
- Always use GitHub Secrets for sensitive information
- Use App Passwords instead of your main account password
- Regularly rotate your credentials

---

## Next Steps

After setting up email notifications:

1. Test the workflow manually
2. Verify you receive the email
3. Check spam folder if email doesn't arrive
4. Customize email content if desired
5. Monitor for a few days to ensure it's working correctly


