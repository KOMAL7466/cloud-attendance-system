import json
import boto3
import os
from datetime import datetime, timedelta

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['ATTENDANCE_TABLE'])
students_table = dynamodb.Table(os.environ['STUDENTS_TABLE'])

def lambda_handler(event, context):
    try:
        query_params = event.get('queryStringParameters', {})
        student_id = query_params.get('student_id')
        start_date = query_params.get('start_date')
        end_date = query_params.get('end_date')
        
        if student_id:
            # Get attendance for specific student
            response = table.query(
                KeyConditionExpression='student_id = :sid',
                ExpressionAttributeValues={':sid': student_id}
            )
        else:
            # Scan all attendance (for admin)
            response = table.scan()
        
        attendance_records = response.get('Items', [])
        
        # Calculate statistics
        total_days = len(attendance_records)
        present_days = len([r for r in attendance_records if r.get('status') == 'Present'])
        absent_days = len([r for r in attendance_records if r.get('status') == 'Absent'])
        
        # Get student names
        students = {}
        all_students = students_table.scan().get('Items', [])
        for student in all_students:
            students[student['student_id']] = student['name']
        
        # Add student names to records
        for record in attendance_records:
            record['student_name'] = students.get(record['student_id'], 'Unknown')
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'records': attendance_records,
                'statistics': {
                    'total_days': total_days,
                    'present_days': present_days,
                    'absent_days': absent_days,
                    'attendance_percentage': round((present_days / total_days * 100) if total_days > 0 else 0, 2)
                }
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }