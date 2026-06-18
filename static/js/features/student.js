// static/js/features/student.js
// Students and Interns registry, installments, certificate generation handlers

let studentInstallmentRows = [];
let currentSelectedStudentName = '';
let currentStudentDetails = null;
let generatedPdfUrl = null;

// ---------- STUDENTS & INTERNS VIEW ----------
async function loadStudentData() {
    document.getElementById('pageTitle').textContent = 'Student / Intern Module';
    // Load ongoing students from Bitrix24 API
    try {
        const res = await apiFetch('/api/student/bitrix-active/');
        if (res.ok) {
            const data = await res.json();
            const studList = data.results || [];
            const tbody = document.getElementById('studentTableBody');
            
            if (tbody) {
                if (studList.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="9" style="text-align:center; padding:30px; color:#64748b;">No ongoing students found.</td></tr>';
                    return;
                }
                
                tbody.innerHTML = studList.map(s => `
                    <tr>
                        <td>-</td>
                        <td>${s.name || '-'}</td>
                        <td>${s.email || '-'}</td>
                        <td>Student</td>
                        <td>${s.start_date || '-'}</td>
                        <td>${s.completion_date || '-'}</td>
                        <td>Rs. ${s.total_fees || '0'}</td>
                        <td><span style="font-weight:bold; color:#eab308; font-size:8.5pt;">ONGOING</span></td>
                        <td style="white-space: nowrap;">
                            <button class="btn" style="font-size:8pt; padding:4px 8px;" onclick="openCertTabWithBitrixStudent('${s.id}', '${s.name.replace(/'/g, "\\'")}', '${s.course_id || ''}', '${s.institute || ''}', '${s.start_date || ''}', '${s.completion_date || ''}')">Generate Cert</button>
                        </td>
                    </tr>
                `).join('');
            }
        } else {
            const tbody = document.getElementById('studentTableBody');
            if (tbody) {
                tbody.innerHTML = '<tr><td colspan="9" style="text-align:center; padding:30px; color:#ef4444;">Failed to fetch ongoing students from Bitrix24.</td></tr>';
            }
        }
    } catch (e) {
        console.error('Error loading students:', e);
        const tbody = document.getElementById('studentTableBody');
        if (tbody) {
            tbody.innerHTML = '<tr><td colspan="9" style="text-align:center; padding:30px; color:#ef4444;">Error connecting to Bitrix24 API.</td></tr>';
        }
    }
}

function openStudentModal() {
    const modal = document.getElementById('studentModal');
    if (modal) {
        modal.style.display = 'flex';
        loadDepartmentsSelect('studDept');
        loadCoursesSelect('studEnrolledCourse');
        // reset installments rows
        studentInstallmentRows = [];
        const container = document.getElementById('installmentsWrapper');
        if (container) container.innerHTML = '';
    }
}
function closeStudentModal() {
    const modal = document.getElementById('studentModal');
    if (modal) modal.style.display = 'none';
}

function addInstallmentRow() {
    const index = studentInstallmentRows.length + 1;
    const div = document.createElement('div');
    div.className = 'form-grid';
    div.style.marginBottom = '5px';
    div.innerHTML = `
        <div>
            <label>Installment ${index} Amount (Rs.)</label>
            <input type="number" class="inst-amount" required>
        </div>
        <div>
            <label>Due Date</label>
            <input type="date" class="inst-due" required>
        </div>
    `;
    const container = document.getElementById('installmentsWrapper');
    if (container) {
        container.appendChild(div);
        studentInstallmentRows.push(div);
    }
}

// Open Certificate tab and automatically select a student
function openCertTabWithStudent(studentId) {
    switchStudentTab('certgen');
    // We wait a tiny bit to make sure select option elements are loaded
    setTimeout(() => {
        const select = document.getElementById('certStudentSelect');
        if (select) {
            select.value = studentId;
            loadStudentCertPrefills();
        }
    }, 400);
}

// Open Certificate tab with Bitrix student data (from API, not database)
function openCertTabWithBitrixStudent(bitrixId, name, courseId, institute, startDate, completionDate) {
    switchStudentTab('certgen');
    
    // Wait for tab to load and form elements to be ready
    setTimeout(() => {
        // Pre-fill certificate form with Bitrix student data
        const nameField = document.getElementById('certStudentNameInput') || document.createElement('input');
        const courseField = document.getElementById('certCourseSelect');
        const instituteField = document.getElementById('certInstituteInput') || document.createElement('input');
        const startDateField = document.getElementById('certStartDateInput') || document.createElement('input');
        const completionDateField = document.getElementById('certCompletionDateInput') || document.createElement('input');
        
        // Store Bitrix ID for later use
        if (!document.getElementById('certBitrixIdInput')) {
            const hidden = document.createElement('input');
            hidden.type = 'hidden';
            hidden.id = 'certBitrixIdInput';
            hidden.value = bitrixId;
            const form = document.querySelector('#studentTabCertGen form') || document.getElementById('certParagraphTextarea').parentElement;
            if (form) form.appendChild(hidden);
        } else {
            document.getElementById('certBitrixIdInput').value = bitrixId;
        }
        
        // Populate visible fields
        if (nameField) nameField.value = name;
        if (instituteField) instituteField.value = institute;
        if (startDateField) startDateField.value = startDate;
        if (completionDateField) completionDateField.value = completionDate;
        
        // Update preview
        setTimeout(() => {
            if (nameField && nameField.oninput) nameField.oninput();
        }, 100);
        
        showToast(`Loaded Bitrix student: ${name}`);
    }, 300);
}


// Installments viewer overlay/list
async function viewInstallmentsModal(studentId, name) {
    try {
        const res = await apiFetch(`/student/installments/?student_id=${studentId}`);
        if (res.ok) {
            const installments = await res.json();
            const list = installments.results || installments;
            
            // Open warning toast/alert showing details or build inline popup
            let htmlList = list.map(inst => `
                <div style="border-bottom:1px solid var(--border-color); padding:10px 0; display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <strong>Installment ${inst.installment_number}</strong><br>
                        Amount: Rs. ${inst.amount} | Due: ${inst.due_date}<br>
                        Paid: Rs. ${inst.paid_amount} | Date: ${inst.paid_date || 'N/A'}<br>
                        Status: <span style="font-weight:bold; color:${inst.status === 'PAID' ? '#22c55e' : '#ef4444'}">${inst.status}</span>
                    </div>
                    <div>
                        ${inst.status !== 'PAID' ? `
                            <button class="btn btn-primary" style="font-size:7.5pt; padding:3px 6px;" onclick="openRecordPaymentModal(${inst.id})">Pay</button>
                            <button class="btn" style="font-size:7.5pt; padding:3px 6px; background-color:#eab308; color:white;" onclick="triggerWarningEmail(${inst.id})">Email Warn</button>
                        ` : ''}
                    </div>
                </div>
            `).join('');

            if (list.length === 0) {
                htmlList = '<div>No fee installments defined for this student.</div>';
            }

            // Build standard inline alert dialog or dynamic popup
            alertModalHTML(`Fee installments for ${name}`, htmlList);
        }
    } catch (e) {
        console.error(e);
    }
}

function alertModalHTML(title, content) {
    // Remove previous if exists
    const old = document.getElementById('alertDynamicModal');
    if (old) old.remove();

    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.id = 'alertDynamicModal';
    modal.style.display = 'flex';
    modal.innerHTML = `
        <div class="modal-content" style="max-height:80%; overflow-y:auto;">
            <div class="flex-row-header">
                <h3 style="margin:0;">${title}</h3>
                <button onclick="document.getElementById('alertDynamicModal').remove()" style="background:none; border:none; font-size:16pt; cursor:pointer;">&times;</button>
            </div>
            <div>${content}</div>
        </div>
    `;
    document.body.appendChild(modal);
}

// Record installment payment
function openRecordPaymentModal(instId) {
    // Close dynamic installment viewer
    const dynamic = document.getElementById('alertDynamicModal');
    if (dynamic) dynamic.style.display = 'none';

    const modal = document.getElementById('recordPaymentModal');
    if (modal) {
        modal.style.display = 'flex';
        document.getElementById('paymentInstallmentId').value = instId;
    }
}
function closeRecordPaymentModal() {
    const modal = document.getElementById('recordPaymentModal');
    if (modal) modal.style.display = 'none';
}

async function triggerWarningEmail(instId) {
    try {
        showToast('Sending overdue alert email...');
        const res = await apiFetch(`/student/installments/${instId}/send-warning/`, { method: 'POST' });
        if (res.ok) {
            showToast('Warning email sent successfully to student.');
        } else {
            showToast('Failed to send warning email.', 'error');
        }
    } catch (e) {
        console.error(e);
    }
}

// ---------- TABS CONTROLLERS & DROPDOWNS ----------
function switchStudentTab(tab) {
    const dirTab = document.getElementById('studentTabDirectory');
    const certTab = document.getElementById('studentTabCertGen');
    const bitrixTab = document.getElementById('studentTabBitrix');
    const dirBtn = document.getElementById('tabStudentDirectoryBtn');
    const certBtn = document.getElementById('tabCertGenBtn');
    const bitrixBtn = document.getElementById('tabBitrixStudentsBtn');
    
    // Hide all tabs
    if (dirTab) dirTab.style.display = 'none';
    if (certTab) certTab.style.display = 'none';
    if (bitrixTab) bitrixTab.style.display = 'none';
    
    // Remove active from all buttons
    if (dirBtn) dirBtn.classList.remove('active');
    if (certBtn) certBtn.classList.remove('active');
    if (bitrixBtn) bitrixBtn.classList.remove('active');
    
    if (tab === 'directory') {
        if (dirTab) dirTab.style.display = 'block';
        if (dirBtn) dirBtn.classList.add('active');
        loadStudentData(); // Load Bitrix ongoing students
    } else if (tab === 'bitrix') {
        if (bitrixTab) bitrixTab.style.display = 'block';
        if (bitrixBtn) bitrixBtn.classList.add('active');
        loadBitrixStudents();
    } else {
        if (certTab) certTab.style.display = 'block';
        if (certBtn) certBtn.classList.add('active');
        loadStudentsSelect();
        loadCoursesSelect('certCourseSelect');
    }
}

async function loadBitrixStudents() {
    const tbody = document.getElementById('bitrixStudentTableBody');
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="10" style="text-align:center; padding:30px; color:#64748b;">Loading active students from Bitrix24...</td></tr>';
    
    try {
        const res = await apiFetch('/api/student/bitrix-active/');
        if (res.ok) {
            const data = await res.json();
            const students = data.results || [];
            
            if (students.length === 0) {
                tbody.innerHTML = '<tr><td colspan="10" style="text-align:center; padding:30px; color:#64748b;">No active students found.</td></tr>';
                return;
            }
            
            tbody.innerHTML = students.map(s => `
                <tr>
                    <td>${s.id}</td>
                    <td>${s.name}</td>
                    <td>${s.email}</td>
                    <td>${s.phone}</td>
                    <td>${s.institute}</td>
                    <td>${s.father_name}</td>
                    <td>${s.start_date}</td>
                    <td>${s.completion_date}</td>
                    <td>${s.total_fees}</td>
                    <td><span style="font-size:7.5pt; padding:2px 8px; border-radius:10px; background:#e0f2fe; color:#0369a1; font-weight:600;">${s.stage.split(':').pop()}</span></td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="10" style="text-align:center; padding:30px; color:#ef4444;">Failed to fetch data from Bitrix24.</td></tr>';
        }
    } catch (e) {
        console.error(e);
        tbody.innerHTML = '<tr><td colspan="10" style="text-align:center; padding:30px; color:#ef4444;">Error connecting to Bitrix24 API.</td></tr>';
    }
}

async function loadCoursesSelect(elementId) {
    const el = document.getElementById(elementId);
    if (!el) return;
    try {
        const res = await apiFetch('/api/student/courses/');
        if (res.ok) {
            const data = await res.json();
            const list = data.results || data;
            
            let html = '<option value="">-- Select Course --</option>';
            list.forEach(c => {
                html += `<option value="${c.id}" data-skills='${JSON.stringify(c.skills_list)}' data-duration="${c.default_duration}">${c.course_name}</option>`;
            });
            el.innerHTML = html;
        }
    } catch (e) {
        console.error(e);
    }
}

async function loadStudentsSelect() {
    const el = document.getElementById('certStudentSelect');
    if (!el) return;
    try {
        const res = await apiFetch('/api/student/students/');
        if (res.ok) {
            const data = await res.json();
            const list = data.results || data;
            let html = '<option value="">-- Select Student --</option>';
            list.forEach(s => {
                html += `<option value="${s.id}">${s.name} (${s.cert_no})</option>`;
            });
            el.innerHTML = html;
        }
    } catch (e) {
        console.error(e);
    }
}

function onSelectModalCourse() {
    const select = document.getElementById('studEnrolledCourse');
    const input = document.getElementById('studCourse');
    if (select && input && select.selectedIndex > 0) {
        const option = select.options[select.selectedIndex];
        input.value = option.text;
    }
}

// ---------- EDITOR & PREVIEW LOGIC ----------
async function loadStudentCertPrefills() {
    const select = document.getElementById('certStudentSelect');
    if (!select || !select.value) return;
    
    const studentId = select.value;
    currentSelectedStudentName = select.options[select.selectedIndex].text.split(' (')[0];
    
    try {
        const res = await apiFetch(`/api/student/students/${studentId}/enrollment-details/`);
        if (res.ok) {
            const data = await res.json();
            currentStudentDetails = data;
            
            // Disable downloads until new generation succeeds
            generatedPdfUrl = null;
            document.getElementById('btnDownloadPDF').disabled = true;
            
            // Set Course select
            const courseSelect = document.getElementById('certCourseSelect');
            if (courseSelect) {
                courseSelect.value = data.course_id || '';
            }
            
            // Set Duration input
            const durationInput = document.getElementById('certDurationInput');
            if (durationInput) {
                durationInput.value = data.duration || '';
            }
            
            // Set Place and Issue Date (today)
            document.getElementById('certPlace').value = "Mohali";
            const todayStr = new Date().toISOString().split('T')[0];
            document.getElementById('certIssueDate').value = todayStr;
            
            // Build skills
            renderEditorSkills(data.skills);
            
            // Set Paragraph Text
            const showDates = document.getElementById('certShowDatesToggle').checked;
            document.getElementById('certParagraphTextarea').value = showDates ? data.default_paragraph_with_dates : data.default_paragraph;
            
            // Update preview
            updateLivePreview();
        }
    } catch (e) {
        console.error(e);
    }
}

function renderEditorSkills(skillsList) {
    const container = document.getElementById('certSkillsContainer');
    if (!container) return;
    
    if (!skillsList || skillsList.length === 0) {
        container.innerHTML = '<div style="color:#64748b; font-size:9.5pt;">No skills defined for this course.</div>';
        return;
    }
    
    let html = '';
    skillsList.forEach((skill, idx) => {
        html += `
            <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px dashed var(--border-color); padding-bottom: 6px;">
                <span style="font-weight: 600; font-size: 9.5pt; color: var(--text-color);">${skill}</span>
                <div style="display: flex; gap: 10px;">
                    <label style="margin:0; font-size: 9pt; display: inline-flex; align-items: center; gap: 4px; cursor:pointer;">
                        <input type="radio" name="skill_${idx}" value="Excellent" checked onchange="updateLivePreview()" style="width: auto; cursor:pointer;"> Excellent
                    </label>
                    <label style="margin:0; font-size: 9pt; display: inline-flex; align-items: center; gap: 4px; cursor:pointer;">
                        <input type="radio" name="skill_${idx}" value="Good" onchange="updateLivePreview()" style="width: auto; cursor:pointer;"> Good
                    </label>
                    <label style="margin:0; font-size: 9pt; display: inline-flex; align-items: center; gap: 4px; cursor:pointer;">
                        <input type="radio" name="skill_${idx}" value="Poor" onchange="updateLivePreview()" style="width: auto; cursor:pointer;"> Poor
                    </label>
                </div>
                <input type="hidden" class="skill-name-hidden" value="${skill}">
            </div>
        `;
    });
    container.innerHTML = html;
}

function onCertCourseChange() {
    const select = document.getElementById('certCourseSelect');
    if (!select) return;
    
    if (select.selectedIndex > 0) {
        const option = select.options[select.selectedIndex];
        const duration = option.getAttribute('data-duration') || '6 months';
        const skills = JSON.parse(option.getAttribute('data-skills') || '[]');
        
        document.getElementById('certDurationInput').value = duration;
        renderEditorSkills(skills);
        
        if (currentStudentDetails) {
            currentStudentDetails.course_name = option.text;
            currentStudentDetails.duration = duration;
            currentStudentDetails.skills = skills;
            
            const s_o_d_o = currentStudentDetails.s_o_d_o;
            const father_name = currentStudentDetails.father_name;
            const address = currentStudentDetails.address;
            const student_name = currentStudentDetails.student_name;
            const completion_month = currentStudentDetails.completion_month;
            
            currentStudentDetails.default_paragraph = `This is to certify that **${student_name}** **${s_o_d_o} ${father_name}**, ${address}. Has successfully Completed ${duration} \"**${option.text}**\" course .`;
            currentStudentDetails.default_paragraph_with_dates = `This is to certify that **${student_name}** **${s_o_d_o} ${father_name}**, ${address}. Has successfully Completed \"**${option.text}**\" course in the month of **${completion_month}**.`;
            
            const showDates = document.getElementById('certShowDatesToggle').checked;
            document.getElementById('certParagraphTextarea').value = showDates ? currentStudentDetails.default_paragraph_with_dates : currentStudentDetails.default_paragraph;
        }
    }
    updateLivePreview();
}

function onCertDurationChange() {
    const duration = document.getElementById('certDurationInput').value;
    const textarea = document.getElementById('certParagraphTextarea');
    if (textarea && currentStudentDetails) {
        let text = textarea.value;
        const oldDuration = currentStudentDetails.duration;
        if (text.includes(oldDuration)) {
            textarea.value = text.replace(oldDuration, duration);
            currentStudentDetails.duration = duration;
        }
    }
    updateLivePreview();
}

function onShowDatesToggle() {
    const showDates = document.getElementById('certShowDatesToggle').checked;
    const textarea = document.getElementById('certParagraphTextarea');
    if (textarea && currentStudentDetails) {
        textarea.value = showDates ? currentStudentDetails.default_paragraph_with_dates : currentStudentDetails.default_paragraph;
    }
    updateLivePreview();
}

function updateLivePreview() {
    if (!currentStudentDetails) return;
    
    // 1. Serial Number Preview
    const completionYear = new Date(currentStudentDetails.completion_date).getFullYear() || 2025;
    const batchCode = String(completionYear).slice(-2);
    document.getElementById('prevSerialNo').textContent = `Sr.no DHUB|${batchCode}|XXX`;
    
    // 2. Paragraph Text formatting
    let text = document.getElementById('certParagraphTextarea').value || "";
    let htmlText = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    htmlText = htmlText.replace(/\n/g, '<br>');
    document.getElementById('prevParagraph').innerHTML = htmlText;
    
    // 3. Performance Heading
    const hisHer = currentStudentDetails.his_her || 'his/her';
    const capHisHer = hisHer.charAt(0).toUpperCase() + hisHer.slice(1);
    document.getElementById('prevPerformanceHeading').textContent = `${capHisHer} Performance Given as Below`;
    
    // 4. Skills checkboxes
    const skillsContainer = document.getElementById('certSkillsContainer');
    const prevTable = document.getElementById('prevSkillsTable');
    if (skillsContainer && prevTable) {
        const hiddenInputs = skillsContainer.querySelectorAll('.skill-name-hidden');
        let tableHtml = '<tbody>';
        
        hiddenInputs.forEach((input, idx) => {
            const skillName = input.value;
            const ratingRadio = skillsContainer.querySelector(`input[name="skill_${idx}"]:checked`);
            const rating = ratingRadio ? ratingRadio.value : 'Excellent';
            
            tableHtml += `
                <tr>
                    <td style="padding: 2.5px 0; font-weight:600; width:40%;">${skillName}</td>
                    <td style="padding: 2.5px 0; width:25%;">Excellent <span class="prev-checkbox ${rating === 'Excellent' ? 'checked' : ''}"></span></td>
                    <td style="padding: 2.5px 0; width:17.5%;">Good <span class="prev-checkbox ${rating === 'Good' ? 'checked' : ''}"></span></td>
                    <td style="padding: 2.5px 0; width:17.5%;">Poor <span class="prev-checkbox ${rating === 'Poor' ? 'checked' : ''}"></span></td>
                </tr>
            `;
        });
        tableHtml += '</tbody>';
        prevTable.innerHTML = tableHtml;
    }
    
    // 5. Show Dates Section
    const showDates = document.getElementById('certShowDatesToggle').checked;
    const prevDatesSection = document.getElementById('prevDatesSection');
    if (prevDatesSection) {
        if (showDates) {
            prevDatesSection.style.display = 'block';
            const joiningDate = formatInputDate(currentStudentDetails.joining_date);
            const completionDate = formatInputDate(currentStudentDetails.completion_date);
            document.getElementById('prevJoinDate').textContent = `Date of joining : ${joiningDate}`;
            document.getElementById('prevCompDate').textContent = `Date of completion : ${completionDate}`;
        } else {
            prevDatesSection.style.display = 'none';
        }
    }
    
    // 6. Closing Text
    const heShe = currentStudentDetails.he_she || 'he/she';
    document.getElementById('prevClosingText').textContent = `We hope ${heShe} serves ${hisHer} best service to this industry.`;
    
    // 7. Footer text
    const issueDateVal = document.getElementById('certIssueDate').value;
    const formattedIssueDate = issueDateVal ? formatInputDate(issueDateVal) : '';
    document.getElementById('prevIssueDateText').textContent = `Date: ${formattedIssueDate}`;
    
    const placeVal = document.getElementById('certPlace').value;
    document.getElementById('prevPlaceText').textContent = `Place: ${placeVal}`;
}

function formatInputDate(dateString) {
    if (!dateString) return '';
    const parts = dateString.split('-');
    if (parts.length === 3) {
        return `${parts[2]}-${parts[1]}-${parts[0]}`; // DD-MM-YYYY
    }
    return dateString;
}

// ---------- ACTIONS ----------
async function generateAndSaveCertificate() {
    const select = document.getElementById('certStudentSelect');
    if (!select || !select.value) {
        showToast('Please select a student.', 'error');
        return;
    }
    const courseSelect = document.getElementById('certCourseSelect');
    if (!courseSelect || !courseSelect.value) {
        showToast('Please select a course.', 'error');
        return;
    }
    
    const skillRatings = {};
    const container = document.getElementById('certSkillsContainer');
    if (container) {
        const hiddenInputs = container.querySelectorAll('.skill-name-hidden');
        hiddenInputs.forEach((input, idx) => {
            const skillName = input.value;
            const ratingRadio = container.querySelector(`input[name="skill_${idx}"]:checked`);
            skillRatings[skillName] = ratingRadio ? ratingRadio.value : 'Excellent';
        });
    }
    
    const data = {
        student: parseInt(select.value),
        course: parseInt(courseSelect.value),
        skill_ratings: skillRatings,
        show_dates: document.getElementById('certShowDatesToggle').checked,
        issue_date: document.getElementById('certIssueDate').value,
        place: document.getElementById('certPlace').value,
        cert_content: document.getElementById('certParagraphTextarea').value
    };
    
    showToast('Generating and saving certificate PDF...');
    
    try {
        const res = await apiFetch('/api/student/certificates/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
        
        if (res.ok) {
            const result = await res.json();
            showToast('Certificate saved & PDF generated successfully!');
            
            generatedPdfUrl = result.pdf_file;
            document.getElementById('btnDownloadPDF').disabled = false;
            
            document.getElementById('prevSerialNo').textContent = `Sr.no ${result.serial_no}`;
            loadStudentData();
        } else {
            const err = await res.json();
            showToast(JSON.stringify(err), 'error');
        }
    } catch (e) {
        console.error(e);
        showToast('An error occurred during certificate generation.', 'error');
    }
}

function downloadGeneratedPDF() {
    if (generatedPdfUrl) {
        window.open(generatedPdfUrl, '_blank');
    } else {
        showToast('No PDF generated yet.', 'error');
    }
}



// ---------- DOM SETUP & SUBMISSION ----------
document.addEventListener('DOMContentLoaded', () => {
    // Register student submit
    const studentForm = document.getElementById('studentForm');
    if (studentForm) {
        studentForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            // Build installments schedule
            const schedule = [];
            const amounts = document.querySelectorAll('.inst-amount');
            const dues = document.querySelectorAll('.inst-due');
            for (let i = 0; i < amounts.length; i++) {
                schedule.push({
                    amount: amounts[i].value,
                    due_date: dues[i].value
                });
            }

            const enrolledCourseVal = document.getElementById('studEnrolledCourse').value;
            const data = {
                name: document.getElementById('studName').value,
                email: document.getElementById('studEmail').value,
                phone: document.getElementById('studPhone').value,
                institute: document.getElementById('studInstitute').value,
                course_at_institute: document.getElementById('studCourse').value,
                enrolled_course: enrolledCourseVal ? parseInt(enrolledCourseVal) : null,
                gender: document.getElementById('studGender').value,
                father_name: document.getElementById('studFatherName').value,
                address: document.getElementById('studAddress').value,
                student_type: document.getElementById('studType').value,
                program_name: document.getElementById('studProgram').value,
                department: document.getElementById('studDept').value,
                mentor: document.getElementById('studMentor').value,
                joining_date: document.getElementById('studJoining').value,
                completion_date: document.getElementById('studCompletion').value,
                cert_type: document.getElementById('studCertType').value,
                total_fees: document.getElementById('studFees').value,
                installments_schedule: schedule
            };

            try {
                const res = await apiFetch('/students/', {
                    method: 'POST',
                    body: JSON.stringify(data)
                });
                if (res.ok) {
                    showToast('Student registered successfully!');
                    closeStudentModal();
                    loadStudentData();
                } else {
                    const err = await res.json();
                    showToast(JSON.stringify(err), 'error');
                }
            } catch (ex) {
                console.error(ex);
            }
        });
    }

    // Submit payment recording
    const paymentForm = document.getElementById('recordPaymentForm');
    if (paymentForm) {
        paymentForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const instId = document.getElementById('paymentInstallmentId').value;
            const data = {
                amount_paid: document.getElementById('paymentAmountPaid').value,
                remarks: document.getElementById('paymentRemarks').value
            };

            try {
                const res = await apiFetch(`/student/installments/${instId}/record-payment/`, {
                    method: 'POST',
                    body: JSON.stringify(data)
                });
                if (res.ok) {
                    showToast('Payment recorded successfully.');
                    closeRecordPaymentModal();
                    loadStudentData();
                } else {
                    showToast('Failed to record payment.', 'error');
                }
            } catch (ex) {
                console.error(ex);
            }
        });
    }
});
