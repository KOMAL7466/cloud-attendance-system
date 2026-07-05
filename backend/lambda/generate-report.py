import json
import boto3
import os
from datetime import datetime
import csv
from io import StringIO, BytesIO
import base64
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')
ses = boto3.client('ses', region_name='ap-south-1')

attendance_table = dynamodb.Table(os.environ['ATTENDANCE_TABLE'])
students_table = dynamodb.Table(os.environ['STUDENTS_TABLE'])
users_table = dynamodb.Table(os.environ.get('USERS_TABLE', 'attendance_users'))

BUCKET_NAME = os.environ['REPORT_BUCKET']
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'dahiyamohit764@gmail.com')
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'dahiyamohit764@gmail.com')

# Admin Signature (can be stored in S3 or as base64 string)
ADMIN_SIGNATURE = """
<div style="margin-top: 30px; border-top: 2px solid #667eea; padding-top: 20px;">
    <p style="font-family: 'Brush Script MT', cursive; font-size: 24px; color: #333;">
        Mohit Dahiya
    </p>
    <p style="color: #666; font-size: 14px;">Administrator</p>
    <p style="color: #999; font-size: 12px;">Cloud Attendance System</p>
    <p style="color: #999; font-size: 12px;">Date: {date}</p>
</div>
"""

def send_email(to_email, subject, body, attachment=None, filename=None):
    """Send email using AWS SES with optional attachment"""
    try:
        if attachment:
            # Create multipart message
            msg = MIMEMultipart()
            msg['Subject'] = subject
            msg['From'] = SENDER_EMAIL
            msg['To'] = to_email
            
            # Attach body
            msg.attach(MIMEText(body, 'html'))
            
            # Attach file
            if attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment)
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename={filename}'
                )
                msg.attach(part)
            
            # Send email using SES
            response = ses.send_raw_email(
                Source=SENDER_EMAIL,
                Destinations=[to_email],
                RawMessage={'Data': msg.as_string()}
            )
        else:
            # Send simple email
            response = ses.send_email(
                Source=SENDER_EMAIL,
                Destination={'ToAddresses': [to_email]},
                Message={
                    'Subject': {'Data': subject},
                    'Body': {'Html': {'Data': body}}
                }
            )
        
        print(f"✅ Email sent to {to_email}")
        return True
    except Exception as e:
        print(f"❌ Email error: {e}")
        return False

def generate_pdf_report(records, students, report_type, date, admin_name='Mohit Dahiya'):
    """Generate PDF report as HTML (will be converted to PDF)"""
    
    # Calculate statistics
    total_records = len(records)
    present_records = len([r for r in records if r.get('status') == 'present'])
    absent_records = len([r for r in records if r.get('status') == 'absent'])
    leave_records = len([r for r in records if r.get('status') == 'leave'])
    
    # Department wise breakdown
    dept_stats = {}
    for record in records:
        student = students.get(record['student_id'], {})
        dept = student.get('department', 'Other')
        if dept not in dept_stats:
            dept_stats[dept] = {'present': 0, 'absent': 0, 'leave': 0, 'total': 0}
        status = record.get('status', 'absent')
        if status == 'present':
            dept_stats[dept]['present'] += 1
        elif status == 'leave':
            dept_stats[dept]['leave'] += 1
        else:
            dept_stats[dept]['absent'] += 1
        dept_stats[dept]['total'] += 1
    
    # Generate HTML report
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Attendance Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; color: #333; }}
            .header {{ text-align: center; border-bottom: 3px solid #667eea; padding-bottom: 20px; margin-bottom: 30px; }}
            .header h1 {{ color: #667eea; font-size: 28px; margin: 0; }}
            .header p {{ color: #666; margin: 5px 0; }}
            .info-box {{ background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
            .info-box table {{ width: 100%; }}
            .info-box td {{ padding: 5px 10px; }}
            table.report {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
            table.report th {{ background: #667eea; color: white; padding: 12px; text-align: left; }}
            table.report td {{ padding: 10px; border-bottom: 1px solid #ddd; }}
            table.report tr:hover {{ background: #f5f5f5; }}
            .status-present {{ color: green; font-weight: bold; }}
            .status-absent {{ color: red; font-weight: bold; }}
            .status-leave {{ color: orange; font-weight: bold; }}
            .summary {{ background: #f0f4ff; padding: 20px; border-radius: 8px; margin: 20px 0; }}
            .summary-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; }}
            .summary-item {{ text-align: center; background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
            .summary-item .number {{ font-size: 24px; font-weight: bold; color: #667eea; }}
            .summary-item .label {{ color: #666; font-size: 14px; }}
            .dept-stats {{ margin: 20px 0; }}
            .dept-card {{ background: white; padding: 15px; border-radius: 8px; margin: 10px 0; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
            .signature {{ margin-top: 40px; border-top: 2px solid #667eea; padding-top: 20px; text-align: right; }}
            .signature .name {{ font-family: 'Brush Script MT', cursive; font-size: 28px; color: #333; }}
            .signature .title {{ color: #666; font-size: 14px; }}
            .footer {{ text-align: center; margin-top: 30px; color: #999; font-size: 12px; border-top: 1px solid #ddd; padding-top: 15px; }}
            @media print {{
                .no-print {{ display: none; }}
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📊 Cloud Attendance System</h1>
            <h2>Attendance Report - {report_type.upper()}</h2>
            <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Report Period: {date}</p>
        </div>
        
        <div class="info-box">
            <table>
                <tr><td><strong>Report Type:</strong></td><td>{report_type.upper()}</td></tr>
                <tr><td><strong>Date:</strong></td><td>{date}</td></tr>
                <tr><td><strong>Total Records:</strong></td><td>{total_records}</td></tr>
            </table>
        </div>
        
        <div class="summary">
            <h3>📈 Attendance Summary</h3>
            <div class="summary-grid">
                <div class="summary-item">
                    <div class="number">{total_records}</div>
                    <div class="label">Total Records</div>
                </div>
                <div class="summary-item">
                    <div class="number" style="color: green;">{present_records}</div>
                    <div class="label">Present</div>
                </div>
                <div class="summary-item">
                    <div class="number" style="color: orange;">{leave_records}</div>
                    <div class="label">Leave</div>
                </div>
                <div class="summary-item">
                    <div class="number" style="color: red;">{absent_records}</div>
                    <div class="label">Absent</div>
                </div>
            </div>
        </div>
        
        <div class="dept-stats">
            <h3>📚 Department Wise Breakdown</h3>
    """
    
    for dept, stats in dept_stats.items():
        percentage = (stats['present'] / stats['total'] * 100) if stats['total'] > 0 else 0
        html += f"""
            <div class="dept-card">
                <strong>{dept}</strong>
                <span style="float: right;">
                    Present: {stats['present']} | 
                    Leave: {stats['leave']} | 
                    Absent: {stats['absent']} | 
                    Total: {stats['total']} | 
                    <span style="color: #667eea; font-weight: bold;">{percentage:.1f}%</span>
                </span>
            </div>
        """
    
    html += """
        </div>
        
        <h3>📋 Detailed Attendance Records</h3>
        <table class="report">
            <thead>
                <tr>
                    <th>#</th>
                    <th>Student ID</th>
                    <th>Student Name</th>
                    <th>Department</th>
                    <th>Branch</th>
                    <th>Batch</th>
                    <th>Date</th>
                    <th>Status</th>
                    <th>Marked At</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for i, record in enumerate(records, 1):
        student = students.get(record['student_id'], {})
        status_class = f"status-{record.get('status', 'absent')}"
        status_display = record.get('status', 'Absent').upper()
        html += f"""
            <tr>
                <td>{i}</td>
                <td>{record['student_id']}</td>
                <td>{student.get('name', 'Unknown')}</td>
                <td>{student.get('department', 'N/A')}</td>
                <td>{student.get('branch', 'N/A')}</td>
                <td>{student.get('batch', 'N/A')}</td>
                <td>{record.get('date', 'N/A')}</td>
                <td class="{status_class}">{status_display}</td>
                <td>{record.get('marked_at', 'N/A')[:19] if record.get('marked_at') else 'N/A'}</td>
            </tr>
        """
    
    html += f"""
            </tbody>
        </table>
        
        <div class="signature">
            <div class="name">Mohit Dahiya</div>
            <div class="title">Administrator</div>
            <div style="color: #999; font-size: 12px;">{datetime.now().strftime('%Y-%m-%d')}</div>
        </div>
        
        <div class="footer">
            <p>This is a system-generated report from Cloud Attendance System</p>
            <p>For any queries, contact: {SENDER_EMAIL}</p>
        </div>
    </body>
    </html>
    """
    
    return html

def lambda_handler(event, context):
    try:
        # CORS headers
        headers = {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization'
        }
        
        # Handle preflight
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({})
            }
        
        body = json.loads(event.get('body', '{}'))
        report_type = body.get('type', 'daily')
        date = body.get('date', datetime.now().strftime('%Y-%m-%d'))
        send_email_to = body.get('send_email', False)
        email_recipient = body.get('email', ADMIN_EMAIL)
        department_filter = body.get('department', None)
        batch_filter = body.get('batch', None)
        
        # Get all attendance records
        attendance_response = attendance_table.scan()
        all_records = attendance_response.get('Items', [])
        
        # Filter by date and type
        if report_type == 'daily':
            records = [r for r in all_records if r.get('date') == date]
        elif report_type == 'monthly':
            month = date[:7]  # YYYY-MM
            records = [r for r in all_records if r.get('date', '').startswith(month)]
        else:  # yearly
            year = date[:4]  # YYYY
            records = [r for r in all_records if r.get('date', '').startswith(year)]
        
        # Get student details
        students_response = students_table.scan()
        students = {s['student_id']: s for s in students_response.get('Items', [])}
        
        # Filter by department if specified
        if department_filter:
            filtered_students = [sid for sid, s in students.items() if s.get('department') == department_filter]
            records = [r for r in records if r['student_id'] in filtered_students]
        
        # Filter by batch if specified
        if batch_filter:
            filtered_students = [sid for sid, s in students.items() if s.get('batch') == batch_filter]
            records = [r for r in records if r['student_id'] in filtered_students]
        
        # Sort records by date
        records.sort(key=lambda x: x.get('date', ''))
        
        # Generate HTML report
        html_report = generate_pdf_report(records, students, report_type, date, admin_name='Mohit Dahiya')
        
        # Generate CSV report for backup
        csv_output = StringIO()
        csv_writer = csv.writer(csv_output)
        csv_writer.writerow(['Student ID', 'Name', 'Department', 'Branch', 'Batch', 'Date', 'Status', 'Marked At'])
        
        for record in records:
            student = students.get(record['student_id'], {})
            csv_writer.writerow([
                record['student_id'],
                student.get('name', 'Unknown'),
                student.get('department', 'N/A'),
                student.get('branch', 'N/A'),
                student.get('batch', 'N/A'),
                record.get('date', ''),
                record.get('status', ''),
                record.get('marked_at', '')
            ])
        
        csv_data = csv_output.getvalue()
        
        # Upload to S3
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        csv_filename = f"reports/{report_type}_attendance_{date}_{timestamp}.csv"
        html_filename = f"reports/{report_type}_attendance_{date}_{timestamp}.html"
        
        # Upload CSV to S3
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=csv_filename,
            Body=csv_data.encode('utf-8'),
            ContentType='text/csv'
        )
        
        # Upload HTML to S3
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=html_filename,
            Body=html_report.encode('utf-8'),
            ContentType='text/html'
        )
        
        # Generate download URLs
        csv_url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': BUCKET_NAME, 'Key': csv_filename},
            ExpiresIn=3600
        )
        
        html_url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': BUCKET_NAME, 'Key': html_filename},
            ExpiresIn=3600
        )
        
        # Send email if requested
        email_sent = False
        if send_email_to and email_recipient:
            email_subject = f"📊 Attendance Report - {report_type.upper()} ({date})"
            email_body = f"""
            <html>
            <body>
            <h2 style="color: #667eea;">📊 Attendance Report</h2>
            <p>Dear User,</p>
            <p>Please find the attendance report attached below.</p>
            
            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 15px 0;">
                <p><strong>Report Type:</strong> {report_type.upper()}</p>
                <p><strong>Date:</strong> {date}</p>
                <p><strong>Total Records:</strong> {len(records)}</p>
                <p><strong>Generated By:</strong> Mohit Dahiya (Administrator)</p>
            </div>
            
            <p><strong>Download Links:</strong></p>
            <ul>
                <li><a href="{html_url}">📄 HTML Report</a></li>
                <li><a href="{csv_url}">📊 CSV Report</a></li>
            </ul>
            
            <hr>
            <p style="color: #999; font-size: 12px;">
                This is an automated email from Cloud Attendance System.<br>
                Administrator: Mohit Dahiya | {SENDER_EMAIL}
            </p>
            </body>
            </html>
            """
            
            # Convert HTML to PDF attachment (simplified - using HTML as PDF)
            # In production, use a PDF generation library like reportlab
            
            email_sent = send_email(
                email_recipient,
                email_subject,
                email_body,
                None,  # No attachment for now
                None
            )
            
            # Also send to admin
            if email_recipient != ADMIN_EMAIL:
                send_email(
                    ADMIN_EMAIL,
                    f"📊 Report Sent to {email_recipient}",
                    f"<p>Report of type {report_type} for {date} has been sent to {email_recipient}</p>"
                )
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'success': True,
                'message': 'Report generated successfully',
                'report_type': report_type,
                'date': date,
                'record_count': len(records),
                'csv_url': csv_url,
                'html_url': html_url,
                'csv_filename': csv_filename,
                'html_filename': html_filename,
                'email_sent': email_sent,
                'email_recipient': email_recipient if email_sent else None,
                'admin_signature': 'Mohit Dahiya',
                'department_filter': department_filter,
                'batch_filter': batch_filter,
                'generated_at': datetime.now().isoformat()
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': headers if 'headers' in locals() else {'Content-Type': 'application/json'},
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        }