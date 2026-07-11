from datetime import datetime, timedelta
from database.mysql_db import execute_query
from services.email_service import send_reminder_email


def send_pending_reminders():
    """Send reminder for interviews expiring in 12 hours"""
    now = datetime.now()
    twelve_hr_later = now + timedelta(hours=12)
    thirteen_hr_later = now + timedelta(hours=13)

    # Find interviews expiring in 12-13 hours that haven't been attempted
    pending = execute_query(
        """SELECT a.app_id, u.name, u.email, j.title
           FROM applications a
           JOIN users u ON a.candidate_id=u.id
           JOIN jobs j ON a.job_id=j.job_id
           WHERE a.status='interview_sent'
             AND a.interview_attempts=0
             AND a.interview_expires BETWEEN %s AND %s
             AND (a.reminder_sent IS NULL OR a.reminder_sent=0)""",
        (twelve_hr_later, thirteen_hr_later), fetch=True
    )

    for app in pending:
        try:
            send_reminder_email(
                app["email"], app["name"],
                app["title"], 12
            )
            execute_query(
                "UPDATE applications SET reminder_sent=1 WHERE app_id=%s",
                (app["app_id"],)
            )
            print(f"Reminder sent to {app['email']}")
        except Exception as e:
            print(f"Failed: {e}")