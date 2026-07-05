from flask import Flask, request, jsonify
from flask_cors import CORS
import jwt
import datetime
import hashlib
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
import string

app = Flask(__name__)

# ==================== ✅ FIXED CORS CONFIGURATION ====================
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "expose_headers": ["Content-Type", "Authorization"]
    }
})

# ==================== EMAIL CONFIGURATION ====================
EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'sender_email': 'varshadahiya708@gmail.com ',
    'sender_password': 'qzvn hdio cpto qmcn',  # Change this
    'admin_email': 'dahiyamohit764@gmail.com'
}

# In-memory storage
users = {}
students = {}
attendance_records = []
leave_applications = []

SECRET_KEY = "your-secret-key-here"

# ==================== EMAIL FUNCTION ====================
def send_email(to_email, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_CONFIG['sender_email']
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
        server.starttls()
        server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
        server.send_message(msg)
        server.quit()
        print(f"✅ Email sent to {to_email}")
        return True
    except Exception as e:
        print(f"❌ Email error: {e}")
        return False

# ==================== HEALTH CHECK ====================
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.datetime.now().isoformat()})

# ==================== AUTH ENDPOINT ====================
@app.route('/auth', methods=['POST', 'OPTIONS'])
def auth():
    if request.method == 'OPTIONS':
        return '', 200
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
                    'role': user['role'],
                    'username': username
                })
            else:
                return jsonify({'success': False, 'error': 'Invalid credentials'}), 401
        
        elif action == 'register':
            username = data.get('username')
            password = data.get('password')
            name = data.get('name')
            role = data.get('role', 'student')
            email = data.get('email', '')
            department = data.get('department', 'Other')
            branch = data.get('branch', 'General')
            batch = data.get('batch', '1st Year')
            admission_year = data.get('admission_year', str(datetime.datetime.now().year))
            
            if username in users:
                return jsonify({'success': False, 'error': 'Username already exists'}), 400
            
            users[username] = {
                'username': username,
                'password': hashlib.md5(password.encode()).hexdigest(),
                'name': name,
                'role': role,
                'email': email,
                'created_at': datetime.datetime.now().isoformat()
            }
            
            if role == 'student':
                students[username] = {
                    'student_id': username,
                    'name': name,
                    'email': email,
                    'department': department,
                    'branch': branch,
                    'batch': batch,
                    'admission_year': admission_year,
                    'created_at': datetime.datetime.now().isoformat()
                }
            
            return jsonify({'success': True, 'message': 'User registered successfully'})
        
        else:
            return jsonify({'success': False, 'error': 'Invalid action'}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== GENERATE STUDENT CREDENTIALS ====================
@app.route('/generate-student-credentials', methods=['POST', 'OPTIONS'])
def generate_student_credentials():
    if request.method == 'OPTIONS':
        return '', 200
    try:
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '')
        
        if not token:
            return jsonify({'success': False, 'error': 'No token provided'}), 401
        
        user_data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        username = user_data['username']
        
        if username not in users or users[username]['role'] != 'admin':
            return jsonify({'success': False, 'error': 'Admin access required'}), 403
        
        data = request.json
        student_id = data.get('student_id')
        name = data.get('name')
        email = data.get('email')
        department = data.get('department', 'Other')
        branch = data.get('branch', 'General')
        batch = data.get('batch', '1st Year')
        admission_year = data.get('admission_year', str(datetime.datetime.now().year))
        
        if not student_id or not email or not name:
            return jsonify({'success': False, 'error': 'student_id, name and email required'}), 400
        
        temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        
        if student_id in users:
            users[student_id]['password'] = hashlib.md5(temp_password.encode()).hexdigest()
            users[student_id]['name'] = name
            users[student_id]['email'] = email
            message = f'Credentials updated for {student_id}'
        else:
            users[student_id] = {
                'username': student_id,
                'password': hashlib.md5(temp_password.encode()).hexdigest(),
                'name': name,
                'role': 'student',
                'email': email,
                'created_at': datetime.datetime.now().isoformat()
            }
            message = f'Student {name} created'
        
        students[student_id] = {
            'student_id': student_id,
            'name': name,
            'email': email,
            'department': department,
            'branch': branch,
            'batch': batch,
            'admission_year': admission_year,
            'created_at': datetime.datetime.now().isoformat()
        }
        
        email_body = f"""
        <html>
        <body>
        <h2 style="color: #667eea;">🎓 Welcome to Cloud Attendance System</h2>
        <p><strong>Student ID:</strong> {student_id}</p>
        <p><strong>Password:</strong> <span style="background: #f0f0f0; padding: 5px;">{temp_password}</span></p>
        <p><strong>Login URL:</strong> <a href="https://cloud-attendance-system.vercel.app">Click Here</a></p>
        <hr>
        <p><small>Cloud Attendance System</small></p>
        </body>
        </html>
        """
        send_email(email, '🎓 Your Attendance System Credentials', email_body)
        
        return jsonify({
            'success': True,
            'message': f'{message} and credentials sent to {email}',
            'student': {'student_id': student_id, 'name': name, 'email': email}
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== MARK ATTENDANCE ====================
@app.route('/mark-attendance', methods=['POST', 'OPTIONS'])
def mark_attendance():
    if request.method == 'OPTIONS':
        return '', 200
    try:
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '')
        
        if not token:
            return jsonify({'success': False, 'error': 'No token provided'}), 401
        
        user_data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        
        data = request.json
        student_id = data.get('student_id')
        date = data.get('date', datetime.datetime.now().strftime('%Y-%m-%d'))
        status = data.get('status', 'absent').lower()
        leave_subject = data.get('leave_subject', '')
        leave_message = data.get('leave_message', '')
        marked_by = data.get('marked_by', user_data['username'])
        
        if not student_id:
            return jsonify({'success': False, 'error': 'student_id required'}), 400
        
        if student_id not in students:
            return jsonify({'success': False, 'error': 'Student not found'}), 404
        
        student = students[student_id]
        student_name = student.get('name', student_id)
        student_email = student.get('email', '')
        day_of_week = datetime.datetime.now().strftime('%A')
        
        if status not in ['present', 'leave']:
            status = 'absent'
        
        existing_index = -1
        for i, record in enumerate(attendance_records):
            if record['student_id'] == student_id and record['date'] == date:
                existing_index = i
                break
        
        attendance_entry = {
            'student_id': student_id,
            'student_name': student_name,
            'student_department': student.get('department', 'N/A'),
            'student_branch': student.get('branch', 'N/A'),
            'student_batch': student.get('batch', 'N/A'),
            'date': date,
            'status': status,
            'marked_at': datetime.datetime.now().isoformat(),
            'marked_by': marked_by,
            'day': day_of_week
        }
        
        if existing_index >= 0:
            attendance_records[existing_index] = attendance_entry
            message = f'Attendance updated to {status}'
        else:
            attendance_records.append(attendance_entry)
            message = f'Attendance marked as {status}'
        
        leave_applied = False
        if status == 'leave' and leave_subject:
            leave_applications.append({
                'student_id': student_id,
                'student_name': student_name,
                'student_email': student_email,
                'department': student.get('department', 'N/A'),
                'batch': student.get('batch', 'N/A'),
                'date': date,
                'subject': leave_subject,
                'message': leave_message,
                'status': 'pending',
                'applied_at': datetime.datetime.now().isoformat()
            })
            leave_applied = True
        
        # Send email to ADMIN
        email_body = f"""
        <html>
        <body>
        <h2 style="color: #667eea;">📋 Attendance Update</h2>
        <p><strong>Student:</strong> {student_name} ({student_id})</p>
        <p><strong>Department:</strong> {student.get('department', 'N/A')}</p>
        <p><strong>Branch:</strong> {student.get('branch', 'N/A')}</p>
        <p><strong>Batch:</strong> {student.get('batch', 'N/A')}</p>
        <p><strong>Date:</strong> {date}</p>
        <p><strong>Day:</strong> {day_of_week}</p>
        <p><strong>Status:</strong> <span style="color: {'green' if status == 'present' else 'orange' if status == 'leave' else 'red'};">{status.upper()}</span></p>
        <p><strong>Marked By:</strong> {marked_by}</p>
        <p><strong>Time:</strong> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        """
        if leave_applied:
            email_body += f"""
        <h3>📝 Leave Application</h3>
        <p><strong>Subject:</strong> {leave_subject}</p>
        <p><strong>Message:</strong> {leave_message}</p>
        <p><strong>Status:</strong> ⏳ Pending</p>
            """
        email_body += """
        <hr>
        <p><small>Cloud Attendance System</small></p>
        </body>
        </html>
        """
        send_email(EMAIL_CONFIG['admin_email'], f'📋 Attendance Update - {student_name}', email_body)
        
        return jsonify({
            'success': True,
            'message': message,
            'attendance': attendance_entry,
            'leave_applied': leave_applied
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== GET ATTENDANCE ====================
@app.route('/get-attendance', methods=['GET', 'OPTIONS'])
def get_attendance():
    if request.method == 'OPTIONS':
        return '', 200
    try:
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '')
        
        if not token:
            return jsonify({'success': False, 'error': 'No token provided'}), 401
        
        user_data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        
        student_id = request.args.get('student_id')
        department = request.args.get('department')
        branch = request.args.get('branch')
        batch = request.args.get('batch')
        status_filter = request.args.get('status')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        filtered_records = attendance_records.copy()
        
        if student_id:
            filtered_records = [r for r in filtered_records if r['student_id'] == student_id]
        if department:
            student_ids = [sid for sid, s in students.items() if s.get('department') == department]
            filtered_records = [r for r in filtered_records if r['student_id'] in student_ids]
        if branch:
            student_ids = [sid for sid, s in students.items() if s.get('branch') == branch]
            filtered_records = [r for r in filtered_records if r['student_id'] in student_ids]
        if batch:
            student_ids = [sid for sid, s in students.items() if s.get('batch') == batch]
            filtered_records = [r for r in filtered_records if r['student_id'] in student_ids]
        if status_filter:
            filtered_records = [r for r in filtered_records if r['status'].lower() == status_filter.lower()]
        if start_date:
            filtered_records = [r for r in filtered_records if r['date'] >= start_date]
        if end_date:
            filtered_records = [r for r in filtered_records if r['date'] <= end_date]
        
        total_days = len(filtered_records)
        present_days = len([r for r in filtered_records if r['status'].lower() == 'present'])
        absent_days = len([r for r in filtered_records if r['status'].lower() == 'absent'])
        leave_days = len([r for r in filtered_records if r['status'].lower() == 'leave'])
        attendance_percentage = round((present_days / total_days * 100), 2) if total_days > 0 else 0
        
        return jsonify({
            'success': True,
            'records': filtered_records,
            'statistics': {
                'total_days': total_days,
                'present_days': present_days,
                'absent_days': absent_days,
                'leave_days': leave_days,
                'attendance_percentage': attendance_percentage
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== ADMIN DASHBOARD ====================
@app.route('/admin-dashboard', methods=['GET', 'OPTIONS'])
def admin_dashboard():
    if request.method == 'OPTIONS':
        return '', 200
    try:
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '')
        
        if not token:
            return jsonify({'success': False, 'error': 'No token provided'}), 401
        
        user_data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        username = user_data['username']
        
        if username not in users or users[username]['role'] != 'admin':
            return jsonify({'success': False, 'error': 'Admin access required'}), 403
        
        total_users = len(users)
        total_students = len(students)
        total_present = len([r for r in attendance_records if r['status'].lower() == 'present'])
        total_leave = len([r for r in attendance_records if r['status'].lower() == 'leave'])
        total_absent = len([r for r in attendance_records if r['status'].lower() == 'absent'])
        
        return jsonify({
            'success': True,
            'overall_stats': {
                'total_users': total_users,
                'total_students': total_students,
                'total_present': total_present,
                'total_leave': total_leave,
                'total_absent': total_absent,
                'overall_attendance_percentage': round((total_present / (total_present + total_absent + total_leave) * 100), 2) if (total_present + total_absent + total_leave) > 0 else 0
            },
            'student_attendance': list(students.values()),
            'leave_applications': leave_applications,
            'last_updated': datetime.datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== ADD STUDENT ====================
@app.route('/add-student', methods=['POST', 'OPTIONS'])
def add_student():
    if request.method == 'OPTIONS':
        return '', 200
    try:
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '')
        
        if not token:
            return jsonify({'success': False, 'error': 'No token provided'}), 401
        
        user_data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        username = user_data['username']
        
        if username not in users or users[username]['role'] != 'admin':
            return jsonify({'success': False, 'error': 'Admin access required'}), 403
        
        data = request.json
        student_id = data.get('student_id')
        name = data.get('name')
        department = data.get('department', 'Other')
        branch = data.get('branch', 'General')
        batch = data.get('batch', '1st Year')
        admission_year = data.get('admission_year', str(datetime.datetime.now().year))
        
        if not student_id or not name:
            return jsonify({'success': False, 'error': 'student_id and name required'}), 400
        
        students[student_id] = {
            'student_id': student_id,
            'name': name,
            'department': department,
            'branch': branch,
            'batch': batch,
            'admission_year': admission_year,
            'created_at': datetime.datetime.now().isoformat()
        }
        
        return jsonify({'success': True, 'message': f'Student {name} added successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== GET STUDENTS ====================
@app.route('/get-students', methods=['GET', 'OPTIONS'])
def get_students():
    if request.method == 'OPTIONS':
        return '', 200
    try:
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '')
        
        if not token:
            return jsonify({'success': False, 'error': 'No token provided'}), 401
        
        jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        
        student_list = list(students.values())
        
        return jsonify({'success': True, 'students': student_list})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== GENERATE REPORT ====================
@app.route('/generate-report', methods=['POST', 'OPTIONS'])
def generate_report():
    if request.method == 'OPTIONS':
        return '', 200
    try:
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '')
        
        if not token:
            return jsonify({'success': False, 'error': 'No token provided'}), 401
        
        user_data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        
        data = request.json
        report_type = data.get('type', 'daily')
        date = data.get('date')
        department_filter = data.get('department')
        batch_filter = data.get('batch')
        
        filtered_records = attendance_records.copy()
        
        if report_type == 'daily' and date:
            filtered_records = [r for r in filtered_records if r['date'] == date]
        elif report_type == 'monthly' and date:
            month = date[:7]
            filtered_records = [r for r in filtered_records if r['date'].startswith(month)]
        
        if department_filter:
            student_ids = [sid for sid, s in students.items() if s.get('department') == department_filter]
            filtered_records = [r for r in filtered_records if r['student_id'] in student_ids]
        
        if batch_filter:
            student_ids = [sid for sid, s in students.items() if s.get('batch') == batch_filter]
            filtered_records = [r for r in filtered_records if r['student_id'] in student_ids]
        
        for record in filtered_records:
            student = students.get(record['student_id'], {})
            record['student_name'] = student.get('name', 'Unknown')
        
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Student ID', 'Student Name', 'Department', 'Branch', 'Batch', 'Date', 'Status', 'Marked At', 'Marked By'])
        
        for record in filtered_records:
            writer.writerow([
                record['student_id'],
                record.get('student_name', 'Unknown'),
                record.get('student_department', 'N/A'),
                record.get('student_branch', 'N/A'),
                record.get('student_batch', 'N/A'),
                record['date'],
                record['status'],
                record.get('marked_at', ''),
                record.get('marked_by', '')
            ])
        
        csv_data = output.getvalue()
        filename = f"attendance_report_{report_type}_{date}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
        
        return jsonify({
            'success': True,
            'csv_data': csv_data,
            'filename': filename,
            'record_count': len(filtered_records)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== DELETE STUDENT ====================
@app.route('/delete-student', methods=['DELETE', 'OPTIONS'])
def delete_student():
    if request.method == 'OPTIONS':
        return '', 200
    try:
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '')
        
        if not token:
            return jsonify({'success': False, 'error': 'No token provided'}), 401
        
        user_data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        username = user_data['username']
        
        if username not in users or users[username]['role'] != 'admin':
            return jsonify({'success': False, 'error': 'Admin access required'}), 403
        
        data = request.json
        student_id = data.get('student_id')
        
        if not student_id:
            return jsonify({'success': False, 'error': 'student_id required'}), 400
        
        if student_id in users:
            del users[student_id]
        if student_id in students:
            del students[student_id]
        
        global attendance_records, leave_applications
        attendance_records = [r for r in attendance_records if r['student_id'] != student_id]
        leave_applications = [l for l in leave_applications if l['student_id'] != student_id]
        
        return jsonify({'success': True, 'message': f'Student {student_id} deleted successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== DEMO DATA ====================
def create_demo_data():
    if 'admin' not in users:
        users['admin'] = {
            'username': 'admin',
            'password': hashlib.md5('admin123'.encode()).hexdigest(),
            'name': 'Administrator',
            'role': 'admin',
            'email': EMAIL_CONFIG['admin_email'],
            'created_at': datetime.datetime.now().isoformat()
        }
        print("✅ Admin user created: username='admin', password='admin123'")
    
    demo_students = [
        {'student_id': '24021541017', 'name': 'Mohit Dahiya', 'department': 'Science', 'branch': 'Computer Science', 'batch': '1st Year', 'admission_year': '2024', 'email': 'dahiyamohit764@gmail.com'},
        {'student_id': '24021541018', 'name': 'Priya Patel', 'department': 'Science', 'branch': 'Computer Science', 'batch': '1st Year', 'admission_year': '2024', 'email': 'priya@example.com'},
        {'student_id': '24021541019', 'name': 'Amit Kumar', 'department': 'Arts', 'branch': 'History', 'batch': '2nd Year', 'admission_year': '2023', 'email': 'amit@example.com'},
        {'student_id': '24021541020', 'name': 'Sneha Reddy', 'department': 'Commerce', 'branch': 'Accountancy', 'batch': 'Final Year', 'admission_year': '2021', 'email': 'sneha@example.com'},
    ]
    
    for student in demo_students:
        if student['student_id'] not in students:
            students[student['student_id']] = student
            print(f"✅ Demo student added: {student['name']} ({student['student_id']})")

# ==================== MAIN ====================
if __name__ == '__main__':
    create_demo_data()
    port = int(os.environ.get('PORT', 5000))
    print("=" * 50)
    print("🚀 Cloud Attendance System - Local Server")
    print("=" * 50)
    print(f"\n📧 Admin email: {EMAIL_CONFIG['admin_email']}")
    print(f"📧 Sender email: {EMAIL_CONFIG['sender_email']}")
    print(f"\n🔑 Test Credentials:")
    print("   Admin: username='admin', password='admin123'")
    print("\n" + "=" * 50)
    print(f"🔥 Server running on http://localhost:{port}")
    print("=" * 50)
    app.run(debug=False, host='0.0.0.0', port=port, threaded=True)