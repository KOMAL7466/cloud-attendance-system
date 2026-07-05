import json
import boto3
import os
from datetime import datetime, timedelta
from boto3.dynamodb.conditions import Key, Attr

# Hardcoded config
ATTENDANCE_TABLE = 'attendance_records'
STUDENTS_TABLE = 'attendance_students'
USERS_TABLE = 'attendance_users'

dynamodb = boto3.resource('dynamodb')
attendance_table = dynamodb.Table(ATTENDANCE_TABLE)
students_table = dynamodb.Table(STUDENTS_TABLE)
users_table = dynamodb.Table(USERS_TABLE)

def lambda_handler(event, context):
    try:
        # CORS headers
        headers = {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization'
        }
        
        # Handle preflight
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({})
            }
        
        # Get query parameters
        query_params = event.get('queryStringParameters', {}) or {}
        student_id = query_params.get('student_id')
        start_date = query_params.get('start_date')
        end_date = query_params.get('end_date')
        department = query_params.get('department')
        branch = query_params.get('branch')
        batch = query_params.get('batch')
        status_filter = query_params.get('status')  # present, absent, leave
        limit = int(query_params.get('limit', 100))
        
        # Get all students first
        students_response = students_table.scan()
        all_students = students_response.get('Items', [])
        students_dict = {s['student_id']: s for s in all_students}
        
        # Filter students by department/branch/batch if specified
        filtered_student_ids = None
        if department or branch or batch:
            filtered_student_ids = []
            for student in all_students:
                match = True
                if department and student.get('department') != department:
                    match = False
                if branch and student.get('branch') != branch:
                    match = False
                if batch and student.get('batch') != batch:
                    match = False
                if match:
                    filtered_student_ids.append(student['student_id'])
        
        # Get attendance records
        if student_id:
            # Get attendance for specific student
            response = attendance_table.query(
                KeyConditionExpression='student_id = :sid',
                ExpressionAttributeValues={':sid': student_id}
            )
            attendance_records = response.get('Items', [])
        else:
            # Get all attendance records
            response = attendance_table.scan()
            attendance_records = response.get('Items', [])
        
        # Apply filters
        filtered_records = []
        for record in attendance_records:
            # Filter by student ID list (department/branch/batch filter)
            if filtered_student_ids is not None:
                if record['student_id'] not in filtered_student_ids:
                    continue
            
            # Filter by date range
            if start_date and record.get('date', '') < start_date:
                continue
            if end_date and record.get('date', '') > end_date:
                continue
            
            # Filter by status
            if status_filter and record.get('status', '').lower() != status_filter.lower():
                continue
            
            filtered_records.append(record)
        
        # Sort records by date (newest first)
        filtered_records.sort(key=lambda x: x.get('date', ''), reverse=True)
        
        # Limit results
        if len(filtered_records) > limit:
            filtered_records = filtered_records[:limit]
        
        # Add student details to records
        for record in filtered_records:
            student = students_dict.get(record['student_id'], {})
            record['student_name'] = student.get('name', 'Unknown')
            record['student_email'] = student.get('email', '')
            record['student_department'] = student.get('department', 'N/A')
            record['student_branch'] = student.get('branch', 'N/A')
            record['student_batch'] = student.get('batch', 'N/A')
            record['admission_year'] = student.get('admission_year', 'N/A')
        
        # ============================================
        # CALCULATE STATISTICS
        # ============================================
        
        # Overall statistics
        total_days = len(filtered_records)
        present_days = len([r for r in filtered_records if r.get('status', '').lower() == 'present'])
        absent_days = len([r for r in filtered_records if r.get('status', '').lower() == 'absent'])
        leave_days = len([r for r in filtered_records if r.get('status', '').lower() == 'leave'])
        
        attendance_percentage = round((present_days / total_days * 100), 2) if total_days > 0 else 0
        
        # Department wise statistics
        dept_stats = {}
        for record in filtered_records:
            dept = students_dict.get(record['student_id'], {}).get('department', 'Other')
            if dept not in dept_stats:
                dept_stats[dept] = {'present': 0, 'absent': 0, 'leave': 0, 'total': 0}
            status = record.get('status', 'absent').lower()
            if status == 'present':
                dept_stats[dept]['present'] += 1
            elif status == 'leave':
                dept_stats[dept]['leave'] += 1
            else:
                dept_stats[dept]['absent'] += 1
            dept_stats[dept]['total'] += 1
        
        # Calculate department percentages
        for dept, stats in dept_stats.items():
            stats['percentage'] = round((stats['present'] / stats['total'] * 100), 2) if stats['total'] > 0 else 0
        
        # Student wise summary
        student_summary = {}
        for record in filtered_records:
            sid = record['student_id']
            if sid not in student_summary:
                student_summary[sid] = {
                    'student_id': sid,
                    'name': students_dict.get(sid, {}).get('name', 'Unknown'),
                    'department': students_dict.get(sid, {}).get('department', 'N/A'),
                    'branch': students_dict.get(sid, {}).get('branch', 'N/A'),
                    'batch': students_dict.get(sid, {}).get('batch', 'N/A'),
                    'email': students_dict.get(sid, {}).get('email', ''),
                    'present': 0,
                    'absent': 0,
                    'leave': 0,
                    'total': 0
                }
            status = record.get('status', 'absent').lower()
            if status == 'present':
                student_summary[sid]['present'] += 1
            elif status == 'leave':
                student_summary[sid]['leave'] += 1
            else:
                student_summary[sid]['absent'] += 1
            student_summary[sid]['total'] += 1
        
        # Calculate percentages for each student
        for sid, data in student_summary.items():
            data['percentage'] = round((data['present'] / data['total'] * 100), 2) if data['total'] > 0 else 0
        
        # Convert to list and sort by percentage
        student_summary_list = sorted(
            list(student_summary.values()),
            key=lambda x: x['percentage'],
            reverse=True
        )
        
        # Get daily attendance trend
        daily_trend = {}
        for record in filtered_records:
            date = record.get('date')
            if date:
                if date not in daily_trend:
                    daily_trend[date] = {'present': 0, 'absent': 0, 'leave': 0, 'total': 0}
                status = record.get('status', 'absent').lower()
                if status == 'present':
                    daily_trend[date]['present'] += 1
                elif status == 'leave':
                    daily_trend[date]['leave'] += 1
                else:
                    daily_trend[date]['absent'] += 1
                daily_trend[date]['total'] += 1
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'success': True,
                'records': filtered_records,
                'statistics': {
                    'total_days': total_days,
                    'present_days': present_days,
                    'absent_days': absent_days,
                    'leave_days': leave_days,
                    'attendance_percentage': attendance_percentage,
                    'department_stats': dept_stats,
                    'student_summary': student_summary_list,
                    'daily_trend': daily_trend
                },
                'filters_applied': {
                    'student_id': student_id,
                    'start_date': start_date,
                    'end_date': end_date,
                    'department': department,
                    'branch': branch,
                    'batch': batch,
                    'status': status_filter,
                    'limit': limit
                },
                'total_records': len(filtered_records)
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