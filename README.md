# Google Classroom Auto-Submitter

This application automatically monitors all your Google Classroom courses and assignments, submitting any uploaded files one minute before their deadlines. It's perfect for students who upload their work but forget to submit it before the deadline.

## Prerequisites

1. Python 3.7 or higher
2. A Google account with access to Google Classroom
3. Google Cloud Project with Classroom API enabled

## Setup

1. Clone this repository
2. Install the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Set up Google Cloud Project:

   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project
   - Enable the Google Classroom API
   - Create OAuth 2.0 credentials
   - Download the credentials and save them as `credentials.json` in the project directory

## Usage

1. Run the application:

   ```bash
   python gcr_auto_submitter.py
   ```

2. On first run, you'll be prompted to authenticate with your Google account through your browser.

3. The application will:
   - Automatically detect all your Google Classroom courses
   - Monitor all assignments in these courses
   - Find any uploaded files in the assignment materials
   - Submit these files one minute before the deadline
   - Keep track of submissions to avoid duplicate submissions

## How It Works

1. The application runs continuously, checking all courses and assignments every minute
2. For each assignment:
   - It checks if there's a deadline
   - If within 1 minute of the deadline, it looks for uploaded files
   - If files are found and not already submitted, it automatically submits them
   - It maintains a history of submissions to prevent duplicate submissions

## Troubleshooting

If you encounter any issues:

1. Delete `token.pickle` and restart the application
2. Make sure your Google Cloud Project has the Classroom API enabled
3. Check that you have the necessary permissions in Google Classroom
4. Ensure you have uploaded files to the assignment materials
