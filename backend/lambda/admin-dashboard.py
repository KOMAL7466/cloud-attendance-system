import json
import boto3
import os
from datetime import datetime, timedelta

# Environment variables with defaults
ATTENDANCE_TABLE = os.environ.get('ATTENDANCE_TABLE', 'attendance_records')
STUDENTS_TABLE = os.environ.get('STUDENTS_TABLE', 'attendance_students')
USERS_TABLE = os.environ.get('USERS_TABLE', 'attendance_users')

dynamodb = boto3.resource('dynamodb')
attendance_table = dynamodb.Table(ATTENDANCE_TABLE)
students_table = dynamodb.Table(STUDENTS_TABLE)
users_table = dynamodb.Table(USERS_TABLE)

def lambda_handler(event, context):
    try:
        # Get auth token from headers
        headers = event.get('headers', {})
        auth_token = headers.get('Authorization', '').replace('Bearer ', '')
        
        # Verify admin role (simplified for now)
        # In production, verify JWT token
        
        # Get all students
        students_response = students_table.scan()
        students = students_response.get('Items', [])
        
        # Get attendance records for last 30 days
        date_limit = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        attendance_response = attendance_table.scan()
        attendance_records = attendance_response.get('Items', [])
        
        # Filter last 30 days
        recent_records = [r for r in attendance_records if r.get('date', '') >= date_limit]
        
        # Calculate daily attendance
        daily_attendance = {}
        for record in recent_records:
            date = record.get('date')
            if not date:
                continue
            if date not in daily_attendance:
                daily_attendance[date] = {'present': 0, 'absent': 0, 'total': 0}
            if record.get('status') == 'present':
                daily_attendance[date]['present'] += 1
            else:
                daily_attendance[date]['absent'] += 1
            daily_attendance[date]['total'] += 1
        
        # Calculate student-wise attendance percentage
        student_attendance = {}
        for record in attendance_records:
            sid = record.get('student_id')
            if not sid:
                continue
            if sid not in student_attendance:
                student_attendance[sid] = {'present': 0, 'total': 0}
            if record.get('status') == 'present':
                student_attendance[sid]['present'] += 1
            student_attendance[sid]['total'] += 1
        
        # Get student names
        student_names = {s.get('student_id'): s.get('name', 'Unknown') for s in students}
        
        attendance_percentages = []
        for sid, data in student_attendance.items():
            percentage = (data['present'] / data['total'] * 100) if data['total'] > 0 else 0
            attendance_percentages.append({
                'student_id': sid,
                'name': student_names.get(sid, 'Unknown'),
                'percentage': round(percentage, 2),
                'present': data['present'],
                'total': data['total']
            })
        
        # Get total users
        users_response = users_table.scan()
        total_users = len(users_response.get('Items', []))
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': True,
                'total_students': len(students),
                'total_users': total_users,
                'daily_attendance': daily_attendance,
                'student_attendance': attendance_percentages,
                'last_updated': datetime.now().isoformat()
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e)})
        }