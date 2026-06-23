// static/js/features/student.js
// Students and Interns registry, installments, certificate generation handlers

let studentInstallmentRows = [];
let currentSelectedStudentName = '';
let currentStudentDetails = null;
let generatedPdfUrl = null;
let certEditorSkills = [];
let currentStudentList = [];

let studentDirectoryStart = 0;
let studentDirectoryNext = null;
let bitrixStudentStart = 0;
let bitrixStudentNext = null;

// ---------- STUDENTS & INTERNS VIEW ----------
async function loadStudentData() {
    document.getElementById('pageTitle').textContent = 'Student / Intern Module';
    // Load ongoing students from Bitrix24 API with pagination
    try {
        const res = await apiFetch(`/api/student/bitrix-active/?start=${studentDirectoryStart}`);
        if (res.ok) {
            const data = await res.json();
            const studList = data.results || [];
            currentStudentList = studList;
            studentDirectoryNext = data.next !== undefined ? data.next : null;

            const tbody = document.getElementById('studentTableBody');
            if (tbody) {
                if (studList.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:30px; color:#64748b;">No ongoing students found.</td></tr>';
                    // Update pagination controls
                    updateStudentDirectoryPagination(0);
                    return;
                }

                tbody.innerHTML = studList.map((s, index) => `
                    <tr onclick="handleStudentRowClick(event, ${index})" style="cursor: pointer;">
                        <td>${s.name || '-'}</td>
                        <td>${s.email || '-'}</td>
                        <td>Rs. ${s.total_fees || '0'}</td>
                        <td><span style="font-weight:bold; color:#eab308; font-size:8.5pt;">ONGOING</span></td>
                        <td style="white-space: nowrap;" onclick="event.stopPropagation()">
                            <button class="btn" style="font-size:8pt; padding:4px 8px;" onclick="openCertTabWithBitrixStudent(${index})">Generate Cert</button>
                        </td>
                    </tr>
                `).join('');

                // Update pagination controls
                updateStudentDirectoryPagination(studList.length);
            }
        } else {
            const tbody = document.getElementById('studentTableBody');
            if (tbody) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:30px; color:#ef4444;">Failed to fetch ongoing students from Bitrix24.</td></tr>';
            }
        }
    } catch (e) {
        console.error('Error loading students:', e);
        const tbody = document.getElementById('studentTableBody');
        if (tbody) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:30px; color:#ef4444;">Error connecting to Bitrix24 API.</td></tr>';
        }
    }
}

function updateStudentDirectoryPagination(count) {
    const pageStart = count === 0 ? 0 : studentDirectoryStart + 1;
    const pageEnd = count === 0 ? 0 : studentDirectoryStart + count;

    const startEl = document.getElementById('studentPageStart');
    const endEl = document.getElementById('studentPageEnd');
    const prevBtn = document.getElementById('studentPrevBtn');
    const nextBtn = document.getElementById('studentNextBtn');

    if (startEl) startEl.textContent = pageStart;
    if (endEl) endEl.textContent = pageEnd;
    if (prevBtn) prevBtn.disabled = (studentDirectoryStart === 0);
    if (nextBtn) nextBtn.disabled = (studentDirectoryNext === null);
}

function updateStudentDirectoryPagination(count) {
    const pageStart = count === 0 ? 0 : studentDirectoryStart + 1;
    const pageEnd = count === 0 ? 0 : studentDirectoryStart + count;

    const startEl = document.getElementById('studentPageStart');
    const endEl = document.getElementById('studentPageEnd');
    const prevBtn = document.getElementById('studentPrevBtn');
    const nextBtn = document.getElementById('studentNextBtn');

    if (startEl) startEl.textContent = pageStart;
    if (endEl) endEl.textContent = pageEnd;
    if (prevBtn) prevBtn.disabled = (studentDirectoryStart === 0);
    if (nextBtn) nextBtn.disabled = (studentDirectoryNext === null);
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
    switchStudentTab('certgen', studentId);
}

// Open Certificate tab with Bitrix student data (from API, not database)
async function openCertTabWithBitrixStudent(index) {
    const s = currentStudentList[index];
    if (!s) return;
    showGlobalLoader(true);
    try {
        const payload = {
            id: s.bitrix_id ?? s.id,
            name: s.name,
            email: s.email,
            course_name: s.course_id ? String(s.course_id) : '',
            institute: s.institute || '',
            start_date: s.start_date || '',
            completion_date: s.completion_date || '',
            total_fees: s.total_fees || '0'
        };
        const res = await apiFetch('/api/student/students/get-or-create-from-bitrix/', {
            method: 'POST',
            body: JSON.stringify(payload)
        });
        if (res.ok) {
            const student = await res.json();
            switchStudentTab('certgen');

            // Reload the students select dropdown so it contains the new/updated student
            await loadStudentsSelect();

            // Pre-select the student in the dropdown
            const select = document.getElementById('certStudentSelect');
            if (select) {
                select.value = student.id;
                // Trigger the prefills and preview load
                await loadStudentCertPrefills();
            }
            showToast(`Loaded and synced student: ${student.name}`);
        } else {
            const err = await res.json();
            showToast(JSON.stringify(err), 'error');
        }
    } catch (e) {
        console.error(e);
        showToast('Error syncing student data.', 'error');
    } finally {
        hideGlobalLoader();
    }
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
function switchStudentTab(tab, selectedStudentId = null) {
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
        studentDirectoryStart = 0;
        loadStudentData(); // Load Bitrix ongoing students
    } else if (tab === 'bitrix') {
        if (bitrixTab) bitrixTab.style.display = 'block';
        if (bitrixBtn) bitrixBtn.classList.add('active');
        bitrixStudentStart = 0;
        loadBitrixStudents();
    } else {
        if (certTab) certTab.style.display = 'block';
        if (certBtn) {
            certBtn.classList.add('active');
            certBtn.style.display = 'inline-block'; // Ensure the tab button is shown
        }
        loadStudentsSelect(selectedStudentId);
        loadCoursesSelect('certCourseSelect');
    }
}

async function loadBitrixStudents(forceRefresh = false) {
    const tbody = document.getElementById('bitrixStudentTableBody');
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="10" style="text-align:center; padding:30px; color:#64748b;">Loading active students from Bitrix24...</td></tr>';

    try {
        const res = await apiFetch(`/api/student/bitrix-active/?start=${bitrixStudentStart}`);
        if (res.ok) {
            const data = await res.json();
            const students = data.results || [];
            bitrixStudentNext = data.next !== undefined ? data.next : null;

            if (students.length === 0) {
                tbody.innerHTML = '<tr><td colspan="10" style="text-align:center; padding:30px; color:#64748b;">No active students found.</td></tr>';
                updateBitrixStudentPagination(0);
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

            updateBitrixStudentPagination(students.length);
        } else {
            tbody.innerHTML = '<tr><td colspan="10" style="text-align:center; padding:30px; color:#ef4444;">Failed to fetch data from Bitrix24.</td></tr>';
        }
    } catch (e) {
        console.error(e);
        tbody.innerHTML = '<tr><td colspan="10" style="text-align:center; padding:30px; color:#ef4444;">Error connecting to Bitrix24 API.</td></tr>';
    }
}

function updateBitrixStudentPagination(count) {
    const pageStart = count === 0 ? 0 : bitrixStudentStart + 1;
    const pageEnd = count === 0 ? 0 : bitrixStudentStart + count;

    const startEl = document.getElementById('bitrixStudentPageStart');
    const endEl = document.getElementById('bitrixStudentPageEnd');
    const prevBtn = document.getElementById('bitrixStudentPrevBtn');
    const nextBtn = document.getElementById('bitrixStudentNextBtn');

    if (startEl) startEl.textContent = pageStart;
    if (endEl) endEl.textContent = pageEnd;
    if (prevBtn) prevBtn.disabled = (bitrixStudentStart === 0);
    if (nextBtn) nextBtn.disabled = (bitrixStudentNext === null);
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

async function loadStudentsSelect(selectedStudentId = null) {
    const el = document.getElementById('certStudentSelect');
    if (!el) return;
    try {
        const res = await apiFetch('/api/student/students/?status=ACTIVE');
        if (res.ok) {
            const data = await res.json();
            const list = data.results || data;
            let html = '<option value="">-- Select Student --</option>';
            list.forEach(s => {
                html += `<option value="${s.id}">${s.name} (${s.cert_no})</option>`;
            });
            el.innerHTML = html;
            if (selectedStudentId) {
                el.value = selectedStudentId;
                loadStudentCertPrefills();
            }
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
            certEditorSkills = (data.skills || []).map(s => ({ name: s, rating: 'Excellent' }));
            renderEditorSkills();

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

function renderEditorSkills() {
    const container = document.getElementById('certSkillsContainer');
    if (!container) return;

    if (certEditorSkills.length === 0) {
        container.innerHTML = '<div style="color:#64748b; font-size:9.5pt; text-align: center; padding: 15px;">No skills added. Click "+ Add Skill" to add one.</div>';
        return;
    }

    let html = '';
    certEditorSkills.forEach((skill, idx) => {
        html += `
            <div class="skill-row-item" style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px dashed var(--border-color); padding-bottom: 8px; gap: 10px;">
                <div style="display: flex; align-items: center; gap: 8px; width: 45%;">
                    <button type="button" onclick="removeCertSkill(${idx})" style="background: none; border: none; color: #ef4444; font-size: 14pt; cursor: pointer; padding: 0 4px; line-height: 1;" title="Remove Skill">&times;</button>
                    <input type="text" value="${skill.name}" oninput="updateSkillName(${idx}, this.value)" style="font-weight: 600; font-size: 9.5pt; color: var(--text-color); width: 100%; border: 1px solid var(--border-color); border-radius: 4px; padding: 4px 8px; box-sizing: border-box;" placeholder="Skill Name">
                </div>
                <div style="display: flex; gap: 10px;">
                    <label style="margin:0; font-size: 9pt; display: inline-flex; align-items: center; gap: 4px; cursor:pointer;">
                        <input type="radio" name="skill_${idx}" value="Excellent" ${skill.rating === 'Excellent' ? 'checked' : ''} onchange="updateSkillRating(${idx}, this.value)" style="width: auto; cursor:pointer;"> Excellent
                    </label>
                    <label style="margin:0; font-size: 9pt; display: inline-flex; align-items: center; gap: 4px; cursor:pointer;">
                        <input type="radio" name="skill_${idx}" value="Good" ${skill.rating === 'Good' ? 'checked' : ''} onchange="updateSkillRating(${idx}, this.value)" style="width: auto; cursor:pointer;"> Good
                    </label>
                    <label style="margin:0; font-size: 9pt; display: inline-flex; align-items: center; gap: 4px; cursor:pointer;">
                        <input type="radio" name="skill_${idx}" value="Poor" ${skill.rating === 'Poor' ? 'checked' : ''} onchange="updateSkillRating(${idx}, this.value)" style="width: auto; cursor:pointer;"> Poor
                    </label>
                </div>
                <input type="hidden" class="skill-name-hidden" value="${skill.name}">
            </div>
        `;
    });
    container.innerHTML = html;
}

function addCustomCertSkill() {
    certEditorSkills.push({ name: 'New Skill', rating: 'Excellent' });
    renderEditorSkills();
    updateLivePreview();
}

function removeCertSkill(idx) {
    certEditorSkills.splice(idx, 1);
    renderEditorSkills();
    updateLivePreview();
}

function updateSkillName(idx, name) {
    if (certEditorSkills[idx]) {
        certEditorSkills[idx].name = name;
        const rows = document.querySelectorAll('.skill-row-item');
        if (rows[idx]) {
            const hidden = rows[idx].querySelector('.skill-name-hidden');
            if (hidden) hidden.value = name;
        }
        updateLivePreview();
    }
}

function updateSkillRating(idx, rating) {
    if (certEditorSkills[idx]) {
        certEditorSkills[idx].rating = rating;
        updateLivePreview();
    }
}

function onCertCourseChange() {
    const select = document.getElementById('certCourseSelect');
    if (!select) return;

    if (select.selectedIndex > 0) {
        const option = select.options[select.selectedIndex];
        const duration = option.getAttribute('data-duration') || '6 months';
        const skills = JSON.parse(option.getAttribute('data-skills') || '[]');

        document.getElementById('certDurationInput').value = duration;
        certEditorSkills = skills.map(s => ({ name: s, rating: 'Excellent' }));
        renderEditorSkills();

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
            if (err.requires_override) {
                if (confirm(err.warning)) {
                    data.confirm_override = true;
                    showToast('Generating and saving certificate (with override)...');
                    const retryRes = await apiFetch('/api/student/certificates/', {
                        method: 'POST',
                        body: JSON.stringify(data)
                    });
                    if (retryRes.ok) {
                        const retryResult = await retryRes.json();
                        showToast('Certificate saved & PDF generated successfully!');
                        generatedPdfUrl = retryResult.pdf_file;
                        document.getElementById('btnDownloadPDF').disabled = false;
                        document.getElementById('prevSerialNo').textContent = `Sr.no ${retryResult.serial_no}`;
                        loadStudentData();
                    } else {
                        const retryErr = await retryRes.json();
                        showToast(retryErr.error || JSON.stringify(retryErr), 'error');
                    }
                }
            } else {
                showToast(err.error || JSON.stringify(err), 'error');
            }
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
                const res = await apiFetch(`/api/student/installments/${instId}/record-payment/`, {
                    method: 'POST',
                    body: JSON.stringify(data)
                });
                if (res.ok) {
                    showToast('Payment recorded successfully.');
                    closeRecordPaymentModal();
                    // If detail panel is open and installments tab is active, reload list
                    const detailView = document.getElementById('studentDetailView');
                    if (detailView && detailView.style.display !== 'none') {
                        loadStudentInstallmentsList();
                    } else {
                        loadStudentData();
                    }
                } else {
                    showToast('Failed to record payment.', 'error');
                }
            } catch (ex) {
                console.error(ex);
            }
        });
    }

    // Submit student edit
    const editStudentForm = document.getElementById('editStudentForm');
    if (editStudentForm) {
        editStudentForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (!currentStudentDetails) return;

            showToast('Saving changes...');
            const enrolledCourseVal = document.getElementById('editStudEnrolledCourse').value;
            const data = {
                name: document.getElementById('editStudName').value,
                email: document.getElementById('editStudEmail').value,
                phone: document.getElementById('editStudPhone').value,
                father_name: document.getElementById('editStudFatherName').value,
                gender: document.getElementById('editStudGender').value,
                dob: document.getElementById('editStudDob').value || null,
                address: document.getElementById('editStudAddress').value,
                institute: document.getElementById('editStudInstitute').value,
                enrolled_course: enrolledCourseVal ? parseInt(enrolledCourseVal) : null,
                course_at_institute: document.getElementById('editStudCourse').value,
                student_type: document.getElementById('editStudType').value,
                cert_type: document.getElementById('editStudCertType').value,
                program_name: document.getElementById('editStudProgram').value,
                department: parseInt(document.getElementById('editStudDept').value),
                mentor: document.getElementById('editStudMentor').value,
                joining_date: document.getElementById('editStudJoining').value,
                completion_date: document.getElementById('editStudCompletion').value,
                total_fees: document.getElementById('editStudFees').value,
                status: document.getElementById('editStudStatus').value
            };

            try {
                const res = await apiFetch(`/api/student/students/${currentStudentDetails.id}/`, {
                    method: 'PATCH',
                    body: JSON.stringify(data)
                });
                if (res.ok) {
                    showToast('Student profile updated successfully.');
                    openStudentProfileDetail(currentStudentDetails.id, 'personal');
                    loadStudentData();
                } else {
                    const err = await res.json();
                    showToast('Failed to update profile: ' + JSON.stringify(err), 'error');
                }
            } catch (ex) {
                console.error(ex);
                showToast('Error saving changes.', 'error');
            }
        });
    }

    // Submit student document upload
    const studentDocUploadForm = document.getElementById('studentDocUploadForm');
    if (studentDocUploadForm) {
        studentDocUploadForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (!currentStudentDetails) return;

            showToast('Uploading document...');
            const formData = new FormData();
            formData.append('student', currentStudentDetails.id);
            formData.append('doc_type', document.getElementById('studentUploadDocType').value);
            formData.append('label', document.getElementById('studentUploadDocLabel').value);
            formData.append('remarks', document.getElementById('studentUploadDocRemarks').value);

            const fileInput = document.getElementById('studentUploadDocFile');
            if (fileInput.files.length > 0) {
                formData.append('file', fileInput.files[0]);
            }

            try {
                const res = await apiFetch('/api/student/documents/', {
                    method: 'POST',
                    body: formData
                });
                if (res.ok) {
                    showToast('Document uploaded successfully.');
                    fileInput.value = '';
                    document.getElementById('studentUploadDocLabel').value = '';
                    document.getElementById('studentUploadDocRemarks').value = '';
                    loadStudentDocumentsList();
                } else {
                    const err = await res.json();
                    showToast(JSON.stringify(err), 'error');
                }
            } catch (ex) {
                console.error(ex);
                showToast('Error uploading document.', 'error');
            }
        });
    }
});

// ---------- STUDENT PROFILE PANEL DYNAMIC LOGIC ----------
let activeStudentProfileTab = 'personal';

async function handleStudentRowClick(event, index) {
    if (event.target.tagName === 'BUTTON' || event.target.closest('button')) {
        return;
    }

    const s = currentStudentList[index];
    if (!s) return;

    switchView('studentDetailView', false);
    showGlobalLoader(true);
    try {
        const payload = {
            id: s.bitrix_id ?? s.id,
            name: s.name,
            email: s.email,
            course_name: s.course_id ? String(s.course_id) : '',
            institute: s.institute || '',
            start_date: s.start_date || '',
            completion_date: s.completion_date || '',
            total_fees: s.total_fees || '0'
        };
        const res = await apiFetch('/api/student/students/get-or-create-from-bitrix/', {
            method: 'POST',
            body: JSON.stringify(payload)
        });
        if (res.ok) {
            const student = await res.json();
            openStudentProfileDetail(student.id);
        } else {
            const err = await res.json();
            showToast(JSON.stringify(err), 'error');
        }
    } catch (e) {
        console.error(e);
        showToast('Error syncing student data.', 'error');
    } finally {
        hideGlobalLoader();
    }
}

async function openStudentProfileDetail(studentId, tabToFocus = 'personal', shouldSwitchView = true) {
    if (shouldSwitchView) {
        switchView('studentDetailView', true, {
            studentId: studentId,
            studentTab: tabToFocus,
            skipStudentDetailLoad: true
        });
    }
    showGlobalLoader(true);
    try {
        const res = await apiFetch(`/api/student/students/${studentId}/`);
        if (res.ok) {
            const student = await res.json();
            currentStudentDetails = student;

            // Populate header banner
            const nameEl = document.getElementById('detailStudentName');
            if (nameEl) nameEl.textContent = student.name || '';
            const courseEl = document.getElementById('detailStudentCourse');
            if (courseEl) courseEl.textContent = student.course_at_institute || 'General';
            const deptEl = document.getElementById('detailStudentDept');
            if (deptEl) deptEl.textContent = student.department_details ? student.department_details.name : 'Training';
            const certNoEl = document.getElementById('detailStudentCertNo');
            if (certNoEl) certNoEl.textContent = student.cert_no || 'Pending';

            // Student type badge styling
            const typeBadge = document.getElementById('detailStudentTypeBadge');
            if (typeBadge) {
                typeBadge.textContent = student.student_type;
                if (student.student_type === 'INTERN') {
                    typeBadge.style.backgroundColor = '#8b5cf6'; // Purple
                } else if (student.student_type === 'TRAINEE') {
                    typeBadge.style.backgroundColor = '#3b82f6'; // Blue
                } else {
                    typeBadge.style.backgroundColor = '#10b981'; // Green
                }
                typeBadge.style.color = 'white';
            }

            // Status badge styling
            const statusBadge = document.getElementById('detailStudentStatusBadge');
            if (statusBadge) {
                statusBadge.textContent = student.status;
                if (student.status === 'ACTIVE') {
                    statusBadge.style.backgroundColor = '#10b981';
                } else if (student.status === 'COMPLETED') {
                    statusBadge.style.backgroundColor = '#10b981';
                } else {
                    statusBadge.style.backgroundColor = '#ef4444';
                }
                statusBadge.style.color = 'white';
            }

            // Populate Form Fields (Personal Info Tab) safely
            const setVal = (id, val) => {
                const el = document.getElementById(id);
                if (el) el.value = val || '';
            };

            setVal('editStudName', student.name);
            setVal('editStudEmail', student.email);
            setVal('editStudPhone', student.phone);
            setVal('editStudFatherName', student.father_name);
            setVal('editStudGender', student.gender || 'MALE');
            setVal('editStudDob', student.dob);
            setVal('editStudAddress', student.address);
            setVal('editStudInstitute', student.institute);
            setVal('editStudCourse', student.course_at_institute);
            setVal('editStudType', student.student_type || 'TRAINEE');
            setVal('editStudCertType', student.cert_type || 'TRAINING_CERT');
            setVal('editStudProgram', student.program_name);
            setVal('editStudMentor', student.mentor);
            setVal('editStudJoining', student.joining_date);
            setVal('editStudCompletion', student.completion_date);
            setVal('editStudFees', student.total_fees || '0');
            setVal('editStudStatus', student.status || 'ACTIVE');

            // Load enrolled course and departments dropdowns
            await loadStudentDetailSelects(student.enrolled_course, student.department);

            switchStudentProfileTab(tabToFocus);
        } else {
            showToast('Failed to load student details.', 'error');
        }
    } catch (e) {
        console.error('Error inside openStudentProfileDetail:', e);
        showToast('Error loading student details: ' + e.message, 'error');
    } finally {
        hideGlobalLoader();
    }
}

async function loadStudentDetailSelects(enrolledCourseId, deptId) {
    // Enrolled Courses Select
    const courseSelect = document.getElementById('editStudEnrolledCourse');
    if (courseSelect) {
        try {
            const res = await apiFetch('/api/student/courses/');
            if (res.ok) {
                const data = await res.json();
                const list = data.results || data;
                let html = '<option value="">-- Select Course --</option>';
                list.forEach(c => {
                    html += `<option value="${c.id}">${c.course_name}</option>`;
                });
                courseSelect.innerHTML = html;
                courseSelect.value = enrolledCourseId || '';
            }
        } catch (e) {
            console.error(e);
        }
    }

    // Departments Select
    const deptSelect = document.getElementById('editStudDept');
    if (deptSelect) {
        try {
            const res = await apiFetch('/onboarding/departments/');
            if (res.ok) {
                const depts = await res.json();
                const deptList = depts.results || depts;
                let html = deptList.map(d => `<option value="${d.id}">${d.name}</option>`).join('');
                deptSelect.innerHTML = html;
                deptSelect.value = deptId || '';
            }
        } catch (e) {
            console.error(e);
        }
    }
}

function switchStudentProfileTab(tabId) {
    activeStudentProfileTab = tabId;
    const tabs = ['personal', 'docs', 'installments', 'certificates'];

    tabs.forEach(t => {
        const btn = document.getElementById(`sTab${t.charAt(0).toUpperCase() + t.slice(1)}Btn`);
        const block = document.getElementById(`studentTab${t.charAt(0).toUpperCase() + t.slice(1)}`);

        if (t === tabId) {
            if (btn) {
                btn.classList.add('active');
                btn.style.color = 'var(--primary-color)';
                btn.style.borderBottom = '3px solid var(--primary-color)';
            }
            if (block) {
                block.style.display = 'block';
            }
        } else {
            if (btn) {
                btn.classList.remove('active');
                btn.style.color = 'var(--text-muted)';
                btn.style.borderBottom = '3px solid transparent';
            }
            if (block) {
                block.style.display = 'none';
            }
        }
    });

    if (tabId === 'docs') loadStudentDocumentsList();
    else if (tabId === 'installments') loadStudentInstallmentsList();
    else if (tabId === 'certificates') loadStudentCertificatesList();
}

// ---------- DOCUMENTS TAB LOGIC ----------
function toggleStudentDocLabelField() {
    const typeSelect = document.getElementById('studentUploadDocType');
    const container = document.getElementById('studentDocLabelContainer');
    if (typeSelect && container) {
        if (typeSelect.value === 'OTHER') {
            container.style.display = 'block';
            document.getElementById('studentUploadDocLabel').setAttribute('required', 'true');
        } else {
            container.style.display = 'none';
            document.getElementById('studentUploadDocLabel').removeAttribute('required');
        }
    }
}

async function loadStudentDocumentsList() {
    if (!currentStudentDetails) return;

    try {
        const res = await apiFetch(`/api/student/documents/?student_id=${currentStudentDetails.id}`);
        if (res.ok) {
            const docs = await res.json();
            const docList = docs.results || docs;

            // Render interactive checklist
            renderStudentDocumentsChecklist(docList);

            // Render attachments table
            const tbody = document.getElementById('studentDocsTableBody');
            if (tbody) {
                if (docList.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:20px; color:var(--text-light);">No documents uploaded yet.</td></tr>';
                    return;
                }

                tbody.innerHTML = docList.map(d => `
                    <tr style="border-bottom: 1px solid var(--border-color); height: 50px;">
                        <td style="padding: 10px 20px; font-weight: 600; color: var(--text-main); font-size: 13px;">${getDocTypeLabel(d.doc_type)}</td>
                        <td style="padding: 10px 20px; color: var(--text-secondary); font-size: 13px;">${d.label || d.remarks || '-'}</td>
                        <td style="padding: 10px 20px; color: var(--text-secondary); font-size: 13px;">${formatDate(d.upload_date)}</td>
                        <td style="padding: 10px 20px; color: var(--text-secondary); font-size: 13px;">${d.uploaded_by_username || 'System'}</td>
                        <td style="padding: 10px 20px; text-align: center;">
                            <div style="display: flex; justify-content: center; gap: 8px;">
                                <a href="${d.file}" target="_blank" class="btn" style="font-size: 8pt; padding: 4px 8px; background-color: var(--primary-light); color: var(--primary-color);">👁️ View</a>
                                <button class="btn" style="font-size: 8pt; padding: 4px 8px; background-color: #ef4444; color: white;" onclick="deleteStudentDoc(${d.id})">Delete</button>
                            </div>
                        </td>
                    </tr>
                `).join('');
            }
        }
    } catch (e) {
        console.error(e);
    }
}

function getDocTypeLabel(docType) {
    const labels = {
        'RESUME': 'Resume / CV',
        'AADHAAR': 'ID Proof (Aadhaar Card)',
        'COLLEGE_ID': 'College ID / Enrollment Letter',
        'JOINING_LETTER': 'Joining Letter',
        'FEE_RECEIPT': 'Fee Receipt',
        'OTHER': 'Other'
    };
    return labels[docType] || docType;
}

function renderStudentDocumentsChecklist(docList) {
    const container = document.getElementById('studentDocumentsChecklistContainer');
    if (!container) return;

    const requiredDocs = [
        { type: 'RESUME', name: 'Resume / CV', desc: 'Verify professional/academic experience.' },
        { type: 'AADHAAR', name: 'ID Proof (Aadhaar Card)', desc: 'Government identity verification.' },
        { type: 'COLLEGE_ID', name: 'College ID / Enrollment Letter', desc: 'College credential validation.' },
        { type: 'JOINING_LETTER', name: 'Signed Joining Letter', desc: 'Acceptance of student guidelines.' },
        { type: 'FEE_RECEIPT', name: 'Fee Receipt', desc: 'Payment receipt confirmation.' }
    ];

    container.innerHTML = requiredDocs.map(req => {
        const doc = docList.find(d => d.doc_type === req.type);
        const isUploaded = !!doc;

        const badgeBg = isUploaded ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)';
        const badgeTextColor = isUploaded ? '#10b981' : '#ef4444';
        const badgeBorderColor = isUploaded ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)';
        const badgeText = isUploaded ? 'Uploaded' : 'Missing';

        return `
            <div style="background-color: var(--bg-card); border: 1.5px solid ${isUploaded ? '#e2e8f0' : badgeBorderColor}; border-radius: 12px; padding: 16px; display: flex; flex-direction: column; justify-content: space-between; gap: 12px; box-shadow: var(--shadow-sm); transition: all 0.2s;" onmouseover="this.style.boxShadow='var(--shadow-md)'" onmouseout="this.style.boxShadow='var(--shadow-sm)'">
                <div>
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 10px;">
                        <span style="font-weight: 700; color: var(--text-main); font-size: 13.5px; line-height: 1.3;">${req.name}</span>
                        <span style="background-color: ${badgeBg}; color: ${badgeTextColor}; padding: 3px 8px; border-radius: 999px; font-size: 10px; font-weight: 700; border: 1px solid ${badgeBorderColor}; white-space: nowrap;">${badgeText}</span>
                    </div>
                    <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px; line-height: 1.3;">${req.desc}</div>
                </div>
                ${isUploaded ? `
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-top: 5px; border-top: 1px solid var(--border-color); padding-top: 8px;">
                        <span style="font-size: 9.5px; color: var(--text-light); font-family: monospace;">Uploaded: ${formatSimpleDate(doc.upload_date)}</span>
                        <a href="${doc.file}" target="_blank" class="btn" style="padding: 4px 10px; font-size: 10px; border-radius: 6px; font-weight:700; background-color: var(--primary-light); color: var(--primary-color);">👁️ View</a>
                    </div>
                ` : `
                    <div style="margin-top: 5px; border-top: 1px dashed var(--border-color); padding-top: 8px;">
                        <button class="btn btn-primary btn-sm" style="width: 100%; font-size: 11px; padding: 6px; border-radius: 6px; background-color: var(--primary-light); color: var(--primary-color); border: 1px solid rgba(124,58,237,0.2); font-weight:700;" onclick="document.getElementById('studentUploadDocType').value='${req.type}'; toggleStudentDocLabelField(); document.getElementById('studentUploadDocFile').focus();">Upload File</button>
                    </div>
                `}
            </div>
        `;
    }).join('');
}

async function deleteStudentDoc(docId) {
    if (!confirm('Are you sure you want to delete this document?')) return;

    showToast('Deleting document...');
    try {
        const res = await apiFetch(`/api/student/documents/${docId}/`, {
            method: 'DELETE'
        });
        if (res.ok) {
            showToast('Document deleted.');
            loadStudentDocumentsList();
        } else {
            showToast('Failed to delete document.', 'error');
        }
    } catch (e) {
        console.error(e);
    }
}

// ---------- FEE INSTALLMENTS TAB LOGIC ----------
async function loadStudentInstallmentsList() {
    if (!currentStudentDetails) return;

    try {
        const res = await apiFetch(`/api/student/installments/?student_id=${currentStudentDetails.id}`);
        if (res.ok) {
            const list = await res.json();
            const instList = list.results || list;

            const tbody = document.getElementById('studentInstallmentsTableBody');
            if (tbody) {
                if (instList.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding:20px; color:var(--text-light);">No fee installments defined.</td></tr>';
                    return;
                }

                tbody.innerHTML = instList.map(inst => `
                    <tr style="border-bottom: 1px solid var(--border-color); height: 50px;">
                        <td style="padding: 10px 20px; font-weight: 600; color: var(--text-main); font-size: 13px;">Installment ${inst.installment_number}</td>
                        <td style="padding: 10px 20px; color: var(--text-secondary); font-size: 13px;">${inst.due_date}</td>
                        <td style="padding: 10px 20px; font-weight: 600; color: var(--text-main); font-size: 13px;">Rs. ${inst.amount}</td>
                        <td style="padding: 10px 20px; color: var(--text-secondary); font-size: 13px;">Rs. ${inst.paid_amount}</td>
                        <td style="padding: 10px 20px; color: var(--text-secondary); font-size: 13px;">${inst.paid_date || '-'}</td>
                        <td style="padding: 10px 20px;">
                            <span style="font-size: 7.5pt; font-weight: bold; padding: 3px 8px; border-radius: 999px; background-color: ${inst.status === 'PAID' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)'}; color: ${inst.status === 'PAID' ? '#10b981' : '#ef4444'}">${inst.status}</span>
                        </td>
                        <td style="padding: 10px 20px; color: var(--text-muted); font-size: 12px;">${inst.remarks || '-'}</td>
                        <td style="padding: 10px 20px; text-align: center;">
                            <div style="display: flex; gap: 8px; justify-content: center;">
                                ${inst.status !== 'PAID' ? `
                                    <button class="btn btn-primary" style="font-size: 8pt; padding: 4px 8px;" onclick="openRecordPaymentModal(${inst.id})">Record Payment</button>
                                    <button class="btn" style="font-size: 8pt; padding: 4px 8px; background-color: #eab308; color: white;" onclick="triggerWarningEmail(${inst.id})">Send Warning</button>
                                ` : '-'}
                            </div>
                        </td>
                    </tr>
                `).join('');
            }
        }
    } catch (e) {
        console.error(e);
    }
}

// ---------- CERTIFICATES TAB LOGIC ----------
async function loadStudentCertificatesList() {
    if (!currentStudentDetails) return;

    try {
        const res = await apiFetch(`/api/student/certificates/?student_id=${currentStudentDetails.id}`);
        if (res.ok) {
            const list = await res.json();
            const certs = list.results || list;

            const tbody = document.getElementById('studentCertificatesTableBody');
            if (tbody) {
                if (certs.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:20px; color:var(--text-light);">No certificates generated yet.</td></tr>';
                    return;
                }

                tbody.innerHTML = certs.map(c => `
                    <tr style="border-bottom: 1px solid var(--border-color); height: 50px;">
                        <td style="padding: 10px 20px; font-weight: 600; color: var(--text-main); font-size: 13px;">${c.serial_no}</td>
                        <td style="padding: 10px 20px; color: var(--text-secondary); font-size: 13px;">${c.course_name || '-'}</td>
                        <td style="padding: 10px 20px; color: var(--text-secondary); font-size: 13px;">${formatSimpleDate(c.issue_date)}</td>
                        <td style="padding: 10px 20px; color: var(--text-secondary); font-size: 13px;">${c.place || 'Mohali'}</td>
                        <td style="padding: 10px 20px; text-align: center;">
                            ${c.pdf_file ? `
                                <a href="${c.pdf_file}" target="_blank" class="btn" style="font-size: 8pt; padding: 4px 10px; background-color: var(--primary-light); color: var(--primary-color);">📥 Download PDF</a>
                            ` : '-'}
                        </td>
                    </tr>
                `).join('');
            }
        }
    } catch (e) {
        console.error(e);
    }
}

function changeStudentPage(direction) {
    if (direction === 1 && studentDirectoryNext !== null) {
        studentDirectoryStart = studentDirectoryNext;
    } else if (direction === -1) {
        studentDirectoryStart = Math.max(0, studentDirectoryStart - 50);
    }
    loadStudentData();
}

function changeBitrixStudentPage(direction) {
    if (direction === 1 && bitrixStudentNext !== null) {
        bitrixStudentStart = bitrixStudentNext;
    } else if (direction === -1) {
        bitrixStudentStart = Math.max(0, bitrixStudentStart - 50);
    }
    loadBitrixStudents();
}

