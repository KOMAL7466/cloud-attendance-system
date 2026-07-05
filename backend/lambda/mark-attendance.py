import json
import boto3
import os
from datetime import datetime
import hashlib
import hmac
from email_service import send_email, SENDER_EMAIL, ADMIN_EMAIL

# Hardcoded config
ATTENDANCE_TABLE = 'attendance_records'
STUDENTS_TABLE = 'attendance_students'
USERS_TABLE = 'attendance_users'
LEAVE_TABLE = 'leave_applications'

dynamodb = boto3.resource('dynamodb')
attendance_table = dynamodb.Table(ATTENDANCE_TABLE)
students_table = dynamodb.Table(STUDENTS_TABLE)
users_table = dynamodb.Table(USERS_TABLE)
leave_table = dynamodb.Table(LEAVE_TABLE)

def lambda_handler(event, context):
    try:
        # CORS headers
        headers = {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
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
        student_id = body.get('student_id')
        date = body.get('date', datetime.now().strftime('%Y-%m-%d'))
        status = body.get('status', 'absent').lower()  # present, absent, leave
        leave_subject = body.get('leave_subject', '')
        leave_message = body.get('leave_message', '')
        marked_by = body.get('marked_by', 'student')
        
        # Validate input
        if not student_id:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'student_id is required'})
            }
        
        # ============================================
        # 1. VERIFY STUDENT EXISTS
        # ============================================
        student_response = students_table.get_item(Key={'student_id': student_id})
        if 'Item' not in student_response:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': 'Student not found'})
            }
        
        student = student_response['Item']
        student_name = student.get('name', 'Unknown')
        student_email = student.get('email', '')
        student_department = student.get('department', 'N/A')
        student_branch = student.get('branch', 'N/A')
        student_batch = student.get('batch', 'N/A')
        
        # ============================================
        # 2. AUTO-ABSENT: If no action, mark as absent
        # ============================================
        # If status is not 'present' or 'leave', mark as absent
        if status not in ['present', 'leave']:
            status = 'absent'
        
        # ============================================
        # 3. CHECK IF ATTENDANCE ALREADY MARKED
        # ============================================
        existing = attendance_table.get_item(Key={
            'student_id': student_id,
            'date': date
        })
        
        current_time = datetime.now()
        day_of_week = current_time.strftime('%A')
        
        if 'Item' in existing:
            # Update existing record
            attendance_table.update_item(
                Key={'student_id': student_id, 'date': date},
                UpdateExpression='SET #status = :status, updated_at = :updated_at, marked_by = :marked_by, day = :day',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': status,
                    ':updated_at': current_time.isoformat(),
                    ':marked_by': marked_by,
                    ':day': day_of_week
                }
            )
            message = f'Attendance updated to {status} for {student_id} on {date}'
        else:
            # Create new record
            attendance_table.put_item(Item={
                'student_id': student_id,
                'date': date,
                'status': status,
                'marked_at': current_time.isoformat(),
                'marked_by': marked_by,
                'day': day_of_week
            })
            message = f'Attendance marked as {status} for {student_id} on {date}'
        
        # ============================================
        # 4. LEAVE APPLICATION
        # ============================================
        leave_applied = False
        if status == 'leave' and leave_subject:
            # Store leave application
            leave_item = {
                'student_id': student_id,
                'date': date,
                'student_name': student_name,
                'student_email': student_email,
                'department': student_department,
                'branch': student_branch,
                'batch': student_batch,
                'subject': leave_subject,
                'message': leave_message,
                'status': 'pending',
                'applied_at': current_time.isoformat()
            }
            leave_table.put_item(Item=leave_item)
            leave_applied = True
        
        # ============================================
        # 5. SEND EMAIL NOTIFICATION TO ADMIN
        # ============================================
        email_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .header {{ background: #667eea; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .status-present {{ color: green; font-weight: bold; }}
                .status-absent {{ color: red; font-weight: bold; }}
                .status-leave {{ color: orange; font-weight: bold; }}
                .info-box {{ background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 10px 0; }}
                .footer {{ margin-top: 20px; padding: 10px; background: #f8f9fa; text-align: center; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>📋 Attendance Update</h2>
            </div>
            <div class="content">
                <h3>Student Details</h3>
                <div class="info-box">
                    <p><strong>Student ID:</strong> {student_id}</p>
                    <p><strong>Name:</strong> {student_name}</p>
                    <p><strong>Email:</strong> {student_email}</p>
                    <p><strong>Department:</strong> {student_department}</p>
                    <p><strong>Branch:</strong> {student_branch}</p>
                    <p><strong>Batch:</strong> {student_batch}</p>
                    <p><strong>Date:</strong> {date}</p>
                    <p><strong>Day:</strong> {day_of_week}</p>
                    <p><strong>Status:</strong> <span class="status-{status}">{status.upper()}</span></p>
                    <p><strong>Marked By:</strong> {marked_by}</p>
                    <p><strong>Time:</strong> {current_time.strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
        """
        
        if leave_applied:
            email_body += f"""
                <h3>📝 Leave Application</h3>
                <div class="info-box" style="border-left: 4px solid orange;">
                    <p><strong>Subject:</strong> {leave_subject}</p>
                    <p><strong>Message:</strong> {leave_message}</p>
                    <p><strong>Status:</strong> ⏳ Pending Approval</p>
                </div>
            """
        
        email_body += f"""
            </div>
            <div class="footer">
                <p>This is an automated email from Cloud Attendance System</p>
                <p>Administrator: Mohit Dahiya | {SENDER_EMAIL}</p>
            </div>
        </body>
        </html>
        """
        
        # Send email to admin
        send_email(ADMIN_EMAIL, f'📋 Attendance Update - {student_name} ({status.upper()})', email_body)
        
        # ============================================
        # 6. SEND CONFIRMATION TO STUDENT (if email exists)
        # ============================================
        if student_email and status != 'absent':
            student_email_body = f"""
            <html>
            <body>
                <h2 style="color: #667eea;">✅ Attendance Confirmation</h2>
                <p>Dear {student_name},</p>
                <p>Your attendance has been recorded.</p>
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px;">
                    <p><strong>Date:</strong> {date}</p>
                    <p><strong>Status:</strong> <span style="color: {'green' if status == 'present' else 'orange'};">{status.upper()}</span></p>
                    <p><strong>Time:</strong> {current_time.strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
                <hr>
                <p style="font-size: 12px; color: #666;">Cloud Attendance System</p>
            </body>
            </html>
            """
            send_email(student_email, f'✅ Attendance Confirmation - {date}', student_email_body)
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'success': True,
                'message': message,
                'attendance': {
                    'student_id': student_id,
                    'student_name': student_name,
                    'date': date,
                    'status': status,
                    'day': day_of_week,
                    'marked_at': current_time.isoformat(),
                    'marked_by': marked_by
                },
                'leave_applied': leave_applied,
                'email_sent': True
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