import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import *


def _send(to_email, subject, body):
    msg = MIMEMultipart()
    msg["From"] = GMAIL_USER
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.send_message(msg)


def send_interview_notification(to_email, name, job_title):
    subject = f"Interview Scheduled - {job_title}"
    body = f"""Dear {name},

You have been shortlisted for {job_title}.

Your AI Interview is now available on the platform.
Login to your dashboard to start.

Platform: http://localhost:3000/candidate/dashboard

Important:
- Interview available for 24 hours only
- Maximum 3 attempts allowed
- Ensure good lighting and quiet environment

Best regards,
RecruitAI Team
"""
    _send(to_email, subject, body)


def send_selection_email(to_email, name, job_title, company):
    subject = f"Congratulations! Selected for {job_title}"
    body = f"""Dear {name},

Great news! You have been SELECTED for the position of {job_title} at {company}.

The recruiter will contact you soon with next steps.

You can view your status on the platform:
http://localhost:3000/candidate/dashboard

Congratulations once again!

Best regards,
RecruitAI Team
"""
    _send(to_email, subject, body)


def send_rejection_email(to_email, name, job_title, company):
    subject = f"Application Update - {job_title}"
    body = f"""Dear {name},

Thank you for applying for {job_title} at {company}.

After careful consideration, we have decided to move forward with other candidates whose profile more closely matches our requirements.

Don't lose hope! Check your skill gap analysis and learning recommendations on the platform to improve your chances next time.

Platform: http://localhost:3000/candidate/applications

We wish you all the best for your future endeavors.

Best regards,
RecruitAI Team
"""
    _send(to_email, subject, body)


def send_report_ready_email(to_email, hr_name, candidate_name, job_title):
    subject = f"Interview Report Ready - {candidate_name}"
    body = f"""Dear {hr_name},

The AI interview for {candidate_name} ({job_title}) has been completed.

The detailed report is now available on your dashboard:
http://localhost:3000/hr/dashboard

You can now review scores, observations, and make your final decision.

Best regards,
RecruitAI Team
"""
    _send(to_email, subject, body)


def send_reminder_email(to_email, name, job_title, hours_left):
    subject = f"Reminder: Interview pending for {job_title}"
    body = f"""Dear {name},

This is a friendly reminder that your AI interview for {job_title} expires in {hours_left} hours.

Please complete it as soon as possible.

Start Interview: http://localhost:3000/candidate/dashboard

Best regards,
RecruitAI Team
"""
    _send(to_email, subject, body)