// API Configuration
const API_BASE_URL = 'https://cloud-attendance-system-ab69.onrender.com'; // Change to live URL when deploying

// Store user session
let currentUser = null;
let currentStudentId = null;

// Get auth token
function getAuthToken() {
    return localStorage.getItem('authToken');
}

function getCurrentUser() {
    const user = localStorage.getItem('currentUser');
    return user ? JSON.parse(user) : null;
}

// ==================== INITIALIZATION ====================
document.addEventListener('DOMContentLoaded', function() {
    const token = getAuthToken();
    const user = getCurrentUser();
    
    if (token && user) {
        currentUser = user;
        currentStudentId = user.username;
        
        if (window.location.pathname.includes('dashboard.html')) {
            document.getElementById('userName').innerText = currentUser?.name || currentUser?.username || 'User';
            document.getElementById('userRole').innerText = currentUser?.role || 'Student';
            loadStudentProfile();
            loadTodayStatus();
        } else if (window.location.pathname.includes('admin.html')) {
            document.getElementById('adminName').innerText = currentUser?.name || currentUser?.username || 'Admin';
            loadAdminDashboard();
            loadStudentList();
        }
    } else if (window.location.pathname.includes('dashboard.html') || window.location.pathname.includes('admin.html')) {
        window.location.href = 'index.html';
    }
    
    if (document.getElementById('settingsSection')) {
        loadSettings();
    }
});

// ==================== LOGIN / REGISTER ====================
function showRegister() {
    document.querySelector('.login-card').style.display = 'none';
    document.querySelector('.register-card').style.display = 'block';
}

function showLogin() {
    document.querySelector('.register-card').style.display = 'none';
    document.querySelector('.login-card').style.display = 'block';
}

document.getElementById('loginForm')?.addEventListener('submit', async function(e) {
    e.preventDefault();
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    try {
        const response = await fetch(`${API_BASE_URL}/auth`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'login', username, password })
        });
        
        const data = await response.json();
        
        if (data.success) {
            localStorage.setItem('authToken', data.token);
            localStorage.setItem('currentUser', JSON.stringify({
                name: data.name,
                username: username,
                role: data.role,
                token: data.token
            }));
            currentUser = { name: data.name, username: username, role: data.role };
            
            if (data.role === 'admin') {
                window.location.href = 'admin.html';
            } else {
                window.location.href = 'dashboard.html';
            }
        } else {
            alert('Login failed: ' + (data.error || 'Invalid credentials'));
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
});

document.getElementById('registerForm')?.addEventListener('submit', async function(e) {
    e.preventDefault();
    const name = document.getElementById('regName').value;
    const email = document.getElementById('regEmail').value;
    const username = document.getElementById('regUsername').value;
    const password = document.getElementById('regPassword').value;
    const role = document.getElementById('regRole').value;
    const department = document.getElementById('regDepartment')?.value || 'Other';
    const branch = document.getElementById('regBranch')?.value || 'General';
    const batch = document.getElementById('regBatch')?.value || '1st Year';
    const admissionYear = document.getElementById('regAdmissionYear')?.value || '2024';
    
    try {
        const response = await fetch(`${API_BASE_URL}/auth`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                action: 'register', 
                username, 
                password, 
                name, 
                role,
                email,
                department,
                branch,
                batch,
                admission_year: admissionYear
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert('Registration successful! Please login.');
            showLogin();
            document.getElementById('regName').value = '';
            document.getElementById('regEmail').value = '';
            document.getElementById('regUsername').value = '';
            document.getElementById('regPassword').value = '';
            document.getElementById('regRole').value = '';
        } else {
            alert('Registration failed: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
});

document.getElementById('regRole')?.addEventListener('change', function() {
    const studentFields = document.getElementById('studentFields');
    if (this.value === 'student') {
        studentFields.style.display = 'block';
    } else {
        studentFields.style.display = 'none';
    }
});

function togglePassword() {
    const passwordInput = document.getElementById('password');
    passwordInput.type = passwordInput.type === 'password' ? 'text' : 'password';
}

function toggleRegisterPassword() {
    const passwordInput = document.getElementById('regPassword');
    passwordInput.type = passwordInput.type === 'password' ? 'text' : 'password';
}

// ==================== STUDENT DASHBOARD ====================
function showSection(section) {
    const sections = ['profile', 'mark', 'leave', 'view', 'stats'];
    sections.forEach(s => {
        const el = document.getElementById(`${s}Section`);
        if (el) el.style.display = 'none';
    });
    
    const selectedSection = document.getElementById(`${section}Section`);
    if (selectedSection) selectedSection.style.display = 'block';
    
    if (section === 'stats') {
        loadStatistics();
    }
    if (section === 'leave') {
        loadLeaveHistory();
    }
}

async function loadStudentProfile() {
    const token = getAuthToken();
    const username = currentStudentId;
    
    if (!token || !username) return;
    
    try {
        const response = await fetch(`${API_BASE_URL}/get-attendance?student_id=${username}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await response.json();
        const stats = data.statistics || {};
        
        document.getElementById('profileStudentId').textContent = username;
        document.getElementById('profileName').textContent = currentUser?.name || 'Student';
        document.getElementById('profileEmail').textContent = currentUser?.email || '-';
        document.getElementById('profileDepartment').textContent = '-';
        document.getElementById('profileBranch').textContent = '-';
        document.getElementById('profileBatch').textContent = '-';
        document.getElementById('profileAdmissionYear').textContent = '-';
        document.getElementById('profileTotalPresent').textContent = stats.present_days || 0;
        document.getElementById('profileTotalAbsent').textContent = stats.absent_days || 0;
        document.getElementById('profileTotalLeave').textContent = stats.leave_days || 0;
        document.getElementById('profilePercentage').textContent = (stats.attendance_percentage || 0) + '%';
    } catch (error) {
        console.error('Error loading profile:', error);
    }
}

async function loadTodayStatus() {
    const token = getAuthToken();
    const username = currentStudentId;
    
    if (!token || !username) return;
    
    try {
        const today = new Date().toISOString().split('T')[0];
        const response = await fetch(`${API_BASE_URL}/get-attendance?student_id=${username}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await response.json();
        const todayRecord = data.records?.find(r => r.date === today);
        const statusDiv = document.getElementById('todayStatus');
        
        if (todayRecord) {
            const status = todayRecord.status || 'absent';
            const statusMap = {
                'present': '✅ Present',
                'absent': '❌ Absent',
                'leave': '📝 Leave'
            };
            statusDiv.innerHTML = `
                <div class="status-badge status-${status}">${statusMap[status] || status}</div>
                <p style="margin-top: 10px; color: #666;">Marked at: ${todayRecord.marked_at ? new Date(todayRecord.marked_at).toLocaleTimeString() : '-'}</p>
            `;
        } else {
            statusDiv.innerHTML = `
                <div class="status-badge status-absent">⏳ Not Marked Yet</div>
                <p style="margin-top: 10px; color: #666;">Please mark your attendance for today.<br>If not marked, it will be auto-marked as <strong>ABSENT</strong>.</p>
            `;
        }
    } catch (error) {
        console.error('Error loading today status:', error);
    }
}

async function markAttendance(status) {
    const token = getAuthToken();
    const studentId = currentStudentId;
    const date = new Date().toISOString().split('T')[0];
    
    if (!studentId) {
        showMessage('markMessage', 'Student ID not found', 'error');
        return;
    }
    
    if (!token) {
        showMessage('markMessage', 'Please login again', 'error');
        setTimeout(() => logout(), 2000);
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/mark-attendance`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ 
                student_id: studentId, 
                date, 
                status: status.toLowerCase(),
                marked_by: 'student'
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            const statusMap = {
                'present': '✅ Present',
                'leave': '📝 Leave',
                'absent': '❌ Absent'
            };
            showMessage('markMessage', `✅ Attendance marked as ${statusMap[status] || status}`, 'success');
            loadTodayStatus();
            loadStatistics();
        } else {
            showMessage('markMessage', data.error || 'Failed to mark attendance', 'error');
        }
    } catch (error) {
        showMessage('markMessage', 'Error: ' + error.message, 'error');
    }
}

async function applyLeave() {
    const token = getAuthToken();
    const studentId = currentStudentId;
    const subject = document.getElementById('leaveSubject')?.value;
    const message = document.getElementById('leaveMessage')?.value;
    const date = document.getElementById('leaveDate')?.value || new Date().toISOString().split('T')[0];
    
    if (!subject || !message) {
        showMessage('leaveMessageResult', 'Please fill subject and message', 'error');
        return;
    }
    
    if (!token || !studentId) {
        showMessage('leaveMessageResult', 'Please login again', 'error');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/mark-attendance`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ 
                student_id: studentId, 
                date,
                status: 'leave',
                leave_subject: subject,
                leave_message: message,
                marked_by: 'student'
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showMessage('leaveMessageResult', '✅ Leave application submitted successfully!', 'success');
            document.getElementById('leaveSubject').value = '';
            document.getElementById('leaveMessage').value = '';
            loadLeaveHistory();
        } else {
            showMessage('leaveMessageResult', data.error || 'Failed to apply leave', 'error');
        }
    } catch (error) {
        showMessage('leaveMessageResult', 'Error: ' + error.message, 'error');
    }
}

async function loadLeaveHistory() {
    const token = getAuthToken();
    const studentId = currentStudentId;
    
    if (!token || !studentId) return;
    
    try {
        const response = await fetch(`${API_BASE_URL}/get-attendance?student_id=${studentId}&status=leave`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await response.json();
        const container = document.getElementById('leaveHistory');
        const records = data.records || [];
        
        if (records.length === 0) {
            container.innerHTML = '<p>No leave applications found.</p>';
            return;
        }
        
        let html = `<div style="overflow-x: auto;"><table><thead><tr>
            <th>Date</th><th>Subject</th><th>Message</th><th>Status</th><th>Applied At</th>
        </tr></thead><tbody>`;
        
        records.forEach(record => {
            html += `<tr>
                <td>${record.date || '-'}</td>
                <td>${record.leave_subject || '-'}</td>
                <td>${record.leave_message || '-'}</td>
                <td><span class="status-${record.status || 'pending'}">${record.status || 'Pending'}</span></td>
                <td>${record.marked_at ? new Date(record.marked_at).toLocaleString() : '-'}</td>
            </tr>`;
        });
        
        html += '</tbody></table></div>';
        container.innerHTML = html;
    } catch (error) {
        console.error('Error loading leave history:', error);
        document.getElementById('leaveHistory').innerHTML = '<p class="error">Error loading leave history</p>';
    }
}

async function viewAttendance() {
    const token = getAuthToken();
    const studentId = currentStudentId;
    const startDate = document.getElementById('viewStartDate')?.value;
    const endDate = document.getElementById('viewEndDate')?.value;
    const statusFilter = document.getElementById('viewStatus')?.value;
    
    let url = `${API_BASE_URL}/get-attendance?student_id=${studentId}`;
    if (startDate) url += `&start_date=${startDate}`;
    if (endDate) url += `&end_date=${endDate}`;
    if (statusFilter) url += `&status=${statusFilter}`;
    
    if (!token) {
        showMessage('attendanceRecords', 'Please login again', 'error');
        return;
    }
    
    try {
        const response = await fetch(url, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await response.json();
        
        if (data.success) {
            displayAttendanceRecords(data.records || [], data.statistics || {});
        } else {
            showMessage('attendanceRecords', data.error || 'Failed to fetch records', 'error');
        }
    } catch (error) {
        showMessage('attendanceRecords', 'Error: ' + error.message, 'error');
    }
}

function displayAttendanceRecords(records, statistics) {
    const container = document.getElementById('attendanceRecords');
    
    if (!records || records.length === 0) {
        container.innerHTML = '<div class="message">No attendance records found</div>';
        return;
    }
    
    let html = `
        <div class="stats-summary" style="background: #f7fafc; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
            <h4>📊 Statistics</h4>
            <p><strong>Total Days:</strong> ${statistics.total_days || 0}</p>
            <p><strong>Present:</strong> ${statistics.present_days || 0}</p>
            <p><strong>Absent:</strong> ${statistics.absent_days || 0}</p>
            <p><strong>Leave:</strong> ${statistics.leave_days || 0}</p>
            <p><strong>Attendance Percentage:</strong> ${statistics.attendance_percentage || 0}%</p>
        </div>
        <div style="overflow-x: auto;">
        <table>
            <thead>
                <tr>
                    <th>Student ID</th>
                    <th>Student Name</th>
                    <th>Department</th>
                    <th>Branch</th>
                    <th>Batch</th>
                    <th>Date</th>
                    <th>Day</th>
                    <th>Status</th>
                    <th>Marked At</th>
                    <th>Marked By</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    records.forEach(record => {
        const statusClass = record.status?.toLowerCase() || 'absent';
        const statusMap = {
            'present': '✅ Present',
            'absent': '❌ Absent',
            'leave': '📝 Leave'
        };
        html += `<tr>
            <td><strong>${record.student_id || '-'}</strong></td>
            <td>${record.student_name || '-'}</td>
            <td>${record.student_department || record.department || '-'}</td>
            <td>${record.student_branch || record.branch || '-'}</td>
            <td>${record.student_batch || record.batch || '-'}</td>
            <td>${record.date || '-'}</td>
            <td>${record.day || '-'}</td>
            <td><span class="status-${statusClass}">${statusMap[statusClass] || record.status}</span></td>
            <td>${record.marked_at ? new Date(record.marked_at).toLocaleString() : '-'}</td>
            <td>${record.marked_by || '-'}</td>
        </tr>`;
    });
    
    html += '</tbody></table></div>';
    container.innerHTML = html;
}

async function loadStatistics() {
    const token = getAuthToken();
    const studentId = currentStudentId;
    
    if (!token || !studentId) return;
    
    try {
        const response = await fetch(`${API_BASE_URL}/get-attendance?student_id=${studentId}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await response.json();
        
        if (data.success && data.statistics) {
            document.getElementById('statTotalDays').textContent = data.statistics.total_days || 0;
            document.getElementById('statPresent').textContent = data.statistics.present_days || 0;
            document.getElementById('statAbsent').textContent = data.statistics.absent_days || 0;
            document.getElementById('statLeave').textContent = data.statistics.leave_days || 0;
            document.getElementById('statPercentage').textContent = (data.statistics.attendance_percentage || 0) + '%';
        }
    } catch (error) {
        console.error('Error loading statistics:', error);
    }
}

// ==================== ADMIN FUNCTIONS ====================
function showAdminSection(section) {
    const sections = ['overview', 'students', 'credentials', 'attendance', 'reports', 'leave', 'settings'];
    sections.forEach(s => {
        const el = document.getElementById(`${s}Section`);
        if (el) el.style.display = 'none';
    });
    
    const selectedSection = document.getElementById(`${section}Section`);
    if (selectedSection) selectedSection.style.display = 'block';
    
    if (section === 'students') loadStudentList();
    if (section === 'leave') loadLeaveApplications();
    if (section === 'attendance') viewAdminAttendance();
}

async function loadAdminDashboard() {
    const token = getAuthToken();
    
    if (!token) {
        window.location.href = 'index.html';
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/admin-dashboard`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await response.json();
        
        if (data.success) {
            const stats = data.overall_stats || {};
            document.getElementById('totalStudents').textContent = stats.total_students || 0;
            document.getElementById('totalUsers').textContent = stats.total_users || 0;
            document.getElementById('totalPresent').textContent = stats.total_present || 0;
            document.getElementById('totalLeave').textContent = stats.total_leave || 0;
            document.getElementById('totalAbsent').textContent = stats.total_absent || 0;
            document.getElementById('attendancePercentage').textContent = (stats.overall_attendance_percentage || 0) + '%';
        } else {
            console.error('Failed to load dashboard:', data.error);
        }
    } catch (error) {
        console.error('Error loading dashboard:', error);
    }
}

async function loadStudentList() {
    const token = getAuthToken();
    const container = document.getElementById('studentList');
    
    if (!container) return;
    
    try {
        const response = await fetch(`${API_BASE_URL}/get-students`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await response.json();
        
        if (data.success && data.students) {
            let html = `<div style="overflow-x: auto;"><table><thead><tr>
                <th>Student ID</th><th>Name</th><th>Email</th><th>Department</th><th>Branch</th><th>Batch</th><th>Admission Year</th>
                <th>Action</th>
            </tr></thead><tbody>`;
            
            data.students.forEach(student => {
                html += `<tr>
                    <td>${student.student_id}</td>
                    <td>${student.name}</td>
                    <td>${student.email || '-'}</td>
                    <td>${student.department || '-'}</td>
                    <td>${student.branch || '-'}</td>
                    <td>${student.batch || '-'}</td>
                    <td>${student.admission_year || '-'}</td>
                    <td><button onclick="deleteStudent('${student.student_id}')" class="btn-danger" style="padding: 5px 12px; font-size: 12px; width: auto;">🗑️ Delete</button></td>
                </tr>`;
            });
            html += '</tbody></table></div>';
            container.innerHTML = html;
        } else {
            container.innerHTML = '<div class="message">No students found</div>';
        }
    } catch (error) {
        container.innerHTML = '<div class="message error">Error loading students</div>';
    }
}

async function deleteStudent(studentId) {
    if (!confirm(`Are you sure you want to delete student ${studentId}? This will also delete all attendance records.`)) {
        return;
    }
    
    const token = getAuthToken();
    
    try {
        const response = await fetch(`${API_BASE_URL}/delete-student`, {
            method: 'DELETE',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ student_id: studentId })
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert(`✅ ${data.message}`);
            loadStudentList();
            loadAdminDashboard();
        } else {
            alert(`❌ Failed: ${data.error}`);
        }
    } catch (error) {
        alert(`❌ Error: ${error.message}`);
    }
}

async function generateStudentCredentials() {
    const studentId = document.getElementById('credStudentId')?.value?.trim();
    const name = document.getElementById('credStudentName')?.value?.trim();
    const email = document.getElementById('credStudentEmail')?.value?.trim();
    const department = document.getElementById('credStudentDept')?.value;
    const branch = document.getElementById('credStudentBranch')?.value?.trim();
    const batch = document.getElementById('credStudentBatch')?.value;
    const admissionYear = document.getElementById('credStudentYear')?.value;
    const token = getAuthToken();
    
    if (!studentId || !name || !email) {
        showMessage('credentialResult', '❌ Please fill Student ID, Name and Email', 'error');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/generate-student-credentials`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ 
                student_id: studentId,
                name: name,
                email: email,
                department: department || 'Other',
                branch: branch || 'General',
                batch: batch || '1st Year',
                admission_year: admissionYear || '2024'
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showMessage('credentialResult', `✅ ${data.message}`, 'success');
            document.getElementById('credStudentId').value = '';
            document.getElementById('credStudentName').value = '';
            document.getElementById('credStudentEmail').value = '';
            document.getElementById('credStudentBranch').value = '';
            document.getElementById('credStudentYear').value = '';
            loadStudentList();
        } else {
            showMessage('credentialResult', `❌ ${data.error || 'Failed to generate credentials'}`, 'error');
        }
    } catch (error) {
        showMessage('credentialResult', 'Error: ' + error.message, 'error');
    }
}

async function viewAdminAttendance() {
    const token = getAuthToken();
    const studentId = document.getElementById('attendanceStudentId')?.value;
    const department = document.getElementById('attendanceDepartment')?.value;
    const batch = document.getElementById('attendanceBatch')?.value;
    const status = document.getElementById('attendanceStatus')?.value;
    const startDate = document.getElementById('attendanceStartDate')?.value;
    const endDate = document.getElementById('attendanceEndDate')?.value;
    
    let url = `${API_BASE_URL}/get-attendance`;
    let params = [];
    if (studentId) params.push(`student_id=${studentId}`);
    if (department) params.push(`department=${department}`);
    if (batch) params.push(`batch=${batch}`);
    if (status) params.push(`status=${status}`);
    if (startDate) params.push(`start_date=${startDate}`);
    if (endDate) params.push(`end_date=${endDate}`);
    if (params.length > 0) url += '?' + params.join('&');
    
    try {
        const response = await fetch(url, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await response.json();
        
        if (data.success) {
            displayAttendanceRecords(data.records || [], data.statistics || {});
        } else {
            showMessage('attendanceRecords', data.error || 'Failed to fetch records', 'error');
        }
    } catch (error) {
        showMessage('attendanceRecords', 'Error: ' + error.message, 'error');
    }
}

async function loadLeaveApplications() {
    const token = getAuthToken();
    const container = document.getElementById('leaveApplications');
    
    try {
        const response = await fetch(`${API_BASE_URL}/admin-dashboard`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await response.json();
        
        if (data.success && data.leave_applications) {
            const leaves = data.leave_applications;
            if (leaves.length === 0) {
                container.innerHTML = '<p>No leave applications found.</p>';
                return;
            }
            
            let html = `<div style="overflow-x: auto;"><table><thead><tr>
                <th>Student</th><th>Email</th><th>Department</th><th>Batch</th><th>Date</th><th>Subject</th><th>Message</th><th>Status</th>
            </tr></thead><tbody>`;
            
            leaves.forEach(leave => {
                const statusMap = {
                    'pending': '⏳ Pending',
                    'approved': '✅ Approved',
                    'rejected': '❌ Rejected'
                };
                html += `<tr>
                    <td>${leave.student_name}</td>
                    <td>${leave.student_email || '-'}</td>
                    <td>${leave.department || '-'}</td>
                    <td>${leave.batch || '-'}</td>
                    <td>${leave.date}</td>
                    <td>${leave.subject}</td>
                    <td>${leave.message || '-'}</td>
                    <td><span class="status-${leave.status}">${statusMap[leave.status] || leave.status}</span></td>
                </tr>`;
            });
            
            html += '</tbody></table></div>';
            container.innerHTML = html;
        }
    } catch (error) {
        container.innerHTML = '<p class="error">Error loading leave applications</p>';
    }
}

async function generateReport() {
    const reportType = document.getElementById('reportType')?.value;
    const date = document.getElementById('reportDate')?.value || new Date().toISOString().split('T')[0];
    const department = document.getElementById('reportDepartment')?.value;
    const batch = document.getElementById('reportBatch')?.value;
    const token = getAuthToken();
    
    try {
        const response = await fetch(`${API_BASE_URL}/generate-report`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ 
                type: reportType, 
                date,
                department: department || undefined,
                batch: batch || undefined
            })
        });
        
        const data = await response.json();
        
        const reportResult = document.getElementById('reportResult');
        if (data.success && data.csv_data) {
            const blob = new Blob([data.csv_data], { type: 'text/csv' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = data.filename || `attendance_report_${reportType}.csv`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            reportResult.innerHTML = `<div class="message success">✅ Report downloaded! (${data.record_count || 0} records)</div>`;
        } else {
            reportResult.innerHTML = `<div class="message error">❌ ${data.error || 'Failed to generate report'}</div>`;
        }
    } catch (error) {
        const reportResult = document.getElementById('reportResult');
        if (reportResult) {
            reportResult.innerHTML = `<div class="message error">❌ Error: ${error.message}</div>`;
        }
    }
}

// ==================== UTILITY FUNCTIONS ====================
function showMessage(elementId, message, type) {
    const element = document.getElementById(elementId);
    if (element) {
        const bgColor = type === 'success' ? '#c6f6d5' : type === 'error' ? '#fed7d7' : '#feebc8';
        const textColor = type === 'success' ? '#22543d' : type === 'error' ? '#742a2a' : '#744210';
        element.innerHTML = `<div class="message ${type}" style="padding: 12px; border-radius: 8px; margin-top: 10px; background: ${bgColor}; color: ${textColor};">${message}</div>`;
        setTimeout(() => { element.innerHTML = ''; }, 8000);
    }
}

function logout() {
    localStorage.removeItem('authToken');
    localStorage.removeItem('currentUser');
    window.location.href = 'index.html';
}

function testConnection() {
    const statusDiv = document.getElementById('connectionStatus');
    if (statusDiv) {
        statusDiv.innerHTML = '<div class="message">Testing connection...</div>';
        fetch(`${API_BASE_URL}/health`)
            .then(response => response.json())
            .then(data => {
                statusDiv.innerHTML = '<div class="message success">✅ Connection successful! Backend is live.</div>';
            })
            .catch(error => {
                statusDiv.innerHTML = `<div class="message error">❌ Connection failed: ${error.message}</div>`;
            });
    }
}

function loadSettings() {
    const apiEndpointInput = document.getElementById('apiEndpoint');
    if (apiEndpointInput) {
        apiEndpointInput.value = API_BASE_URL;
    }
}