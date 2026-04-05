from flask import Flask, request, jsonify
from flask_cors import CORS
import jwt
import datetime
import hashlib
import uuid

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

SECRET_KEY = "your-secret-key-here-please-change-in-production"

# In-memory storage for local testing
users = {}  # Store users
students = {}  # Store students
attendance_records = []  # Store attendance records

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.datetime.now().isoformat()})

# Auth endpoint (login and register)
@app.route('/auth', methods=['POST'])
def auth():
    try:
        data = request.json
        action = data.get('action')
        
        if action == 'login':
            username = data.get('username')
            password = data.get('password')
            
            if username not in users:
                return jsonify({'success': False, 'error': 'Invalid credentials'}), 401
            
            user = users[username]
            password_hash = hashlib.md5(password.encode()).hexdigest()
            
            if user['password'] == password_hash:
                token = jwt.encode({
                    'username': username,
                    'role': user['role'],
                    'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
                }, SECRET_KEY, algorithm='HS256')
                
                return jsonify({
                    'success': True,
                    'token': token,
                    'name': user['name'],
                    'role': user['role']
                })
            else:
                return jsonify({'success': False, 'error': 'Invalid credentials'}), 401
        
        elif action == 'register':
            username = data.get('username')
            password = data.get('password')
            name = data.get('name')
            role = data.get('role', 'student')
            
            if username in users:
                return jsonify({'success': False, 'error': 'Username already exists'}), 400
            
            users[username] = {
                'username': username,
                'password': hashlib.md5(password.encode()).hexdigest(),
                'name': name,
                'role': role,
                'created_at': datetime.datetime.now().isoformat()
            }
            
            return jsonify({'success': True, 'message': 'User registered successfully'})
        
        else:
            return jsonify({'success': False, 'error': 'Invalid action'}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Mark attendance endpoint
@app.route('/mark-attendance', methods=['POST'])
def mark_attendance():
    try:
        # Verify token
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '')
        
        if not token:
            return jsonify({'success': False, 'error': 'No token provided'}), 401
        
        try:
            user_data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        except jwt.InvalidTokenError:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401
        
        data = request.json
        student_id = data.get('student_id')
        date = data.get('date')
        status = data.get('status', 'present')
        
        if not student_id:
            return jsonify({'success': False, 'error': 'student_id required'}), 400
        
        # Check if student exists (for local testing, auto-create if not exists)
        if student_id not in students:
            students[student_id] = {
                'student_id': student_id,
                'name': f'Student_{student_id}',
                'department': 'General'
            }
        
        # Check if attendance already marked for this student on this date
        existing_index = -1
        for i, record in enumerate(attendance_records):
            if record['student_id'] == student_id and record['date'] == date:
                existing_index = i
                break
        
        attendance_entry = {
            'student_id': student_id,
            'date': date,
            'status': status,
            'marked_at': datetime.datetime.now().isoformat(),
            'marked_by': user_data['username']
        }
        
        if existing_index >= 0:
            attendance_records[existing_index] = attendance_entry
            message = f'Attendance updated to {status} for {student_id} on {date}'
        else:
            attendance_records.append(attendance_entry)
            message = f'Attendance marked as {status} for {student_id} on {date}'
        
        return jsonify({
            'success': True,
            'message': message
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Get attendance endpoint
@app.route('/get-attendance', methods=['GET'])
def get_attendance():
    try:
        # Verify token
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '')
        
        if not token:
            return jsonify({'success': False, 'error': 'No token provided'}), 401
        
        try:
            user_data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        except jwt.InvalidTokenError:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401
        
        student_id = request.args.get('student_id')
        
        # Filter records
        filtered_records = attendance_records.copy()
        
        if student_id:
            filtered_records = [r for r in filtered_records if r['student_id'] == student_id]
        
        # Add student names
        for record in filtered_records:
            student = students.get(record['student_id'], {})
            record['student_name'] = student.get('name', 'Unknown')
        
        # Calculate statistics
        total_days = len(filtered_records)
        present_days = len([r for r in filtered_records if r['status'].lower() == 'present'])
        absent_days = len([r for r in filtered_records if r['status'].lower() == 'absent'])
        
        attendance_percentage = round((present_days / total_days * 100), 2) if total_days > 0 else 0
        
        return jsonify({
            'success': True,
            'records': filtered_records,
            'statistics': {
                'total_days': total_days,
                'present_days': present_days,
                'absent_days': absent_days,
                'attendance_percentage': attendance_percentage
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Admin dashboard endpoint
@app.route('/admin-dashboard', methods=['GET'])
def admin_dashboard():
    try:
        # Verify token
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '')
        
        if not token:
            return jsonify({'success': False, 'error': 'No token provided'}), 401
        
        try:
            user_data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        except jwt.InvalidTokenError:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401
        
        # Check admin role
        username = user_data['username']
        if username not in users or users[username]['role'] != 'admin':
            return jsonify({'success': False, 'error': 'Admin access required'}), 403
        
        # Calculate daily attendance
        daily_attendance = {}
        for record in attendance_records:
            date = record['date']
            if date not in daily_attendance:
                daily_attendance[date] = {'present': 0, 'absent': 0, 'total': 0}
            
            if record['status'].lower() == 'present':
                daily_attendance[date]['present'] += 1
            else:
                daily_attendance[date]['absent'] += 1
            daily_attendance[date]['total'] += 1
        
        # Calculate student-wise attendance
        student_attendance = {}
        for record in attendance_records:
            sid = record['student_id']
            if sid not in student_attendance:
                student_attendance[sid] = {'present': 0, 'total': 0}
            
            if record['status'].lower() == 'present':
                student_attendance[sid]['present'] += 1
            student_attendance[sid]['total'] += 1
        
        # Get student names
        student_list = []
        for sid, data in student_attendance.items():
            student = students.get(sid, {'name': 'Unknown'})
            percentage = (data['present'] / data['total'] * 100) if data['total'] > 0 else 0
            student_list.append({
                'student_id': sid,
                'name': student.get('name', 'Unknown'),
                'present': data['present'],
                'total': data['total'],
                'percentage': round(percentage, 2)
            })
        
        return jsonify({
            'success': True,
            'total_students': len(students),
            'total_users': len(users),
            'daily_attendance': daily_attendance,
            'student_attendance': student_list,
            'last_updated': datetime.datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Add student endpoint
@app.route('/add-student', methods=['POST'])
def add_student():
    try:
        # Verify token
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '')
        
        if not token:
            return jsonify({'success': False, 'error': 'No token provided'}), 401
        
        try:
            user_data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        except jwt.InvalidTokenError:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401
        
        # Check admin role
        username = user_data['username']
        if username not in users or users[username]['role'] != 'admin':
            return jsonify({'success': False, 'error': 'Admin access required'}), 403
        
        data = request.json
        student_id = data.get('student_id')
        name = data.get('name')
        department = data.get('department', 'General')
        
        if not student_id or not name:
            return jsonify({'success': False, 'error': 'student_id and name required'}), 400
        
        students[student_id] = {
            'student_id': student_id,
            'name': name,
            'department': department,
            'created_at': datetime.datetime.now().isoformat()
        }
        
        return jsonify({
            'success': True,
            'message': f'Student {name} added successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Get students endpoint
@app.route('/get-students', methods=['GET'])
def get_students():
    try:
        # Verify token
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '')
        
        if not token:
            return jsonify({'success': False, 'error': 'No token provided'}), 401
        
        try:
            jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        except jwt.InvalidTokenError:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401
        
        student_list = list(students.values())
        
        return jsonify({
            'success': True,
            'students': student_list
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Generate report endpoint
@app.route('/generate-report', methods=['POST'])
def generate_report():
    try:
        # Verify token
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '')
        
        if not token:
            return jsonify({'success': False, 'error': 'No token provided'}), 401
        
        try:
            user_data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        except jwt.InvalidTokenError:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401
        
        data = request.json
        report_type = data.get('type', 'daily')
        date = data.get('date')
        
        # Filter records by date
        filtered_records = attendance_records.copy()
        if date:
            filtered_records = [r for r in filtered_records if r['date'] == date]
        
        # Add student names
        for record in filtered_records:
            student = students.get(record['student_id'], {})
            record['student_name'] = student.get('name', 'Unknown')
        
        # In local mode, just return the data
        return jsonify({
            'success': True,
            'report_url': '#',  # In local, no actual URL
            'filename': f'report_{report_type}_{date}.csv',
            'record_count': len(filtered_records),
            'data': filtered_records  # Include data for local display
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Create some demo data for testing
def create_demo_data():
    # Create admin user
    if 'admin' not in users:
        users['admin'] = {
            'username': 'admin',
            'password': hashlib.md5('admin123'.encode()).hexdigest(),
            'name': 'Administrator',
            'role': 'admin',
            'created_at': datetime.datetime.now().isoformat()
        }
        print("✅ Admin user created: username='admin', password='admin123'")
    
    # Create some demo students
    demo_students = [
        {'student_id': '23021541001', 'name': 'Rahul Sharma', 'department': 'Computer Science'},
        {'student_id': '23021541002', 'name': 'Priya Patel', 'department': 'Computer Science'},
        {'student_id': '23021541003', 'name': 'Amit Kumar', 'department': 'Information Technology'},
    ]
    
    for student in demo_students:
        if student['student_id'] not in students:
            students[student['student_id']] = student
            print(f"✅ Demo student added: {student['name']} ({student['student_id']})")
    
    # Create some demo attendance records
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    
    demo_records = [
        {'student_id': '23021541001', 'date': today, 'status': 'present', 'marked_at': datetime.datetime.now().isoformat()},
        {'student_id': '23021541002', 'date': today, 'status': 'present', 'marked_at': datetime.datetime.now().isoformat()},
        {'student_id': '23021541003', 'date': today, 'status': 'absent', 'marked_at': datetime.datetime.now().isoformat()},
        {'student_id': '23021541001', 'date': yesterday, 'status': 'present', 'marked_at': (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat()},
        {'student_id': '23021541002', 'date': yesterday, 'status': 'absent', 'marked_at': (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat()},
    ]
    
    for record in demo_records:
        attendance_records.append(record)
    
    print(f"✅ Demo attendance records created")

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 Cloud Attendance System - Local Server")
    print("=" * 50)
    print("\n📋 Creating demo data...")
    create_demo_data()
    print("\n✨ Server is ready!")
    print("\n📍 Access URLs:")
    print("   Frontend: http://localhost:8000")
    print("   Backend API: http://localhost:5000")
    print("\n🔑 Test Credentials:")
    print("   Admin: username='admin', password='admin123'")
    print("   Student: Register a new account")
    print("\n📡 API Endpoints:")
    print("   POST   /auth")
    print("   POST   /mark-attendance")
    print("   GET    /get-attendance")
    print("   GET    /admin-dashboard")
    print("   POST   /add-student")
    print("   GET    /get-students")
    print("   POST   /generate-report")
    print("   GET    /health")
    print("\n" + "=" * 50)
    print("🔥 Server running on http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, host='localhost', port=5000)