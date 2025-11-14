# GitHub Actions Setup Guide - Daily Yahoo Finance Data Collection

This guide will walk you through setting up your repository to run the Yahoo Finance data collection scripts daily on GitHub Actions.

## Prerequisites

- A GitHub account
- Your code repository on GitHub (or create a new one)

## Step-by-Step Setup

### Step 1: Initialize Git Repository (if not already done)

If you haven't already initialized a git repository:

```bash
git init
git add .
git commit -m "Initial commit"
```

### Step 2: Create GitHub Repository

1. Go to [GitHub.com](https://github.com) and sign in
2. Click the "+" icon in the top right corner
3. Select "New repository"
4. Name your repository (e.g., `yahoo-finance-daily`)
5. Choose public or private
6. **Do NOT** initialize with README, .gitignore, or license (we already have these)
7. Click "Create repository"

### Step 3: Push Your Code to GitHub

**⚠️ Authentication Required:** GitHub no longer supports password authentication. You need to use a Personal Access Token (PAT) or SSH.

#### Option A: Using Personal Access Token (Recommended for beginners)

1. **Create a Personal Access Token:**
   - Go to GitHub.com → Click your profile picture (top right) → **Settings**
   - Scroll down to **Developer settings** (left sidebar)
   - Click **Personal access tokens** → **Tokens (classic)**
   - Click **Generate new token** → **Generate new token (classic)**
   - Give it a name (e.g., "yahoo-finance-repo")
   - Select expiration (30 days, 90 days, or no expiration)
   - Check the **repo** scope (this gives full repository access)
   - Click **Generate token**
   - **⚠️ IMPORTANT:** Copy the token immediately (you won't see it again!)

2. **Push using the token:**
   ```bash
   # Add your GitHub repository as remote (replace YOUR_USERNAME and REPO_NAME)
   git remote add origin https://github.com/YOUR_USERNAME/REPO_NAME.git
   
   # Push your code (when prompted for password, paste your token instead)
   git branch -M main
   git push -u origin main
   ```
   
   When prompted:
   - **Username:** Your GitHub username
   - **Password:** Paste your Personal Access Token (not your GitHub password)

3. **Alternative: Use token in URL (one-time setup):**
   ```bash
   # Replace YOUR_USERNAME, YOUR_TOKEN, and REPO_NAME
   git remote add origin https://YOUR_TOKEN@github.com/YOUR_USERNAME/REPO_NAME.git
   git branch -M main
   git push -u origin main
   ```

#### Option B: Using SSH (More secure, recommended for advanced users)

1. **Check if you have SSH keys:**
   ```bash
   ls ~/.ssh
   ```
   If you see `id_rsa` and `id_rsa.pub` (or `id_ed25519` and `id_ed25519.pub`), skip to step 3.

2. **Generate SSH key (if needed):**
   ```bash
   ssh-keygen -t ed25519 -C "your_email@example.com"
   # Press Enter to accept default location
   # Optionally set a passphrase (recommended)
   ```

3. **Add SSH key to GitHub:**
   - Copy your public key:
     ```bash
     # Windows (PowerShell)
     cat ~/.ssh/id_ed25519.pub
     # Or if using id_rsa:
     cat ~/.ssh/id_rsa.pub
     ```
   - Go to GitHub.com → Settings → **SSH and GPG keys** → **New SSH key**
   - Paste your public key and save

4. **Push using SSH:**
   ```bash
   # Use SSH URL instead of HTTPS
   git remote add origin git@github.com:YOUR_USERNAME/REPO_NAME.git
   git branch -M main
   git push -u origin main
   ```

#### Option C: Using GitHub CLI (Alternative)

If you have GitHub CLI installed:
```bash
gh auth login
git remote add origin https://github.com/YOUR_USERNAME/REPO_NAME.git
git branch -M main
git push -u origin main
```

### Step 4: Verify Files Are in Place

Make sure these files are in your repository:
- ✅ `yahoo_daily_gainers.py`
- ✅ `yahoo_daily_losers.py`
- ✅ `requirements.txt`
- ✅ `.gitignore`
- ✅ `.github/workflows/daily_yahoo_finance.yml`

### Step 5: Configure Workflow Schedule (Optional)

The workflow is currently set to run **Monday-Friday at 4:00 PM EST (9:00 PM UTC)**.

To change the schedule, edit `.github/workflows/daily_yahoo_finance.yml` and modify the cron expression:

```yaml
- cron: '0 21 * * 1-5'  # Format: minute hour day month weekday
```

**Cron format:** `minute hour day month weekday`
- `0 21 * * 1-5` = 9:00 PM UTC, Monday-Friday
- `0 20 * * 1-5` = 8:00 PM UTC (4:00 PM EST)
- `0 0 * * *` = Every day at midnight UTC

**Time zones:**
- EST is UTC-5 (or UTC-4 during daylight saving)
- Adjust the UTC hour accordingly

### Step 6: Test the Workflow

1. Go to your repository on GitHub
2. Click on the "Actions" tab
3. You should see "Daily Yahoo Finance Data Collection" workflow
4. Click "Run workflow" button to test it manually
5. Click the workflow run to see the progress

### Step 7: Monitor Daily Runs

After the first run:
- The workflow will run automatically on the schedule
- Database files (`.db`) will be committed back to the repository
- You can view logs in the "Actions" tab
- Each run will append new data to the databases

## Important Notes

### Database Storage

The workflow is configured to commit database files back to the repository. This means:
- ✅ Simple setup, no external storage needed
- ⚠️ Repository size will grow over time
- ⚠️ GitHub has a 100MB file size limit (warning at 50MB)

**Alternative Options:**

1. **Use GitHub Artifacts** (keeps files for 90 days):
   - Modify workflow to upload `.db` files as artifacts instead of committing

2. **Use External Storage** (recommended for long-term):
   - AWS S3, Google Cloud Storage, or Azure Blob Storage
   - Modify scripts to upload databases to cloud storage

3. **Use Git LFS** (for large files):
   - Install Git LFS and track `.db` files
   - Better for large binary files

### Workflow Permissions

If you encounter permission errors when committing:
1. Go to repository Settings → Actions → General
2. Under "Workflow permissions", select "Read and write permissions"
3. Check "Allow GitHub Actions to create and approve pull requests"

### Troubleshooting

**Authentication failed when pushing:**
- Make sure you're using a Personal Access Token (PAT), not your password
- For HTTPS: Use token as password when prompted
- For SSH: Ensure your SSH key is added to GitHub
- If using token in URL, make sure it's correct
- Try removing and re-adding the remote:
  ```bash
  git remote remove origin
  git remote add origin https://github.com/YOUR_USERNAME/REPO_NAME.git
  git push -u origin main
  ```

**Workflow fails to commit:**
- Check workflow permissions (see above)
- Ensure `.gitignore` doesn't exclude `.db` files if you want them committed

**Scripts fail:**
- Check the Actions tab for error logs
- Verify all dependencies are in `requirements.txt`
- Test scripts locally first

**Schedule not running:**
- GitHub Actions may be delayed by a few minutes
- Free accounts have limited concurrent jobs
- Check repository settings for any restrictions

## Manual Trigger

You can manually trigger the workflow anytime:
1. Go to Actions tab
2. Select "Daily Yahoo Finance Data Collection"
3. Click "Run workflow"
4. Select branch and click "Run workflow"

## Next Steps

- Monitor the first few runs to ensure everything works
- Consider setting up notifications for workflow failures
- Review database growth and consider cloud storage if needed
- Add error handling or notifications (email, Slack, etc.) if desired


