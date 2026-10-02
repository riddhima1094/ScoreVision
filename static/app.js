const API_BASE = 'http://127.0.0.1:5000/api';

// DOM Elements
const authView = document.getElementById('auth-view');
const studentDashboard = document.getElementById('student-dashboard');
const adminDashboard = document.getElementById('admin-dashboard');
const logoutBtn = document.getElementById('logout-btn');
const navUserInfo = document.getElementById('nav-user-info');

// UI State
function showView(view) {
    authView.classList.add('hidden');
    studentDashboard.classList.add('hidden');
    adminDashboard.classList.add('hidden');
    logoutBtn.classList.add('hidden');
    navUserInfo.textContent = '';

    const user = JSON.parse(localStorage.getItem('user'));
    if (user) {
        navUserInfo.textContent = `${user.name} (${user.role.toUpperCase()})`;
    }

    if (view === 'auth') authView.classList.remove('hidden');
    if (view === 'student') {
        studentDashboard.classList.remove('hidden');
        logoutBtn.classList.remove('hidden');
    }
    if (view === 'admin') {
        adminDashboard.classList.remove('hidden');
        logoutBtn.classList.remove('hidden');
    }
}

// Sub-navigation Logic
function switchSubView(role, target) {
    const views = role === 's' ? ['dashboard', 'lectures', 'tests'] : ['dashboard', 'directory', 'lectures', 'tests'];
    views.forEach(v => {
        const navItem = document.getElementById(`nav-${role}-${v}`);
        if(navItem) navItem.classList.remove('active');
        const viewItem = document.getElementById(`${role}-view-${v}`);
        if(viewItem) viewItem.classList.add('hidden');
    });
    const targetNav = document.getElementById(`nav-${role}-${target}`);
    if (targetNav) targetNav.classList.add('active');
    const targetView = document.getElementById(`${role}-view-${target}`);
    if (targetView) targetView.classList.remove('hidden');

    if (role === 'a' && target === 'tests') {
        loadAdminTests();
    }
}

['student'].forEach(role => {
    ['dashboard', 'lectures', 'tests'].forEach(view => {
        const btn = document.getElementById(`nav-s-${view}`);
        if(btn) btn.addEventListener('click', () => switchSubView('s', view));
    });
});
['admin'].forEach(role => {
    ['dashboard', 'directory', 'lectures', 'tests'].forEach(view => {
        const btn = document.getElementById(`nav-a-${view}`);
        if(btn) btn.addEventListener('click', () => switchSubView('a', view));
    });
});

// Toast Notifications
function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

// Authentication
async function apiCall(endpoint, options = {}) {
    const token = localStorage.getItem('token');
    const headers = {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` })
    };

    try {
        const response = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || data.message || 'Something went wrong');
        return data;
    } catch (err) {
        showToast(err.message, 'error');
        if (err.message.includes('token') || err.message.includes('Forbidden') || err.message.includes('expired')) logout();
        throw err;
    }
}

function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    showView('auth');
}

document.getElementById('logout-btn').addEventListener('click', logout);

// Auth Tabs
document.getElementById('tab-login').addEventListener('click', (e) => {
    e.target.classList.add('active');
    document.getElementById('tab-register').classList.remove('active');
    document.getElementById('login-form').classList.remove('hidden');
    document.getElementById('register-form').classList.add('hidden');
});
document.getElementById('tab-register').addEventListener('click', (e) => {
    e.target.classList.add('active');
    document.getElementById('tab-login').classList.remove('active');
    document.getElementById('register-form').classList.remove('hidden');
    document.getElementById('login-form').classList.add('hidden');
});

// Auth Submits
document.getElementById('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;
    try {
        const data = await apiCall('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) });
        localStorage.setItem('token', data.access_token);
        localStorage.setItem('user', JSON.stringify(data.user));
        showToast('Login successful!');
        initDashboard();
    } catch (e) {}
});

document.getElementById('register-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
        name: document.getElementById('reg-name').value,
        email: document.getElementById('reg-email').value,
        password: document.getElementById('reg-password').value,
        role: document.getElementById('reg-role').value
    };
    try {
        await apiCall('/auth/register', { method: 'POST', body: JSON.stringify(payload) });
        showToast('Registration successful! Please login.');
        document.getElementById('tab-login').click();
    } catch (e) {}
});

// Init Dashboards
async function initDashboard() {
    const user = JSON.parse(localStorage.getItem('user'));
    if (!user) return showView('auth');

    if (user.role === 'student') {
        showView('student');
        switchSubView('s', 'dashboard');
        loadStudentData();
        loadLectures('s-lectures-list');
        loadStudentTests();
    } else {
    showView('admin');
    switchSubView('a', 'dashboard');

    loadAdminData();
    loadAdminDirectory();
    loadLectures('a-lectures-list');
    loadAdminTests();
}
}

// ---------------- STUDENT LOGIC ----------------
async function loadStudentData() {
    try {
        // Fetch academic data
        const acadRes = await apiCall('/prediction/academic');
        const acadContainer = document.getElementById('s-readonly-data');
        if (acadRes.data && acadRes.data.length > 0) {
            const data = acadRes.data[0];
            acadContainer.innerHTML = `
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                    <div><strong>Attendance:</strong> ${data.attendance_percentage}%</div>
                    <div><strong>Study Hours:</strong> ${data.study_hours}h</div>
                    <div><strong>Previous Exam:</strong> ${data.previous_exam_score}%</div>
                    <div><strong>Assignment Marks:</strong> ${data.assignment_marks}%</div>
                    <div><strong>Internal Assessment:</strong> ${data.internal_assessment_marks}%</div>
                    <div><strong>Participation:</strong> ${data.class_participation}%</div>
                    <div><strong>Sleep Hours:</strong> ${data.sleep_hours}h</div>
                    <div><strong>Extracurricular:</strong> <span style="text-transform:capitalize;">${data.extracurricular_involvement}</span></div>
                </div>
                <p style="margin-top: 1rem; font-size: 0.85rem;">Note: This data is managed by Faculty.</p>
            `;
        } else {
            acadContainer.innerHTML = '<p>No academic data has been uploaded by the faculty yet.</p>';
        }

        // Fetch prediction history
        const data = await apiCall('/prediction/history');
        const historyList = document.getElementById('history-list');
        const history = data.data;

        if (history.length === 0) {
            historyList.innerHTML = '<p style="color: #64748b; text-align: center; padding: 1rem;">No prediction history available.</p>';
            document.getElementById('pred-score').textContent = '--';
            document.getElementById('pred-category').style.display = 'none';
            return;
        }

        historyList.innerHTML = history.map(item => `
            <div class="list-item">
                <div>
                    <div style="font-weight: 600;">Score: ${item.predicted_score}</div>
                    <div style="font-size: 0.75rem; color: #64748b;">${new Date(item.date).toLocaleDateString()}</div>
                </div>
                <div style="display: flex; gap: 0.5rem; align-items: center;">
                    <span class="badge ${item.category.toLowerCase().replace(/\s+/g, '-')}">${item.category}</span>
                    <button class="btn-danger" style="width: auto; padding: 0.25rem 0.6rem; font-size: 0.75rem;" onclick="deletePrediction(${item.id})">Delete</button>
                </div>
            </div>
        `).join('');

        const latest = history[0];
        document.getElementById('pred-score').textContent = latest.predicted_score;
        const catBadge = document.getElementById('pred-category');
        catBadge.textContent = latest.category;
        catBadge.className = `badge ${latest.category.toLowerCase().replace(/\s+/g, '-')}`;
        catBadge.style.display = 'inline-block';
    } catch (e) {}
}

async function deletePrediction(id) {
    if (!confirm("Are you sure you want to delete this prediction from history?")) return;
    try {
        await apiCall(`/prediction/history/${id}`, { method: 'DELETE' });
        showToast('Prediction deleted from history');
        loadStudentData();
    } catch (e) {}
}
// ---------------- TEST LOGIC ----------------

let currentTestId = null;
let testTimerInterval = null;
let qCount = 0;


// ================= STUDENT TESTS =================

async function loadStudentTests() {
    try {
        const res = await apiCall('/cms/tests');
        const list = document.getElementById('s-tests-list');

        if (!list) return;

        if (!res.data || res.data.length === 0) {
            list.innerHTML = '<p>No tests available.</p>';
            return;
        }

        // Get student's previous submissions
        let submissions = [];

        try {
            const subRes = await apiCall('/cms/my-test-submissions');
            submissions = subRes.data || [];
        } catch (e) {
            submissions = [];
        }

        const attemptedTestIds = new Set(
            submissions.map(s => Number(s.test_id))
        );

        list.innerHTML = res.data.map(test => {
            const attempted = attemptedTestIds.has(Number(test.id));

            return `
                <div class="list-item">
                    <div>
                        <h4>${test.title}</h4>

                        <p style="font-size:0.8rem;color:#64748b;">
                            ${test.description || ''}
                        </p>

                        ${
                            test.duration_minutes
                                ? `<span class="badge info">
                                    ${test.duration_minutes} min
                                   </span>`
                                : ''
                        }
                    </div>

                    <div>
                        ${
                            attempted
                            ? `
                                <span class="badge good">
                                    Already Attempted
                                </span>
                            `
                            : `
                                <button
                                    style="width:auto;"
                                    onclick="takeTest(${test.id})">
                                    Take Test
                                </button>
                            `
                        }
                    </div>
                </div>
            `;
        }).join('');

    } catch (e) {
        const list = document.getElementById('s-tests-list');

        if (list) {
            list.innerHTML = `
                <p style="color:#ef4444;">
                    Unable to load tests.
                </p>
            `;
        }
    }
}


// ================= TAKE TEST =================

async function takeTest(id) {

    try {

        const res = await apiCall(`/cms/tests/${id}`);
        const test = res.data;

        currentTestId = id;

        document
            .getElementById('s-test-list-view')
            .classList.add('hidden');

        document
            .getElementById('s-take-test-view')
            .classList.remove('hidden');

        document
            .getElementById('take-test-title')
            .textContent = test.title;


        const qContainer =
            document.getElementById('take-test-questions');


        qContainer.innerHTML = test.questions.map((q, index) => {

            return `
                <div style="margin-bottom:1.5rem;">

                    <p style="font-weight:600;">
                        Q${index + 1}: ${q.question_text}
                    </p>

                    <div style="
                        display:flex;
                        flex-direction:column;
                        gap:0.5rem;
                    ">

                        <label>
                            <input
                                type="radio"
                                name="q_${q.id}"
                                value="A"
                                required>
                            A) ${q.options.A}
                        </label>

                        <label>
                            <input
                                type="radio"
                                name="q_${q.id}"
                                value="B">
                            B) ${q.options.B}
                        </label>

                        <label>
                            <input
                                type="radio"
                                name="q_${q.id}"
                                value="C">
                            C) ${q.options.C}
                        </label>

                        <label>
                            <input
                                type="radio"
                                name="q_${q.id}"
                                value="D">
                            D) ${q.options.D}
                        </label>

                    </div>

                </div>
            `;

        }).join('');


        // TIMER

        if (testTimerInterval) {
            clearInterval(testTimerInterval);
        }

        if (test.duration_minutes) {

            const timerContainer =
                document.getElementById('test-timer-container');

            const timerEl =
                document.getElementById('test-timer');

            timerContainer.style.display = 'block';

            let timeRemaining =
                Number(test.duration_minutes) * 60;

            timerEl.textContent =
                `${Math.floor(timeRemaining / 60)}:${String(
                    timeRemaining % 60
                ).padStart(2, '0')}`;


            testTimerInterval = setInterval(() => {

                timeRemaining--;

                if (timeRemaining <= 0) {

                    clearInterval(testTimerInterval);

                    timerEl.textContent = '0:00';

                    showToast(
                        'Time is up! Auto-submitting test.',
                        'info'
                    );

                    document
                        .getElementById('take-test-form')
                        .dispatchEvent(
                            new Event('submit', {
                                bubbles: true,
                                cancelable: true
                            })
                        );

                } else {

                    timerEl.textContent =
                        `${Math.floor(timeRemaining / 60)}:${String(
                            timeRemaining % 60
                        ).padStart(2, '0')}`;

                }

            }, 1000);

        } else {

            document
                .getElementById('test-timer-container')
                .style.display = 'none';

        }

    } catch (e) {
        console.error(e);
    }
}


// ================= BACK BUTTON =================

document
    .getElementById('btn-back-tests')
    ?.addEventListener('click', () => {

        if (testTimerInterval) {
            clearInterval(testTimerInterval);
        }

        document
            .getElementById('s-test-list-view')
            .classList.remove('hidden');

        document
            .getElementById('s-take-test-view')
            .classList.add('hidden');

        loadStudentTests();
    });


// ================= SUBMIT TEST =================

document
    .getElementById('take-test-form')
    ?.addEventListener('submit', async (e) => {

        e.preventDefault();

        if (!currentTestId) {
            showToast('No test selected.', 'error');
            return;
        }

        const formData = new FormData(e.target);

        const answers = {};

        for (const [key, value] of formData.entries()) {

            if (key.startsWith('q_')) {

                const questionId =
                    key.replace('q_', '');

                answers[questionId] = value;
            }
        }


        try {

            if (testTimerInterval) {
                clearInterval(testTimerInterval);
            }

            const res = await apiCall(
                `/cms/tests/${currentTestId}/submit`,
                {
                    method: 'POST',
                    body: JSON.stringify({
                        answers: answers
                    })
                }
            );


            showToast(
                `Test submitted! You scored ${res.data.score}/${res.data.total_questions}`
            );


            e.target.reset();


            document
                .getElementById('s-test-list-view')
                .classList.remove('hidden');

            document
                .getElementById('s-take-test-view')
                .classList.add('hidden');


            currentTestId = null;

            loadStudentTests();


        } catch (e) {
            console.error(e);
        }

    });


// ================= ADMIN TESTS =================

async function loadAdminTests() {
    try {
        const res = await apiCall('/cms/tests');
        const list = document.getElementById('a-tests-list');

        if (!list) return;

        if (!res.data || res.data.length === 0) {
            list.innerHTML = '<p>No tests created yet.</p>';
            return;
        }

        list.innerHTML = res.data.map(test => `
            <div class="list-item" style="display:block; margin-bottom:1rem;">

                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <h4>${test.title}</h4>

                        <p style="font-size:0.8rem; color:#64748b;">
                            ${test.description || 'No description'}
                        </p>

                        <span class="badge info">
                            ${test.duration_minutes ? test.duration_minutes + ' min' : 'No limit'}
                        </span>
                    </div>

                    <button
                        class="btn-danger"
                        style="width:auto;"
                        onclick="deleteTest(${test.id})">
                        Delete Test
                    </button>
                </div>

                <div style="margin-top:1rem;">
                    <strong>Questions:</strong>

                    ${
                        test.questions && test.questions.length
                        ? test.questions.map((q, index) => `
                            <div style="
                                margin-top:0.8rem;
                                padding:0.8rem;
                                background:#f8fafc;
                                border-radius:8px;
                            ">
                                <p>
                                    <strong>Q${index + 1}:</strong>
                                    ${q.question_text}
                                </p>

                                <p>A) ${q.options.A}</p>
                                <p>B) ${q.options.B}</p>
                                <p>C) ${q.options.C}</p>
                                <p>D) ${q.options.D}</p>

                                <p style="color:#16a34a;">
                                    Correct Answer:
                                    <strong>${q.correct_option}</strong>
                                </p>
                            </div>
                        `).join('')
                        : '<p style="color:#64748b;">No questions found.</p>'
                    }

                </div>

            </div>
        `).join('');

    } catch (error) {
        console.error('Error loading admin tests:', error);
    }
}

// ================= DELETE TEST =================

async function deleteTest(testId) {
    if (!confirm('Are you sure you want to delete this test?')) {
        return;
    }

    try {
        await apiCall(`/cms/tests/${testId}`, {
            method: 'DELETE'
        });

        showToast('Test deleted successfully!');

        loadAdminTests();
        loadStudentTests();

    } catch (error) {
        console.error(error);
    }
}

// ================= CREATE TEST =================

document
    .getElementById('btn-add-q')
    ?.addEventListener('click', () => {

        qCount++;

        const html = `

            <div
                class="glass-panel"
                style="
                    margin-bottom:1rem;
                    padding:1rem;
                "
                id="q-block-${qCount}"
            >

                <div class="form-group">

                    <label>
                        Question ${qCount}
                    </label>

                    <input
                        type="text"
                        name="q_text_${qCount}"
                        required>

                </div>


                <div style="
                    display:grid;
                    grid-template-columns:1fr 1fr;
                    gap:0.5rem;
                ">

                    <input
                        type="text"
                        name="q_a_${qCount}"
                        placeholder="Option A"
                        required>

                    <input
                        type="text"
                        name="q_b_${qCount}"
                        placeholder="Option B"
                        required>

                    <input
                        type="text"
                        name="q_c_${qCount}"
                        placeholder="Option C"
                        required>

                    <input
                        type="text"
                        name="q_d_${qCount}"
                        placeholder="Option D"
                        required>

                </div>


                <div
                    class="form-group"
                    style="margin-top:0.5rem;"
                >

                    <label>
                        Correct Option
                    </label>

                    <select
                        name="q_correct_${qCount}"
                    >

                        <option value="A">A</option>
                        <option value="B">B</option>
                        <option value="C">C</option>
                        <option value="D">D</option>

                    </select>

                </div>

            </div>
        `;


        document
            .getElementById('q-list')
            .insertAdjacentHTML(
                'beforeend',
                html
            );

    });


// ================= CREATE TEST SUBMIT =================

document
    .getElementById('create-test-form')
    ?.addEventListener('submit', async (e) => {

        e.preventDefault();


        if (qCount === 0) {

            showToast(
                'Add at least 1 question',
                'error'
            );

            return;
        }


        const formData =
            new FormData(e.target);


        const questions = [];


        for (let i = 1; i <= qCount; i++) {

            questions.push({

                question_text:
                    formData.get(`q_text_${i}`),

                options: {

                    A: formData.get(`q_a_${i}`),
                    B: formData.get(`q_b_${i}`),
                    C: formData.get(`q_c_${i}`),
                    D: formData.get(`q_d_${i}`)

                },

                correct_option:
                    formData.get(
                        `q_correct_${i}`
                    )

            });

        }


        const payload = {

            title:
                document.getElementById('t-title').value,

            description:
                document.getElementById('t-desc').value,

            duration_minutes:
                document.getElementById('t-duration').value
                || null,

            questions:
                questions

        };


        try {

            await apiCall(
                '/cms/tests',
                {
                    method: 'POST',
                    body: JSON.stringify(payload)
                }
            );


            showToast(
                'Test created successfully!'
            );


            e.target.reset();

            document
                .getElementById('q-list')
                .innerHTML = '';

            qCount = 0;


            loadAdminTests();

            loadStudentTests();


        } catch (e) {

            console.error(e);

        }

    });

// Shared CMS Logic (Lectures)
async function loadLectures(containerId) {
    try {
        const res = await apiCall('/cms/lectures');
        const list = document.getElementById(containerId);

        if (res.data.length === 0) {
            list.innerHTML = '<p>No lectures available.</p>';
            return;
        }

        const user = JSON.parse(localStorage.getItem('user'));
        const isFaculty = user && (user.role === 'faculty' || user.role === 'admin');

        list.innerHTML = res.data.map(l => `
            <div class="list-item">
                <div>
                    <h4>${l.title}</h4>
                    <p style="font-size:0.8rem; color:gray;">
                        ${l.description || ''}
                    </p>
                </div>

                <div style="display:flex; gap:0.5rem; align-items:center;">
                    <a href="${l.link}" target="_blank"
                       class="badge info"
                       style="text-decoration:none;">
                        Open Link
                    </a>

                    ${isFaculty ? `
                        <button
                            class="btn-danger"
                            style="width:auto; padding:0.5rem 0.8rem;"
                            onclick="deleteLecture(${l.id})">
                            Delete
                        </button>
                    ` : ''}
                </div>
            </div>
        `).join('');

    } catch(e) {}
}
async function deleteLecture(id) {
    const confirmed = confirm('Are you sure you want to delete this lecture?');

    if (!confirmed) return;

    try {
        await apiCall(`/cms/lectures/${id}`, {
            method: 'DELETE'
        });

        showToast('Lecture deleted successfully!');

        loadLectures('a-lectures-list');
        loadLectures('s-lectures-list');

    } catch (e) {}
}
// ---------------- ADMIN LOGIC ----------------
async function loadAdminData() {

    try {

        const res = await apiCall('/dashboard');

        const data = res.data;

        document.getElementById('ad-students').textContent =
            data.total_students;

        document.getElementById('ad-preds').textContent =
            data.total_predictions_made;

        const passPercent = data.pass_rate || 0;

        document.getElementById('ad-pass').textContent =
            `${passPercent}%`;

    } catch (e) {

        console.error('Admin dashboard error:', e);

    }
}

// Admin Directory Logic
let adminStudents = [];
async function loadAdminDirectory() {
    try {
        const res = await apiCall('/cms/students');
        adminStudents = res.data;
        const list = document.getElementById('a-students-list');
        
        if(adminStudents.length === 0) {
            list.innerHTML = '<p>No students found.</p>';
            return;
        }

        list.innerHTML = adminStudents.map(s => `
            <div class="list-item">
                <div style="cursor: pointer; flex: 1;" onclick="openEditStudent(${s.id})">
                    <h4><span style="color:var(--primary)">ID: ${s.formatted_id}</span> | ${s.name}</h4>
                    <p style="font-size:0.8rem; color:gray;">${s.email}</p>
                </div>
                <div style="display: flex; gap: 0.5rem; align-items: center;">
                    <span class="badge ${s.latest_record ? 'good' : 'poor'}">
                        ${s.latest_record ? 'Data Uploaded' : 'Missing Data'}
                    </span>
                    <button class="btn-secondary" style="width: auto; padding: 0.4rem 0.8rem; font-size: 0.85rem;" onclick="openEditStudent(${s.id})">
                        Edit
                    </button>
                    <button class="btn-danger" style="width: auto; padding: 0.4rem 0.8rem; font-size: 0.85rem;" onclick="deleteStudent(${s.id}, '${s.name.replace(/'/g, "\\'")}')">
                        Delete
                    </button>
                </div>
            </div>
        `).join('');
    } catch(e) {}
}

function openEditStudent(id) {
    const student = adminStudents.find(s => s.id === id);
    if (!student) return;

    document.getElementById('a-dir-list-view').classList.add('hidden');
    document.getElementById('a-dir-edit-view').classList.remove('hidden');
    
    document.getElementById('edit-student-name').textContent = `${student.formatted_id} - ${student.name}`;
    document.getElementById('edit-s-id').value = student.id;

    const record = student.latest_record || {};
    document.getElementById('e-attendance').value = record.attendance_percentage || 0;
    document.getElementById('e-study').value = record.study_hours || 0;
    document.getElementById('e-prev').value = record.previous_exam_score || 0;
    document.getElementById('e-assignment').value = record.assignment_marks || 0;
    document.getElementById('e-internal').value = record.internal_assessment_marks || 0;
    document.getElementById('e-participation').value = record.class_participation || 0;
    document.getElementById('e-sleep').value = record.sleep_hours || 0;
    document.getElementById('e-extra').value = record.extracurricular_involvement || 'none';
    loadStudentTestScores(student.id);

    const clearBtn = document.getElementById('btn-clear-academic');
    if (clearBtn) clearBtn.onclick = () => clearStudentAcademic(student.id);

    const deleteBtn = document.getElementById('btn-delete-student');
    if (deleteBtn) deleteBtn.onclick = () => deleteStudent(student.id, student.name);
}

async function deleteStudent(id, name) {
    if (!confirm(`Are you sure you want to permanently delete student '${name}' and all their records?`)) return;
    try {
        await apiCall(`/cms/student/${id}`, { method: 'DELETE' });
        showToast(`Student '${name}' deleted successfully`);
        loadAdminDirectory();
        loadAdminData();
        if (!document.getElementById('a-dir-edit-view').classList.contains('hidden')) {
            document.getElementById('btn-back-dir').click();
        }
    } catch (e) {}
}

async function clearStudentAcademic(id) {
    if (!confirm("Are you sure you want to clear this student's academic records and predictions?")) return;
    try {
        await apiCall(`/cms/student/${id}/academic`, { method: 'DELETE' });
        showToast('Academic records cleared');
        loadAdminDirectory();
        loadAdminData();
        document.getElementById('btn-back-dir').click();
    } catch (e) {}
}

document.getElementById('btn-back-dir').addEventListener('click', () => {
    document.getElementById('a-dir-list-view').classList.remove('hidden');
    document.getElementById('a-dir-edit-view').classList.add('hidden');
});

document.getElementById('edit-academic-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const sId = document.getElementById('edit-s-id').value;
    const payload = {
        attendance_percentage: parseFloat(document.getElementById('e-attendance').value),
        study_hours: parseFloat(document.getElementById('e-study').value),
        previous_exam_score: parseFloat(document.getElementById('e-prev').value),
        assignment_marks: parseFloat(document.getElementById('e-assignment').value),
        internal_assessment_marks: parseFloat(document.getElementById('e-internal').value),
        class_participation: parseFloat(document.getElementById('e-participation').value),
        sleep_hours: parseFloat(document.getElementById('e-sleep').value),
        extracurricular_involvement: document.getElementById('e-extra').value
    };

    try {
        await apiCall(`/cms/student/${sId}/academic`, { method: 'POST', body: JSON.stringify(payload) });
        showToast('Data uploaded and prediction updated for student!');
        loadAdminDirectory();
        document.getElementById('btn-back-dir').click();
    } catch (e) {}
});
async function loadStudentTestScores(studentId) {

    const container = document.getElementById('student-test-scores');

    if (!container) return;

    container.innerHTML = '<p>Loading test scores...</p>';

    try {

        const res = await apiCall(
            `/cms/student/${studentId}/test-submissions`
        );

        const submissions = res.data;

        if (!submissions || submissions.length === 0) {

            container.innerHTML = `
                <p style="color:#64748b;">
                    This student has not attempted any tests yet.
                </p>
            `;

            return;
        }

        container.innerHTML = submissions.map(sub => {

            const percentage = sub.percentage;

            let badgeClass = 'poor';

            if (percentage >= 70) {
                badgeClass = 'good';
            } else if (percentage >= 50) {
                badgeClass = 'average';
            }

            return `
                <div class="list-item">

                    <div>

                        <h4>
                            ${sub.test_title}
                        </h4>

                        <p style="font-size:0.85rem; color:#64748b;">

                            Score:
                            <strong>
                                ${sub.score}/${sub.total_questions}
                            </strong>

                            &nbsp; | &nbsp;

                            ${percentage}%

                        </p>

                        <p style="font-size:0.75rem; color:#94a3b8;">

                            Submitted:
                            ${sub.submitted_at
                                ? new Date(sub.submitted_at).toLocaleString()
                                : 'N/A'
                            }

                        </p>
                        <p style="font-size:0.75rem; color:#94a3b8;">
                             Submission ID: ${sub.id}
                        </p>

                    </div>

                    <div style="text-align:right;">

                        <span class="badge ${badgeClass}">
                            ${percentage}%
                        </span>

                        ${
                            sub.is_faculty_overridden
                            ? `
                                <div style="
                                    font-size:0.7rem;
                                    color:#2563eb;
                                    margin-top:0.4rem;
                                ">
                                    Faculty Override
                                </div>
                            `
                            : ''
                        }

                    </div>

                </div>
            `;

        }).join('');

    } catch (error) {

        container.innerHTML = `
            <p style="color:#ef4444;">
                Unable to load test scores.
            </p>
        `;

    }
}

// Add Lecture
document.getElementById('add-lecture-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
        title: document.getElementById('lec-title').value,
        description: document.getElementById('lec-desc').value,
        link: document.getElementById('lec-link').value
    };
    try {
        await apiCall('/cms/lectures', { method: 'POST', body: JSON.stringify(payload) });
        showToast('Lecture posted!');
        e.target.reset();
        loadLectures('a-lectures-list');
    } catch(e) {}
});

// Override Score
document.getElementById('override-score-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const sid = document.getElementById('ov-student').value;
    const subid = document.getElementById('ov-submission').value;
    const score = document.getElementById('ov-score').value;
    try {
        await apiCall(`/cms/student/${sid}/test/${subid}`, { method: 'PUT', body: JSON.stringify({ score }) });
        showToast('Score updated successfully!');
        e.target.reset();
    } catch(e) {}
});

// Create Test (Dynamic Questions Builder)
let qCounter = 0;
document.getElementById('btn-add-q').addEventListener('click', () => {
    qCounter++;
    const currentQId = qCounter;
    const html = `
        <div class="glass-panel q-block" style="margin-bottom: 1rem; padding: 1rem; border: 1px solid #cbd5e1;" id="q-block-${currentQId}">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
                <label style="font-weight:600; margin:0;">Question</label>
                <button type="button" class="btn-danger" style="width:auto; padding:0.25rem 0.6rem; font-size:0.75rem;" onclick="removeQuestionBlock(${currentQId})">✕ Remove</button>
            </div>
            <div class="form-group">
                <input type="text" class="q-text" placeholder="Enter question text" required>
            </div>
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:0.5rem;">
                <input type="text" class="q-opt-a" placeholder="Option A" required>
                <input type="text" class="q-opt-b" placeholder="Option B" required>
                <input type="text" class="q-opt-c" placeholder="Option C" required>
                <input type="text" class="q-opt-d" placeholder="Option D" required>
            </div>
            <div class="form-group" style="margin-top:0.5rem;">
                <label>Correct Option</label>
                <select class="q-correct">
                    <option value="A">A</option><option value="B">B</option>
                    <option value="C">C</option><option value="D">D</option>
                </select>
            </div>
        </div>
    `;
    document.getElementById('q-list').insertAdjacentHTML('beforeend', html);
});

window.removeQuestionBlock = function(id) {
    const el = document.getElementById(`q-block-${id}`);
    if (el) el.remove();
};

document.getElementById('create-test-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const blocks = document.querySelectorAll('.q-block');
    if (blocks.length === 0) return showToast('Add at least 1 question', 'error');

    const questions = [];
    blocks.forEach(block => {
        questions.push({
            question_text: block.querySelector('.q-text').value,
            options: {
                A: block.querySelector('.q-opt-a').value,
                B: block.querySelector('.q-opt-b').value,
                C: block.querySelector('.q-opt-c').value,
                D: block.querySelector('.q-opt-d').value
            },
            correct_option: block.querySelector('.q-correct').value
        });
    });

    const payload = {
        title: document.getElementById('t-title').value,
        description: document.getElementById('t-desc').value,
        duration_minutes: document.getElementById('t-duration').value || null,
        questions: questions
    };

    try {
    await apiCall('/cms/tests', {
        method: 'POST',
        body: JSON.stringify(payload)
    });

    showToast('Test created successfully!');

    e.target.reset();
    document.getElementById('q-list').innerHTML = '';
    qCount = 0;
    loadAdminTests();
    loadStudentTests();

    } catch(e) {}
});

// Admin Tests Management Logic
// ---------------- ADMIN TEST MANAGEMENT ----------------

async function loadAdminTests() {
    try {
        const res = await apiCall('/cms/tests');
        const list = document.getElementById('a-tests-list');

        if (!list) return;

        if (!res.data || res.data.length === 0) {
            list.innerHTML = '<p>No tests available.</p>';
            return;
        }

        list.innerHTML = res.data.map(t => `
            <div class="list-item">
                <div>
                    <h4>${t.title}</h4>

                    <p style="font-size:0.8rem; color:gray;">
                        ${t.description || 'No description'}
                    </p>

                    <p style="font-size:0.75rem; color:#64748b;">
                        Questions: ${t.questions_count}
                        ${t.duration_minutes
                            ? ` | Duration: ${t.duration_minutes} min`
                            : ''}
                    </p>
                </div>

                <button
                    class="btn-danger"
                    style="width:auto; padding:0.5rem 0.8rem;"
                    onclick="deleteTest(${t.id})">
                    Delete
                </button>
            </div>
        `).join('');

    } catch (e) {
        console.error('Failed to load tests:', e);
    }
}


async function deleteTest(id) {

    const confirmed = confirm(
        'Are you sure you want to delete this test? All questions and submissions will also be deleted.'
    );

    if (!confirmed) return;

    try {

        await apiCall(`/cms/tests/${id}`, {
            method: 'DELETE'
        });

        showToast('Test deleted successfully!');

        // Faculty/Admin test list refresh
        loadAdminTests();

        // Student test list refresh
        loadStudentTests();

    } catch (e) {
        console.error('Delete test error:', e);
    }
}

// Boot
if (localStorage.getItem('token')) initDashboard(); else showView('auth');

