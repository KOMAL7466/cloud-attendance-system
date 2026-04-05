import json
import boto3
import os
from datetime import datetime
import csv
from io import StringIO

dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')
attendance_table = dynamodb.Table(os.environ['ATTENDANCE_TABLE'])
students_table = dynamodb.Table(os.environ['STUDENTS_TABLE'])

BUCKET_NAME = os.environ['REPORT_BUCKET']

def lambda_handler(event, context):
    try:
        body = json.loads(event['body'])
        report_type = body.get('type', 'daily')
        date = body.get('date', datetime.now().strftime('%Y-%m-%d'))
        
        # Get attendance data
        if report_type == 'daily':
            attendance_response = attendance_table.scan()
            records = [r for r in attendance_response.get('Items', []) if r['date'] == date]
        else:
            attendance_response = attendance_table.scan()
            records = attendance_response.get('Items', [])
        
        # Get student details
        students_response = students_table.scan()
        students = {s['student_id']: s for s in students_response.get('Items', [])}
        
        # Create CSV report
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Student ID', 'Name', 'Date', 'Status', 'Marked At'])
        
        # Write data
        for record in records:
            student = students.get(record['student_id'], {})
            writer.writerow([
                record['student_id'],
                student.get('name', 'Unknown'),
                record['date'],
                record.get('status', ''),
                record.get('marked_at', '')
            ])
        
        # Upload to S3
        filename = f"reports/{report_type}attendance{date}{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=filename,
            Body=output.getvalue().encode('utf-8'),
            ContentType='text/csv'
        )
        
        # Generate download URL
        url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': BUCKET_NAME, 'Key': filename},
            ExpiresIn=3600
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'report_url': url,
                'filename': filename,
                'record_count': len(records)
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }