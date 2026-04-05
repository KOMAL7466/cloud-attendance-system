import json
import boto3
import os
from datetime import datetime

ATTENDANCE_TABLE = os.environ.get('ATTENDANCE_TABLE', 'attendance_records')
STUDENTS_TABLE = os.environ.get('STUDENTS_TABLE', 'attendance_students')

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(ATTENDANCE_TABLE)
students_table = dynamodb.Table(STUDENTS_TABLE)

def lambda_handler(event, context):
    try:
        # Add CORS headers
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
        status = body.get('status', 'present').lower()
        
        # Validate input
        if not student_id:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'student_id is required'})
            }
        
        # Verify student exists
        student_response = students_table.get_item(Key={'student_id': student_id})
        if 'Item' not in student_response:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': 'Student not found'})
            }
        
        # Check if attendance already marked for today
        existing = table.get_item(Key={
            'student_id': student_id,
            'date': date
        })
        
        if 'Item' in existing:
            # Update existing record
            table.update_item(
                Key={'student_id': student_id, 'date': date},
                UpdateExpression='SET #status = :status, updated_at = :updated_at',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': status,
                    ':updated_at': datetime.now().isoformat()
                }
            )
            message = f'Attendance updated to {status} for {student_id} on {date}'
        else:
            # Create new record
            table.put_item(Item={
                'student_id': student_id,
                'date': date,
                'status': status,
                'marked_at': datetime.now().isoformat()
            })
            message = f'Attendance marked as {status} for {student_id} on {date}'
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'success': True,
                'message': message
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': headers if 'headers' in locals() else {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)})
        }