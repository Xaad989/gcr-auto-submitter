import os
import time
import datetime
import pickle
import schedule
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import json
from datetime import timezone
import pytz

# If modifying these scopes, delete the file token.pickle.
SCOPES = [
    'https://www.googleapis.com/auth/classroom.coursework.me',
    'https://www.googleapis.com/auth/classroom.courses.readonly',
    'https://www.googleapis.com/auth/classroom.coursework.students',
    'https://www.googleapis.com/auth/drive.file'
]

class GoogleClassroomAutoSubmitter:
    def __init__(self):
        self.creds = None
        self.service = None
        self.authenticate()
        self.submission_history = self.load_submission_history()

    def authenticate(self):
        """Authenticate with Google Classroom API"""
        print("\nStarting authentication process...")
        if os.path.exists('token.pickle'):
            print("Found existing authentication token")
            with open('token.pickle', 'rb') as token:
                self.creds = pickle.load(token)
        
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                print("Refreshing expired token...")
                self.creds.refresh(Request())
                print("Token refreshed successfully")
            else:
                print("No valid token found. Starting OAuth flow...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                self.creds = flow.run_local_server(port=0)
                print("OAuth flow completed successfully")
            
            with open('token.pickle', 'wb') as token:
                pickle.dump(self.creds, token)
                print("Token saved for future use")

        self.service = build('classroom', 'v1', credentials=self.creds)
        print("Google Classroom API service initialized")

    def load_submission_history(self):
        """Load submission history from file"""
        if os.path.exists('submission_history.json'):
            with open('submission_history.json', 'r') as f:
                history = json.load(f)
                return history
        return {}

    def save_submission_history(self):
        """Save submission history to file"""
        with open('submission_history.json', 'w') as f:
            json.dump(self.submission_history, f)

    def get_all_courses(self):
        """Get all courses the user is enrolled in"""
        print("\nFetching courses...")
        try:
            results = self.service.courses().list(pageSize=100).execute()
            courses = results.get('courses', [])
            print(f"Found {len(courses)} courses")
            return courses
        except Exception as e:
            print(f"Error getting courses: {e}")
            return []

    def get_course_work(self, course_id):
        """Get all course work for a course"""
        try:
            results = self.service.courses().courseWork().list(
                courseId=course_id,
                pageSize=100
            ).execute()
            course_work = results.get('courseWork', [])
            print(f"Found {len(course_work)} assignments in course {course_id}")
            return course_work
        except Exception as e:
            print(f"Error getting course work for course {course_id}: {e}")
            return []

    def get_submission_status(self, course_id, course_work_id):
        """Get submission status for a course work"""
        try:
            submissions = self.service.courses().courseWork().studentSubmissions().list(
                courseId=course_id,
                courseWorkId=course_work_id,
                states=['TURNED_IN', 'RETURNED', 'RECLAIMED_BY_STUDENT']
            ).execute()
            return submissions.get('studentSubmissions', [])
        except Exception as e:
            print(f"Error getting submission status: {e}")
            return []

    def find_files_to_submit(self, course_id, course_work_id):
        """Find all files in the student's unsubmitted work"""
        try:
            # Get student submissions
            submissions = self.service.courses().courseWork().studentSubmissions().list(
                courseId=course_id,
                courseWorkId=course_work_id,
                states=['NEW', 'CREATED']
            ).execute()
            
            student_submissions = submissions.get('studentSubmissions', [])
            if not student_submissions:
                print("No unsubmitted work found")
                return []
                
            # Get all files from the submission
            file_ids = []
            for submission in student_submissions:
                attachments = submission.get('attachments', [])
                assignment_submission = submission.get('assignmentSubmission', {})
                assignment_attachments = assignment_submission.get('attachments', [])
                
                all_attachments = attachments + assignment_attachments
                
                for attachment in all_attachments:
                    if 'driveFile' in attachment:
                        drive_file = attachment['driveFile']
                        if 'title' in drive_file:
                            print(f"Found file: {drive_file['title']}")
                            file_ids.append(drive_file['id'])
            
            if not file_ids:
                print("No suitable files found in unsubmitted work")
                return []
                
            print(f"Found {len(file_ids)} files to submit")
            return file_ids
        except Exception as e:
            print(f"Error finding files: {e}")
            return []

    def submit_assignment(self, course_id, course_work_id, file_ids):
        """Submit an assignment with multiple files"""
        try:
            # First get the submission ID
            submissions = self.service.courses().courseWork().studentSubmissions().list(
                courseId=course_id,
                courseWorkId=course_work_id,
                states=['NEW', 'CREATED']
            ).execute()
            
            student_submissions = submissions.get('studentSubmissions', [])
            if not student_submissions:
                print("No submission found to turn in")
                return None
                
            submission_id = student_submissions[0]['id']
            
            # Turn in the submission
            result = self.service.courses().courseWork().studentSubmissions().turnIn(
                courseId=course_id,
                courseWorkId=course_work_id,
                id=submission_id
            ).execute()
            
            print(f"Successfully turned in {len(file_ids)} files for course work {course_work_id}")
            return result
        except Exception as e:
            print(f"Error submitting assignment: {e}")
            return None

    def check_and_submit_all(self):
        """Check all courses and assignments for submission"""
        print("\nStarting check cycle...")
        courses = self.get_all_courses()
        for course in courses:
            course_id = course['id']
            course_name = course.get('name', 'Unknown Course')
            print(f"\nChecking course: {course_name}")
            
            course_work_list = self.get_course_work(course_id)
            
            for course_work in course_work_list:
                course_work_id = course_work['id']
                work_title = course_work.get('title', 'Unknown Assignment')
                print(f"\nChecking assignment: {work_title}")
                
                # Skip if already submitted
                if f"{course_id}_{course_work_id}" in self.submission_history:
                    print("Already submitted previously")
                    continue
                
                # Check if there's a deadline
                due_date = course_work.get('dueDate', {})
                due_time = course_work.get('dueTime', {})
                
                if not due_date or not due_time:
                    print("No deadline set for this assignment")
                    continue

                # Create UTC datetime
                utc_deadline = datetime.datetime(
                    due_date.get('year'),
                    due_date.get('month'),
                    due_date.get('day'),
                    due_time.get('hours'),
                    due_time.get('minutes') or 0,
                    tzinfo=timezone.utc
                )

                # Convert to local timezone
                local_tz = pytz.timezone('Asia/Karachi')  # Change this to your timezone
                local_deadline = utc_deadline.astimezone(local_tz)

                current_time = datetime.datetime.now(local_tz)
                time_until_deadline = local_deadline - current_time

                print(f"Time until deadline: {time_until_deadline.total_seconds()} seconds")

                # Submit if within 1 minute of deadline
                if 0 < time_until_deadline.total_seconds() < 60:
                    print("Deadline approaching! Checking for files to submit...")
                    # Check if already submitted
                    submissions = self.get_submission_status(course_id, course_work_id)
                    if submissions:
                        self.submission_history[f"{course_id}_{course_work_id}"] = True
                        self.save_submission_history()
                        continue

                    # Find and submit all files
                    file_ids = self.find_files_to_submit(course_id, course_work_id)
                    if file_ids:
                        result = self.submit_assignment(course_id, course_work_id, file_ids)
                        if result:
                            self.submission_history[f"{course_id}_{course_work_id}"] = True
                            self.save_submission_history()
                    else:
                        print("No files found to submit")
                elif time_until_deadline.total_seconds() < 0:
                    print("Deadline passed")
                else:
                    print("Deadline still far away")

def main():
    print("Starting Google Classroom Auto-Submitter")
    submitter = GoogleClassroomAutoSubmitter()
    
    # Schedule the check every minute
    schedule.every(1).minutes.do(submitter.check_and_submit_all)

    print("\nAuto-submitter is running. Press Ctrl+C to stop.")
    print("Monitoring all courses and assignments...")
    
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    main() 