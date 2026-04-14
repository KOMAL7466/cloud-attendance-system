from flask import Flask, request, jsonify
from flask_cors import CORS
import jwt
import datetime
import hashlib
import uuid
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import csv
from io import StringIO, BytesIO

app = Flask(__name__)
CORS(app)

SECRET_KEY = "your-secret-key-here-please-change-in-production"

EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'sender_email': 'dahiyamohit764@gmail.com',  # 🔴 CHANGE THIS - Email jo bhejega
    'sender_password': 'oard jtbc avyj rdjd', # 🔴 CHANGE THIS - Gmail App Password
    'admin_email': 'varshadahiya708 @gmail.com'        # ✅ This is correct - Admin email
}

# In-memory storage
users = {}
students = {}
attendance_records = []

# ==================== EMAIL FUNCTION ====================
def send_email(to_email, subject, body, attachment=None):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_CONFIG['sender_email']
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'html'))
        
        if attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment)
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename=attendance_report.pdf')
            msg.attach(part)
        
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

# ==================== MARK ATTENDANCE (FIXED) ====================
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
        
        # Check if student exists
        if student_id not in students:
            students[student_id] = {
                'student_id': student_id,
                'name': f'Student_{student_id}',
                'department': 'General'
            }
        
        # Check if attendance already marked
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
        
        # ========== SEND EMAIL TO ADMIN (FIXED - Inside try block) ==========
        if status.lower() == 'present':
            student_name = students.get(student_id, {}).get('name', student_id)
            email_body = f"""
            <html>
            <body>
            <h2 style="color: #667eea;">📋 Attendance Notification</h2>
            <p><strong>Student:</strong> {student_name} ({student_id})</p>
            <p><strong>Date:</strong> {date}</p>
            <p><strong>Status:</strong> <span style="color: green;">{status.upper()}</span></p>
            <p><strong>Marked By:</strong> {user_data['username']}</p>
            <p><strong>Time:</strong> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <hr>
            <p><small>Cloud Attendance System</small></p>
            </body>
            </html>
            """
            send_email(EMAIL_CONFIG['admin_email'], f'✅ Attendance Marked - {student_name}', email_body)
        
        return jsonify({'success': True, 'message': message})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== GET ATTENDANCE ====================
@app.route('/get-attendance', methods=['GET'])
def get_attendance():
    try:
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '')
        
        if not token:
            return jsonify({'success': False, 'error': 'No token provided'}), 401
        
        try:
            user_data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        except jwt.InvalidTokenError:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401
        
        student_id = request.args.get('student_id')
        
        filtered_records = attendance_records.copy()
        
        if student_id:
            filtered_records = [r for r in filtered_records if r['student_id'] == student_id]
        
        for record in filtered_records:
            student = students.get(record['student_id'], {})
            record['student_name'] = student.get('name', 'Unknown')
        
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

# ==================== ADMIN DASHBOARD ====================
@app.route('/admin-dashboard', methods=['GET'])
def admin_dashboard():
    try:
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '')
        
        if not token:
            return jsonify({'success': False, 'error': 'No token provided'}), 401
        
        try:
            user_data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        except jwt.InvalidTokenError:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401
        
        username = user_data['username']
        if username not in users or users[username]['role'] != 'admin':
            return jsonify({'success': False, 'error': 'Admin access required'}), 403
        
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
        
        student_attendance = {}
        for record in attendance_records:
            sid = record['student_id']
            if sid not in student_attendance:
                student_attendance[sid] = {'present': 0, 'total': 0}
            
            if record['status'].lower() == 'present':
                student_attendance[sid]['present'] += 1
            student_attendance[sid]['total'] += 1
        
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

# ==================== ADD STUDENT ====================
@app.route('/add-student', methods=['POST'])
def add_student():
    try:
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '')
        
        if not token:
            return jsonify({'success': False, 'error': 'No token provided'}), 401
        
        try:
            user_data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        except jwt.InvalidTokenError:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401
        
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

# ==================== GET STUDENTS ====================
@app.route('/get-students', methods=['GET'])
def get_students():
    try:
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

# ==================== GENERATE REPORT ====================
@app.route('/generate-report', methods=['POST'])
def generate_report():
    try:
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
        
        filtered_records = attendance_records.copy()
        if date:
            filtered_records = [r for r in filtered_records if r['date'] == date]
        
        for record in filtered_records:
            student = students.get(record['student_id'], {})
            record['student_name'] = student.get('name', 'Unknown')
        
        return jsonify({
            'success': True,
            'report_url': '#',
            'filename': f'report_{report_type}_{date}.csv',
            'record_count': len(filtered_records),
            'data': filtered_records
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== GENERATE MONTHLY REPORT (NEW) ====================
@app.route('/generate-monthly-report', methods=['POST'])
def generate_monthly_report():
    try:
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '')
        
        if not token:
            return jsonify({'success': False, 'error': 'No token provided'}), 401
        
        try:
            user_data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        except jwt.InvalidTokenError:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401
        
        username = user_data['username']
        if username not in users or users[username]['role'] != 'admin':
            return jsonify({'success': False, 'error': 'Admin access required'}), 403
        
        data = request.json
        month = data.get('month')
        year = data.get('year')
        
        if month and year:
            start_date = f"{year}-{month}-01"
            if month == '12':
                end_date = f"{int(year)+1}-01-01"
            else:
                end_date = f"{year}-{int(month)+1:02d}-01"
        else:
            now = datetime.datetime.now()
            start_date = now.replace(day=1).strftime('%Y-%m-%d')
            if now.month == 12:
                end_date = now.replace(year=now.year+1, month=1, day=1).strftime('%Y-%m-%d')
            else:
                end_date = now.replace(month=now.month+1, day=1).strftime('%Y-%m-%d')
        
        monthly_records = [r for r in attendance_records if start_date <= r['date'] < end_date]
        
        student_summary = {}
        for record in monthly_records:
            sid = record['student_id']
            if sid not in student_summary:
                student_summary[sid] = {
                    'name': students.get(sid, {}).get('name', sid),
                    'present': 0,
                    'absent': 0,
                    'total': 0
                }
            
            if record['status'].lower() == 'present':
                student_summary[sid]['present'] += 1
            else:
                student_summary[sid]['absent'] += 1
            student_summary[sid]['total'] += 1
        
        # Generate HTML Report
        html_report = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Attendance Report - {month}/{year}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                h1 {{ color: #667eea; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
                th {{ background-color: #667eea; color: white; }}
                .present {{ color: green; font-weight: bold; }}
                .absent {{ color: red; }}
                .summary {{ margin-top: 30px; padding: 20px; background: #f0f0f0; border-radius: 10px; }}
            </style>
        </head>
        <body>
            <h1>📊 Monthly Attendance Report</h1>
            <p><strong>Month:</strong> {month}/{year}</p>
            <p><strong>Generated on:</strong> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <table>
                <thead>
                    <tr>
                        <th>Student ID</th>
                        <th>Student Name</th>
                        <th>Present Days</th>
                        <th>Absent Days</th>
                        <th>Total Days</th>
                        <th>Attendance %</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        total_present = 0
        total_days = 0
        
        for sid, data in student_summary.items():
            percentage = (data['present'] / data['total'] * 100) if data['total'] > 0 else 0
            total_present += data['present']
            total_days += data['total']
            html_report += f"""
                <tr>
                    <td>{sid}</td>
                    <td>{data['name']}</td>
                    <td class="present">{data['present']}</td>
                    <td class="absent">{data['absent']}</td>
                    <td>{data['total']}</td>
                    <td>{percentage:.1f}%</td>
                </tr>
            """
        
        overall_percentage = (total_present / total_days * 100) if total_days > 0 else 0
        
        html_report += f"""
                </tbody>
            </table>
            <div class="summary">
                <h3>Summary</h3>
                <p><strong>Total Students:</strong> {len(student_summary)}</p>
                <p><strong>Total Present Days:</strong> {total_present}</p>
                <p><strong>Total Attendance Days:</strong> {total_days}</p>
                <p><strong>Overall Attendance:</strong> {overall_percentage:.1f}%</p>
            </div>
        </body>
        </html>
        """
        
        send_email(
            EMAIL_CONFIG['admin_email'],
            f'📊 Monthly Attendance Report - {month}/{year}',
            html_report
        )
        
        return jsonify({
            'success': True,
            'message': f'Monthly report sent to {EMAIL_CONFIG["admin_email"]}',
            'summary': {
                'total_students': len(student_summary),
                'total_present': total_present,
                'total_days': total_days,
                'attendance_percentage': round(overall_percentage, 2)
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== GENERATE STUDENT CREDENTIALS ====================
@app.route('/generate-student-credentials', methods=['POST'])
def generate_student_credentials():
    try:
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '')
        
        if not token:
            return jsonify({'success': False, 'error': 'No token provided'}), 401
        
        try:
            user_data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        except jwt.InvalidTokenError:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401
        
        username = user_data['username']
        if username not in users or users[username]['role'] != 'admin':
            return jsonify({'success': False, 'error': 'Admin access required'}), 403
        
        data = request.json
        student_id = data.get('student_id')
        student_email = data.get('email')
        
        if not student_id or not student_email:
            return jsonify({'success': False, 'error': 'student_id and email required'}), 400
        
        import random
        import string
        temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        
        if student_id not in users:
            users[student_id] = {
                'username': student_id,
                'password': hashlib.md5(temp_password.encode()).hexdigest(),
                'name': students.get(student_id, {}).get('name', student_id),
                'role': 'student',
                'email': student_email,
                'created_at': datetime.datetime.now().isoformat()
            }
            
            email_body = f"""
            <html>
            <body>
            <h2 style="color: #667eea;">🎓 Welcome to Cloud Attendance System</h2>
            <p>Your student account has been created.</p>
            <p><strong>Username:</strong> {student_id}</p>
            <p><strong>Password:</strong> <span style="background: #f0f0f0; padding: 5px;">{temp_password}</span></p>
            <p><strong>Login URL:</strong> <a href="https://your-app-url.com">https://your-app-url.com</a></p>
            <p>Please change your password after first login.</p>
            <hr>
            <p><small>Cloud Attendance System</small></p>
            </body>
            </html>
            """
            send_email(student_email, 'Your Attendance System Credentials', email_body)
            
            return jsonify({'success': True, 'message': f'Credentials sent to {student_email}'})
        else:
            return jsonify({'success': False, 'error': 'Student already has login credentials'}), 400
            
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
            'created_at': datetime.datetime.now().isoformat()
        }
        print("✅ Admin user created: username='admin', password='admin123'")
    
    demo_students = [
        {'student_id': '24021541017', 'name': 'Mohit Dahiya', 'department': 'Computer Science'},
        {'student_id': '24021541018', 'name': 'Priya Patel', 'department': 'Computer Science'},
        {'student_id': '24021541019', 'name': 'Amit Kumar', 'department': 'Information Technology'},
    ]
    
    for student in demo_students:
        if student['student_id'] not in students:
            students[student['student_id']] = student
            print(f"✅ Demo student added: {student['name']} ({student['student_id']})")
    
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    
    demo_records = [
        {'student_id': '24021541017', 'date': today, 'status': 'present', 'marked_at': datetime.datetime.now().isoformat()},
        {'student_id': '24021541018', 'date': today, 'status': 'present', 'marked_at': datetime.datetime.now().isoformat()},
        {'student_id': '24021541019', 'date': today, 'status': 'absent', 'marked_at': datetime.datetime.now().isoformat()},
    ]
    
    for record in demo_records:
        attendance_records.append(record)
    
    print("✅ Demo attendance records created")

# ==================== MAIN ====================
if __name__ == '__main__':
    create_demo_data()
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Attempting to start server on port {port}", flush=True)
    print(f"🔧 Binding to host 0.0.0.0", flush=True)
    print(f"📧 Admin email: {EMAIL_CONFIG['admin_email']}")
    print(f"📧 Sender email: {EMAIL_CONFIG['sender_email']}")
    app.run(debug=False, host='0.0.0.0', port=port, threaded=True)