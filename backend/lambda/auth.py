import json
import boto3
import hashlib
import hmac
import base64
import os
import uuid  
import random
import string
from datetime import datetime, timedelta

# Environment Variables
USER_TABLE = os.environ.get('USER_TABLE', 'attendance_users')
STUDENTS_TABLE = os.environ.get('STUDENTS_TABLE', 'attendance_students')
SECRET_KEY = os.environ.get('JWT_SECRET', 'your-secret-key')

dynamodb = boto3.resource('dynamodb')
users_table = dynamodb.Table(USER_TABLE)
students_table = dynamodb.Table(STUDENTS_TABLE)

def verify_password(stored_password, provided_password, salt):
    """Verify password using HMAC"""
    new_hash = hmac.new(
        salt.encode('utf-8'),
        provided_password.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return new_hash == stored_password

def generate_salt():
    """Generate random salt"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=16))

def hash_password(password, salt):
    """Hash password using HMAC"""
    return hmac.new(
        salt.encode('utf-8'),
        password.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def send_email(to_email, subject, body):
    """Send email using SES or SMTP (placeholder for Lambda)"""
    # In production, use AWS SES
    # For now, return True (will be implemented with SES)
    print(f"📧 Would send email to: {to_email}")
    print(f"📧 Subject: {subject}")
    print(f"📧 Body: {body[:200]}...")
    return True

def lambda_handler(event, context):
    try:
        # CORS Headers
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
        action = body.get('action')
        
        # ============================================
        # 1. LOGIN ACTION
        # ============================================
        if action == 'login':
            username = body.get('username')
            password = body.get('password')
            
            if not username or not password:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({'error': 'Username and password required'})
                }
            
            # Get user from DynamoDB
            response = users_table.get_item(Key={'username': username})
            
            if 'Item' not in response:
                return {
                    'statusCode': 401,
                    'headers': headers,
                    'body': json.dumps({'error': 'Invalid credentials'})
                }
            
            user = response['Item']
            salt = user.get('salt', '')
            stored_password = user.get('password', '')
            
            # Verify password
            if verify_password(stored_password, password, salt):
                # Get student details if student
                student_data = {}
                if user.get('role') == 'student':
                    student_response = students_table.get_item(Key={'student_id': username})
                    if 'Item' in student_response:
                        student_data = student_response['Item']
                
                # Generate JWT token (using simple token for now)
                import jwt
                token = jwt.encode({
                    'username': username,
                    'role': user.get('role', 'student'),
                    'exp': datetime.utcnow() + timedelta(hours=24)
                }, SECRET_KEY, algorithm='HS256')
                
                return {
                    'statusCode': 200,
                    'headers': headers,
                    'body': json.dumps({
                        'success': True,
                        'token': token,
                        'role': user.get('role', 'student'),
                        'name': user.get('name', ''),
                        'username': username,
                        'email': user.get('email', ''),
                        'student_profile': student_data if student_data else None
                    })
                }
            
            return {
                'statusCode': 401,
                'headers': headers,
                'body': json.dumps({'error': 'Invalid credentials'})
            }
        
        # ============================================
        # 2. REGISTER ACTION (Admin Only)
        # ============================================
        elif action == 'register':
            username = body.get('username')
            password = body.get('password')
            name = body.get('name')
            role = body.get('role', 'student')
            email = body.get('email', '')
            department = body.get('department', 'Other')
            branch = body.get('branch', 'General')
            batch = body.get('batch', '1st Year')
            admission_year = body.get('admission_year', str(datetime.now().year))
            
            # Validation
            if not username or not password or not name:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({'error': 'Username, password, and name required'})
                }
            
            # Check if user exists
            response = users_table.get_item(Key={'username': username})
            if 'Item' in response:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({'error': 'Username already exists'})
                }
            
            # Generate salt and hash password
            salt = generate_salt()
            password_hash = hash_password(password, salt)
            
            # Store user
            user_item = {
                'username': username,
                'password': password_hash,
                'salt': salt,
                'name': name,
                'role': role,
                'email': email,
                'created_at': datetime.now().isoformat()
            }
            
            # If student, also store in students table
            if role == 'student':
                student_item = {
                    'student_id': username,
                    'name': name,
                    'email': email,
                    'department': department,
                    'branch': branch,
                    'batch': batch,
                    'admission_year': admission_year,
                    'created_at': datetime.now().isoformat()
                }
                students_table.put_item(Item=student_item)
                
                # Send credentials email
                email_body = f"""
                <html>
                <body>
                <h2 style="color: #667eea;">🎓 Welcome to Cloud Attendance System</h2>
                <p>Your student account has been created.</p>
                <p><strong>Student ID:</strong> {username}</p>
                <p><strong>Password:</strong> <span style="background: #f0f0f0; padding: 5px;">{password}</span></p>
                <p><strong>Name:</strong> {name}</p>
                <p><strong>Department:</strong> {department}</p>
                <p><strong>Branch:</strong> {branch}</p>
                <p><strong>Batch:</strong> {batch}</p>
                <p><strong>Admission Year:</strong> {admission_year}</p>
                <hr>
                <p><small>Cloud Attendance System</small></p>
                </body>
                </html>
                """
                
                if email:
                    send_email(email, 'Your Attendance System Credentials', email_body)
            
            users_table.put_item(Item=user_item)
            
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'success': True, 
                    'message': f'{role.capitalize()} registered successfully',
                    'username': username,
                    'role': role
                })
            }
        
        # ============================================
        # 3. STUDENT SELF-REGISTER (From Login Page)
        # ============================================
        elif action == 'student_register':
            username = body.get('username')  # Student ID
            password = body.get('password')
            name = body.get('name')
            email = body.get('email')
            department = body.get('department', 'Other')
            branch = body.get('branch', 'General')
            batch = body.get('batch', '1st Year')
            admission_year = body.get('admission_year', str(datetime.now().year))
            
            if not username or not password or not name or not email:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({'error': 'Username, password, name and email required'})
                }
            
            # Check if user exists
            response = users_table.get_item(Key={'username': username})
            if 'Item' in response:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({'error': 'Username already exists'})
                }
            
            # Generate salt and hash password
            salt = generate_salt()
            password_hash = hash_password(password, salt)
            
            # Store user
            user_item = {
                'username': username,
                'password': password_hash,
                'salt': salt,
                'name': name,
                'role': 'student',
                'email': email,
                'created_at': datetime.now().isoformat()
            }
            users_table.put_item(Item=user_item)
            
            # Store student details
            student_item = {
                'student_id': username,
                'name': name,
                'email': email,
                'department': department,
                'branch': branch,
                'batch': batch,
                'admission_year': admission_year,
                'created_at': datetime.now().isoformat()
            }
            students_table.put_item(Item=student_item)
            
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'success': True, 
                    'message': 'Student registered successfully',
                    'username': username
                })
            }
        
        # ============================================
        # 4. VERIFY TOKEN ACTION
        # ============================================
        elif action == 'verify_token':
            token = body.get('token')
            if not token:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({'error': 'Token required'})
                }
            
            try:
                import jwt
                user_data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
                return {
                    'statusCode': 200,
                    'headers': headers,
                    'body': json.dumps({
                        'success': True,
                        'user': user_data
                    })
                }
            except:
                return {
                    'statusCode': 401,
                    'headers': headers,
                    'body': json.dumps({'error': 'Invalid token'})
                }
        
        else:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Invalid action'})
            }
            
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': headers if 'headers' in locals() else {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)})
        }