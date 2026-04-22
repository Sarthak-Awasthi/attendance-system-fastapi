# Google Sheets Integration — Setup Guide

This guide walks you through setting up Google Sheets as a storage backend for the Attendance System.

## Prerequisites

- A Google account
- ~5 minutes

## Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **Select a project** → **New Project**
3. Name it (e.g., "Attendance System") and click **Create**

## Step 2: Enable the Google Sheets API

1. In your project, go to **APIs & Services** → **Library**
2. Search for **"Google Sheets API"**
3. Click on it and press **Enable**
4. Also search for and enable **"Google Drive API"**

## Step 3: Create a Service Account

1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **Service Account**
3. Name it (e.g., "attendance-writer") and click **Create and Continue**
4. For role, select **Editor** and click **Continue** → **Done**
5. Click on the newly created service account
6. Go to the **Keys** tab → **Add Key** → **Create new key**
7. Choose **JSON** and click **Create**
8. Save the downloaded JSON file to a safe location on your machine

## Step 4: Create & Share Your Spreadsheet

1. Go to [Google Sheets](https://sheets.google.com/) and create a new spreadsheet
2. Name it after your course (e.g., "CS301 Attendance")
3. Copy the spreadsheet ID from the URL:
   ```
   https://docs.google.com/spreadsheets/d/SPREADSHEET_ID_HERE/edit
   ```
4. Click **Share** on the spreadsheet
5. Add the service account email (found in your JSON file as `client_email`, looks like `name@project.iam.gserviceaccount.com`)
6. Give it **Editor** access and click **Send**

Repeat step 4 for each course you want to track.

## Step 5: Configure in the App

1. Open the teacher configuration page (`/teacher/config`)
2. Under **Storage Backend**, select **Google Sheets** (or **Both** for dual-write)
3. Set the **Service Account JSON Path** to the absolute path of your downloaded JSON file
   - Example: `/Users/professor/credentials/attendance-service-account.json`
4. Set the **Spreadsheet Key / Mapping**:
   - **Single spreadsheet for all courses**: Just paste the spreadsheet ID
   - **One spreadsheet per course**: Use the format `CS301=ID1,MA101=ID2`
5. Click **Save Settings**

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Google credentials path not configured" | Set the path in teacher configuration |
| "Permission denied" or 403 error | Make sure you shared the spreadsheet with the service account email |
| "Spreadsheet not found" | Double-check the spreadsheet ID (the long string from the URL) |
| "Google Sheets API has not been enabled" | Enable it in Google Cloud Console (Step 2) |

## Cost

Google Sheets API is **free** for reasonable usage:
- 300 read requests per minute per project
- 60 write requests per minute per user per project
- Easily sufficient for classroom attendance (~30-100 students)
