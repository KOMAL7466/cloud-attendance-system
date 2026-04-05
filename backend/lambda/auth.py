import json
import boto3
import hashlib
import hmac
import base64
import os
import uuid  
import random
import string

USER_TABLE = os.environ.get('USER_TABLE', 'attendance_users')

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(USER_TABLE)

def verify_password(stored_password, provided_password, salt):
    """Verify password using HMAC"""
    new_hash = hmac.new(
        salt.encode('utf-8'),
        provided_password.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return new_hash == stored_password

def lambda_handler(event, context):
    try:
        # Add CORS headers
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
        
        if action == 'login':
            username = body.get('username')
            password = body.get('password')
            
            if not username or not password:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({'error': 'Username and password required'})
                }
            
            response = table.get_item(Key={'username': username})
            
            if 'Item' not in response:
                return {
                    'statusCode': 401,
                    'headers': headers,
                    'body': json.dumps({'error': 'Invalid credentials'})
                }
            
            user = response['Item']
            salt = user.get('salt', '')
            stored_password = user.get('password', '')
            
            if verify_password(stored_password, password, salt):
                session_token = str(uuid.uuid4())
                
                # Store session (optional - in production use DynamoDB)
                
                return {
                    'statusCode': 200,
                    'headers': headers,
                    'body': json.dumps({
                        'success': True,
                        'token': session_token,
                        'role': user.get('role', 'student'),
                        'name': user.get('name', ''),
                        'username': username
                    })
                }
            
            return {
                'statusCode': 401,
                'headers': headers,
                'body': json.dumps({'error': 'Invalid credentials'})
            }
            
        elif action == 'register':
            username = body.get('username')
            password = body.get('password')
            name = body.get('name')
            role = body.get('role', 'student')
            
            # Validation
            if not username or not password or not name:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({'error': 'Username, password, and name required'})
                }
            
            # Check if user exists
            response = table.get_item(Key={'username': username})
            if 'Item' in response:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({'error': 'Username already exists'})
                }
            
            # Generate salt and hash password
            salt = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
            
            password_hash = hmac.new(
                salt.encode('utf-8'),
                password.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # Store user
            table.put_item(Item={
                'username': username,
                'password': password_hash,
                'salt': salt,
                'name': name,
                'role': role,
                'created_at': str(datetime.now().isoformat())
            })
            
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'success': True, 
                    'message': 'User registered successfully'
                })
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

# Add datetime import
from datetime import datetime