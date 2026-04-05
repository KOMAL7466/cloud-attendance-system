// API Configuration
const API_BASE_URL = 'http://localhost:5000'; // Change for production

// Store user session
let currentUser = null;

// Get auth token
function getAuthToken() {
    return localStorage.getItem('authToken');
}

// Login/Register Functions
document.addEventListener('DOMContentLoaded', function() {
    const token = getAuthToken();
    const user = localStorage.getItem('currentUser');
    
    if (token && user) {
        currentUser = JSON.parse(user);
        
        if (window.location.pathname.includes('dashboard.html')) {
            document.getElementById('userName').innerText = currentUser?.name || currentUser?.username || 'User';
        } else if (window.location.pathname.includes('admin.html')) {
            document.getElementById('adminName').innerText = currentUser?.name || currentUser?.username || 'Admin';
            loadAdminDashboard();
        }
    } else if (window.location.pathname.includes('dashboard.html') || window.location.pathname.includes('admin.html')) {
        // Redirect to login if not authenticated
        window.location.href = 'index.html';
    }
});

function showRegister() {
    document.querySelector('.login-card').style.display = 'none';
    document.querySelector('.register-card').style.display = 'block';
}

function showLogin() {
    document.querySelector('.register-card').style.display = 'none';
    document.querySelector('.login-card').style.display = 'block';
}

// Login handler
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

// Register handler
document.getElementById('registerForm')?.addEventListener('submit', async function(e) {
    e.preventDefault();
    const name = document.getElementById('regName').value;
    const username = document.getElementById('regUsername').value;
    const password = document.getElementById('regPassword').value;
    const role = document.getElementById('regRole').value;
    
    try {
        const response = await fetch(`${API_BASE_URL}/auth`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'register', username, password, name, role })
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert('Registration successful! Please login.');
            showLogin();
            // Clear form
            document.getElementById('regName').value = '';
            document.getElementById('regUsername').value = '';
            document.getElementById('regPassword').value = '';
        } else {
            alert('Registration failed: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
});

// Dashboard Functions
function showSection(section) {
    // Hide all sections
    const sections = ['mark', 'view', 'stats'];
    sections.forEach(s => {
        const el = document.getElementById(`${s}Section`);
        if (el) el.style.display = 'none';
    });
    
    // Show selected section
    const selectedSection = document.getElementById(`${section}Section`);
    if (selectedSection) selectedSection.style.display = 'block';
    
    // Load data if needed
    if (section === 'stats') {
        loadStatistics();
    }
}

// Mark Attendance
async function markAttendance() {
    const studentId = document.getElementById('studentId')?.value;
    const status = document.getElementById('attendanceStatus')?.value;
    const date = new Date().toISOString().split('T')[0];
    const token = getAuthToken();
    
    if (!studentId) {
        showMessage('markMessage', 'Please enter Student ID', 'error');
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
            body: JSON.stringify({ student_id: studentId, date, status: status.toLowerCase() })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showMessage('markMessage', data.message || 'Attendance marked successfully!', 'success');
            document.getElementById('studentId').value = '';
        } else {
            showMessage('markMessage', data.error || 'Failed to mark attendance', 'error');
        }
    } catch (error) {
        showMessage('markMessage', 'Error: ' + error.message, 'error');
    }
}

// View Attendance
async function viewAttendance() {
    const studentId = document.getElementById('viewStudentId')?.value;
    let url = `${API_BASE_URL}/get-attendance`;
    if (studentId) {
        url += `?student_id=${studentId}`;
    }
    const token = getAuthToken();
    
    if (!token) {
        showMessage('attendanceRecords', 'Please login again', 'error');
        setTimeout(() => logout(), 2000);
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
            <p><strong>Attendance Percentage:</strong> ${statistics.attendance_percentage || 0}%</p>
        </div>
        <div style="overflow-x: auto;">
        <table>
            <thead>
                <tr>
                    <th>Date</th>
                    <th>Status</th>
                    <th>Student Name</th>
                    <th>Student ID</th>
                    <th>Marked At</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    records.forEach(record => {
        const statusClass = record.status?.toLowerCase() || 'present';
        html += `<tr>
            <td>${record.date || '-'}</td>
            <td><span class="status-${statusClass}" style="padding: 4px 8px; border-radius: 4px; background: ${statusClass === 'present' ? '#c6f6d5' : statusClass === 'absent' ? '#fed7d7' : '#feebc8'}">${record.status || '-'}</span></td>
            <td>${record.student_name || '-'}</td>
            <td>${record.student_id || '-'}</td>
            <td>${record.marked_at ? new Date(record.marked_at).toLocaleString() : '-'}</td>
        </tr>`;
    });
    
    html += '</tbody></table></div>';
    container.innerHTML = html;
}

// Load Statistics
async function loadStatistics() {
    const token = getAuthToken();
    const statsGrid = document.getElementById('statsGrid');
    
    if (!statsGrid) return;
    
    if (!token) {
        statsGrid.innerHTML = '<div class="message error">Please login again</div>';
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/get-attendance`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await response.json();
        
        if (data.success && data.statistics) {
            statsGrid.innerHTML = `
                <div class="stat-card">
                    <h3>${data.statistics.total_days || 0}</h3>
                    <p>Total Days</p>
                </div>
                <div class="stat-card">
                    <h3>${data.statistics.present_days || 0}</h3>
                    <p>Present Days</p>
                </div>
                <div class="stat-card">
                    <h3>${data.statistics.absent_days || 0}</h3>
                    <p>Absent Days</p>
                </div>
                <div class="stat-card">
                    <h3>${data.statistics.attendance_percentage || 0}%</h3>
                    <p>Attendance Percentage</p>
                </div>
            `;
        } else {
            statsGrid.innerHTML = '<div class="message">No statistics available</div>';
        }
    } catch (error) {
        statsGrid.innerHTML = '<div class="message error">Error loading statistics</div>';
    }
}

// Admin Functions
function showAdminSection(section) {
    const sections = ['overview', 'students', 'reports', 'settings'];
    sections.forEach(s => {
        const el = document.getElementById(`${s}Section`);
        if (el) el.style.display = 'none';
    });
    
    const selectedSection = document.getElementById(`${section}Section`);
    if (selectedSection) selectedSection.style.display = 'block';
    
    if (section === 'students') {
        loadStudentList();
    }
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
            displayAdminOverview(data);
        } else {
            console.error('Failed to load dashboard:', data.error);
        }
    } catch (error) {
        console.error('Error loading dashboard:', error);
    }
}

function displayAdminOverview(data) {
    const statsCards = document.getElementById('statsCards');
    if (statsCards) {
        statsCards.innerHTML = `
            <div class="stat-card">
                <h3>${data.total_students || 0}</h3>
                <p>Total Students</p>
            </div>
            <div class="stat-card">
                <h3>${data.total_users || 0}</h3>
                <p>Total Users</p>
            </div>
            <div class="stat-card">
                <h3>${Object.keys(data.daily_attendance || {}).length}</h3>
                <p>Attendance Days</p>
            </div>
        `;
    }
    
    // Display student attendance percentages
    const studentStats = document.getElementById('studentStats');
    if (studentStats && data.student_attendance && data.student_attendance.length > 0) {
        let html = `<div style="overflow-x: auto;"><table><thead><tr>
            <th>Student ID</th><th>Name</th><th>Present</th><th>Total</th><th>Percentage</th>
        </tr></thead><tbody>`;
        
        data.student_attendance.forEach(student => {
            html += `<tr>
                <td>${student.student_id}</td>
                <td>${student.name}</td>
                <td>${student.present}</td>
                <td>${student.total}</td>
                <td><strong>${student.percentage}%</strong></td>
            </tr>`;
        });
        html += '</tbody></table></div>';
        studentStats.innerHTML = html;
    } else if (studentStats) {
        studentStats.innerHTML = '<div class="message">No attendance records found</div>';
    }
}

async function loadStudentList() {
    const token = getAuthToken();
    const studentListDiv = document.getElementById('studentList');
    
    if (!studentListDiv) return;
    
    try {
        // Note: You'll need to add a /get-students endpoint in backend
        // For now, using admin-dashboard data
        const response = await fetch(`${API_BASE_URL}/admin-dashboard`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await response.json();
        
        if (data.success && data.student_attendance) {
            let html = `<div style="overflow-x: auto;"><table><thead><tr>
                <th>Student ID</th><th>Name</th><th>Present Days</th><th>Total Days</th><th>Percentage</th>
            </tr></thead><tbody>`;
            
            data.student_attendance.forEach(student => {
                html += `<tr>
                    <td>${student.student_id}</td>
                    <td>${student.name}</td>
                    <td>${student.present}</td>
                    <td>${student.total}</td>
                    <td>${student.percentage}%</td>
                </tr>`;
            });
            html += '</tbody></table></div>';
            studentListDiv.innerHTML = html;
        } else {
            studentListDiv.innerHTML = '<div class="message">No students found</div>';
        }
    } catch (error) {
        studentListDiv.innerHTML = '<div class="message error">Error loading students</div>';
    }
}

async function addStudent() {
    const studentId = document.getElementById('newStudentId')?.value;
    const name = document.getElementById('newStudentName')?.value;
    const department = document.getElementById('newStudentDept')?.value;
    const token = getAuthToken();
    
    if (!studentId || !name) {
        alert('Please fill Student ID and Name');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/add-student`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ student_id: studentId, name, department: department || 'General' })
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert('Student added successfully!');
            document.getElementById('newStudentId').value = '';
            document.getElementById('newStudentName').value = '';
            document.getElementById('newStudentDept').value = '';
            loadStudentList();
        } else {
            alert('Failed to add student: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

async function generateReport() {
    const reportType = document.getElementById('reportType')?.value;
    const date = document.getElementById('reportDate')?.value || new Date().toISOString().split('T')[0];
    const token = getAuthToken();
    
    try {
        const response = await fetch(`${API_BASE_URL}/generate-report`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ type: reportType, date })
        });
        
        const data = await response.json();
        
        const reportResult = document.getElementById('reportResult');
        if (data.success && data.report_url) {
            reportResult.innerHTML = `
                <div class="message success">
                    ✅ Report generated successfully! 
                    <a href="${data.report_url}" target="_blank">📥 Download Report</a>
                    (${data.record_count || 0} records)
                </div>
            `;
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

function showMessage(elementId, message, type) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = `<div class="message ${type}" style="padding: 10px; border-radius: 5px; margin-top: 10px; background: ${type === 'success' ? '#c6f6d5' : '#fed7d7'}; color: ${type === 'success' ? '#22543d' : '#742a2a'}">${message}</div>`;
        setTimeout(() => {
            element.innerHTML = '';
        }, 5000);
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
                statusDiv.innerHTML = '<div class="message success">✅ Connection successful!</div>';
            })
            .catch(error => {
                statusDiv.innerHTML = '<div class="message error">❌ Connection failed: ' + error.message + '</div>';
            });
    }
}

// Set API endpoint in settings
function loadSettings() {
    const apiEndpointInput = document.getElementById('apiEndpoint');
    if (apiEndpointInput) {
        apiEndpointInput.value = API_BASE_URL;
    }
}

// Call loadSettings when settings section is shown
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('settingsSection')) {
        loadSettings();
    }
});