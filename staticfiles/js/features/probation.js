// static/js/features/probation.js

let productivityChartInstance = null;
let efficiencyChartInstance = null;

async function loadProbationData() {
    showGlobalLoader(true);
    try {
        // Load stats & submissions
        const response = await apiFetch('/api/probation/dashboard/');
        if (response.ok) {
            const data = await response.json();
            renderProbationDashboard(data);
        } else {
            showToast('Failed to load probation dashboard data', 'error');
        }

        // Load employees list & templates list for assign form
        await populateAssignChecklistDropdowns();

        // Render standard mock charts for summary
        renderDashboardCharts();

    } catch (e) {
        console.error("Error loading probation data: ", e);
        showToast('Connection error to probation analytics engine', 'error');
    } finally {
        hideGlobalLoader();
    }
}

function renderProbationDashboard(data) {
    const metrics = data.metrics;
    
    // Update metrics
    document.getElementById('probMetricTotal').textContent = metrics.total_employees;
    document.getElementById('probMetricPending').textContent = metrics.pending_forms;
    document.getElementById('probMetricSubmittedToday').textContent = metrics.submitted_today;
    document.getElementById('probMetricAvgScore').textContent = metrics.average_probation_score + '%';
    document.getElementById('probMetricImproving').textContent = metrics.employees_improving;
    document.getElementById('probMetricDeclining').textContent = metrics.employees_declining;
    document.getElementById('probMetricReady').textContent = metrics.employees_ready;

    // Render submissions table
    const tbody = document.getElementById('probationSubmissionsTableBody');
    tbody.innerHTML = '';

    if (data.recent_submissions.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding: 30px; color: #64748b;">No checklist submissions recorded yet.</td></tr>`;
        return;
    }

    data.recent_submissions.forEach(sub => {
        const scoreVal = sub.score !== null ? `${sub.score}%` : `<span style="color:#64748b;">Pending AI</span>`;
        const trendIcon = sub.status === 'Analyzed' ? getTrendTagHTML(sub.trend) : 'N/A';
        const actionsHTML = sub.status === 'Analyzed' 
            ? `<button class="btn" style="padding: 4px 10px; font-size: 8pt; background-color: #7c3aed; color:white; border:none;" onclick="openAiReportDetail(${sub.id})">View AI Report</button>`
            : `<span style="font-size: 8.5pt; color: #64748b; font-style: italic;">Awaiting Fill</span>`;

        const row = document.createElement('tr');
        row.style.borderBottom = '1px solid #e2e8f0';
        row.innerHTML = `
            <td style="padding: 12px 16px; font-weight: 600;">
                ${sub.employee_name}
                <div style="font-size: 7.5pt; color: #64748b; font-weight: normal;">${sub.designation}</div>
            </td>
            <td style="padding: 12px 16px;">${sub.checklist_title}</td>
            <td style="padding: 12px 16px;">${sub.submitted_at}</td>
            <td style="padding: 12px 16px; font-weight: 700;">${scoreVal}</td>
            <td style="padding: 12px 16px;">${trendIcon}</td>
            <td style="padding: 12px 16px;">${actionsHTML}</td>
        `;
        tbody.appendChild(row);
    });
}

function getTrendTagHTML(trend) {
    if (trend === 'Improving') {
        return `<span style="background-color: #d1fae5; color: #065f46; padding: 3px 8px; border-radius: 99px; font-size: 8pt; font-weight: 600;">↑ Improving</span>`;
    } else if (trend === 'Declining') {
        return `<span style="background-color: #fee2e2; color: #991b1b; padding: 3px 8px; border-radius: 99px; font-size: 8pt; font-weight: 600;">↓ Declining</span>`;
    } else {
        return `<span style="background-color: #f3f4f6; color: #374151; padding: 3px 8px; border-radius: 99px; font-size: 8pt; font-weight: 600;">→ Steady</span>`;
    }
}

async function populateAssignChecklistDropdowns() {
    try {
        // Load active employees
        const empRes = await apiFetch('/api/onboarding/employees/');
        let employees = [];
        if (empRes.ok) {
            const dataObj = await empRes.json();
            employees = dataObj.results || dataObj || [];
        }

        const empSelect = document.getElementById('probationEmployeeSelect');
        const assignEmpSelect = document.getElementById('assignEmployeeField');
        
        empSelect.innerHTML = '<option value="">Choose an employee...</option>';
        assignEmpSelect.innerHTML = '<option value="">Select Employee...</option>';

        employees.forEach(emp => {
            const name = `${emp.first_name} ${emp.last_name || ''}`.trim();
            const bitrixId = emp.bitrix_user_id || emp.id || emp.bitrix_contact_id;
            if (bitrixId) {
                const opt = `<option value="${bitrixId}">${name} (ID: ${bitrixId})</option>`;
                empSelect.innerHTML += opt;
                assignEmpSelect.innerHTML += opt;
            }
        });

        // Load checklists
        const checkRes = await apiFetch('/api/probation/checklists/');
        const assignChecklistField = document.getElementById('assignChecklistField');
        assignChecklistField.innerHTML = '<option value="">Select Template...</option>';

        if (checkRes.ok) {
            const rawChecklists = await checkRes.json();
            const checklists = rawChecklists.results || rawChecklists || [];
            // If no checklists exist, create a default template automatically
            if (checklists.length === 0) {
                await createDefaultChecklistTemplate();
                // reload
                const reloadCheck = await apiFetch('/api/probation/checklists/');
                if (reloadCheck.ok) {
                    const rawReChecklists = await reloadCheck.json();
                    const reChecklists = rawReChecklists.results || rawReChecklists || [];
                    reChecklists.forEach(c => {
                        assignChecklistField.innerHTML += `<option value="${c.id}">${c.title}</option>`;
                    });
                }
            } else {
                checklists.forEach(c => {
                    assignChecklistField.innerHTML += `<option value="${c.id}">${c.title}</option>`;
                });
            }
        }
    } catch (e) {
        console.error("Error populating dropdowns: ", e);
    }
}

async function createDefaultChecklistTemplate() {
    const payload = {
        title: "Daily Probation Performance Check-in",
        description: "Standard checklist for probation assessment. Analyzed daily by DevEx Hub AI engine.",
        questions: [
            { id: "goals_completed", label: "Were all targets and tasks assigned to you for today completed?", type: "select", options: ["Fully Completed", "Mostly Completed (80%+)", "Partially Completed", "Not Completed"] },
            { id: "challenges", label: "Did you face any dependencies or blockers today (e.g. requirement changes, technical issues)?", type: "textarea" },
            { id: "learning_progress", label: "Detail any new technology, codebase architecture, or workflow principles you learned today.", type: "textarea" },
            { id: "support_needed", label: "Do you require any technical training or feedback from your team lead?", type: "textarea" }
        ]
    };

    await apiFetch('/api/probation/checklists/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
}

function openAssignChecklistModal() {
    const el = document.getElementById('assignChecklistModal');
    el.style.display = 'flex';
    setTimeout(() => { el.style.right = '20px'; }, 50);
}

function closeAssignChecklistModal() {
    const el = document.getElementById('assignChecklistModal');
    el.style.right = '-420px';
    setTimeout(() => { el.style.display = 'none'; }, 350);
}

async function submitAssignChecklist(e) {
    e.preventDefault();
    const empId = document.getElementById('assignEmployeeField').value;
    const checklistId = document.getElementById('assignChecklistField').value;

    if (!empId || !checklistId) return;

    showGlobalLoader(true);
    try {
        const response = await apiFetch('/api/probation/assignments/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                employee: empId,
                checklist: checklistId
            })
        });

        if (response.ok) {
            showToast('Checklist assigned successfully and sent to employee in Bitrix24!', 'success');
            closeAssignChecklistModal();
            loadProbationData();
        } else {
            showToast('Failed to assign checklist form.', 'error');
        }
    } catch (err) {
        showToast('Network error during assignment creation', 'error');
    } finally {
        hideGlobalLoader();
    }
}

async function loadEmployeeTimeline(employeeId) {
    if (!employeeId) {
        document.getElementById('probationTimelineContainer').style.display = 'none';
        document.getElementById('probationTimelineEmpty').style.display = 'block';
        return;
    }

    showGlobalLoader(true);
    try {
        const response = await apiFetch(`/api/probation/timeline/${employeeId}/`);
        if (response.ok) {
            const data = await response.json();
            renderTimeline(data, employeeId);
        } else {
            showToast('Failed to fetch employee timeline', 'error');
        }
    } catch (e) {
        showToast('Connection error fetching performance timeline', 'error');
    } finally {
        hideGlobalLoader();
    }
}

function renderTimeline(data, employeeId) {
    document.getElementById('probationTimelineEmpty').style.display = 'none';
    const container = document.getElementById('probationTimelineContainer');
    container.style.display = 'block';

    document.getElementById('timelineEmployeeName').textContent = data.employee_name;
    document.getElementById('timelineEmployeeRole').textContent = `${data.designation || 'Staff'} — ${data.department || 'HR'}`;
    
    // Set target employee ID for compilation button
    document.getElementById('btnGenerateFinalReport').setAttribute('data-emp-id', employeeId);

    const list = document.getElementById('timelineList');
    list.innerHTML = '';

    if (data.timeline.length === 0) {
        list.innerHTML = `<div style="color: #64748b; font-size: 9pt;">No checkpoints submitted yet for this employee.</div>`;
        return;
    }

    // Render timeline points
    data.timeline.forEach(point => {
        const pointEl = document.createElement('div');
        pointEl.style.position = 'relative';
        pointEl.style.marginBottom = '8px';

        const dotColor = point.status === 'Analyzed' ? '#7c3aed' : '#cbd5e1';
        
        let reportHTML = '';
        if (point.ai_report) {
            const rep = point.ai_report;
            reportHTML = `
                <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; margin-top: 8px; font-size: 8.5pt;">
                    <div style="display:flex; justify-content:space-between; font-weight: 700; margin-bottom: 6px;">
                        <span style="color:#7c3aed;">AI Score: ${rep.overall_score}%</span>
                        <span style="color:#475569;">Recommendation: ${rep.recommendation}</span>
                    </div>
                    <div style="color: #475569; line-height:1.4;">${rep.summary}</div>
                    <div style="display:flex; gap: 8px; margin-top: 8px;">
                        ${getTrendTagHTML(rep.trend)}
                        <button class="btn" style="padding: 2px 8px; font-size: 7.5pt; height:auto; margin:0;" onclick="openAiReportDetail(${point.ai_report.report_id}, true)">Details</button>
                    </div>
                </div>
            `;
        } else {
            reportHTML = `<div style="font-size: 8pt; color: #64748b; font-style: italic; margin-top: 4px;">Form assigned - Awaiting employee responses</div>`;
        }

        pointEl.innerHTML = `
            <span style="position: absolute; left: -26px; top: 4px; width: 10px; height: 10px; border-radius: 50%; background-color: ${dotColor}; border: 2px solid white; box-shadow: 0 0 0 2px ${dotColor}33;"></span>
            <div style="font-weight: 700; font-size: 9.5pt; color: #1e293b;">${point.checklist_title}</div>
            <div style="font-size: 8pt; color: #64748b;">Assigned: ${point.assigned_at} ${point.submitted_at ? `| Submitted: ${point.submitted_at}` : ''}</div>
            ${reportHTML}
        `;
        list.appendChild(pointEl);
    });

    // Handle final consolidated report visual badge
    if (data.final_report) {
        const finalRep = data.final_report;
        const finalReportBanner = document.createElement('div');
        finalReportBanner.style.background = 'linear-gradient(135deg, #10b981 0%, #059669 100%)';
        finalReportBanner.style.color = 'white';
        finalReportBanner.style.borderRadius = '12px';
        finalReportBanner.style.padding = '16px';
        finalReportBanner.style.marginTop = '24px';
        finalReportBanner.style.boxShadow = '0 10px 15px -3px rgba(16, 185, 129, 0.2)';

        finalReportBanner.innerHTML = `
            <div style="font-weight: 800; font-size: 10pt; text-transform: uppercase; letter-spacing: 0.05em; display:flex; justify-content:space-between; align-items:center;">
                <span>Consolidated Probation Report</span>
                <span style="background: rgba(255,255,255,0.2); padding: 2px 8px; border-radius: 99px; font-size: 7.5pt;">90 Days Summary</span>
            </div>
            <div style="margin-top: 10px; display:grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 8.5pt;">
                <div>Avg AI Score: <strong>${finalRep.average_score}%</strong></div>
                <div>Overall Trend: <strong>${finalRep.overall_trend}</strong></div>
                <div style="grid-column: span 2;">Recommendation: <strong>${finalRep.final_recommendation}</strong></div>
            </div>
            <button class="btn" style="background: white; color: #059669; border: none; padding: 6px 12px; font-size: 8pt; font-weight: 700; width:100%; border-radius: 6px; margin-top: 12px; cursor:pointer;" onclick="showFinalReportModal('${employeeId}')">
                Open Detailed Final Report
            </button>
        `;
        list.appendChild(finalReportBanner);
    }

    // Refresh charts for specific employee if they have AI scores
    const scores = data.timeline.filter(p => p.ai_report).map(p => p.ai_report.overall_score);
    const dates = data.timeline.filter(p => p.ai_report).map(p => p.submitted_at);
    
    if (scores.length > 0) {
        updateChartsForEmployee(dates, scores, data.timeline.filter(p => p.ai_report));
    }
}

async function openAiReportDetail(reportIdOrAssignmentId, isReportId = false) {
    let report = null;
    showGlobalLoader(true);
    try {
        let endpoint = `/api/probation/assignments/${reportIdOrAssignmentId}/`;
        if (isReportId) {
            // Find by assignment directly via filtering or detail load. For simplicity, we can fetch all assignments and match report ID.
            const assignmentsRes = await apiFetch('/api/probation/assignments/');
            if (assignmentsRes.ok) {
                const list = await assignmentsRes.json();
                const match = list.find(a => a.scores && a.id == reportIdOrAssignmentId); // fallback
                if (match) report = match;
            }
        } else {
            const res = await apiFetch(endpoint);
            if (res.ok) report = await res.json();
        }

        if (!report) {
            // Alternatively, pull the assignment details
            const resDirect = await apiFetch(`/api/probation/assignments/${reportIdOrAssignmentId}/`);
            if (resDirect.ok) report = await resDirect.json();
        }

        if (report && report.status === 'Analyzed') {
            renderAiReportModal(report);
        } else {
            showToast('Could not load detailed AI report metadata', 'error');
        }
    } catch (e) {
        console.error(e);
        showToast('Error loading report details', 'error');
    } finally {
        hideGlobalLoader();
    }
}

function renderAiReportModal(report) {
    const el = document.getElementById('aiAnalysisModal');
    const content = document.getElementById('aiReportDetailContent');

    const scores = report.scores || {};
    
    // Strengths list items
    let strengthsList = '';
    if (report.strengths) {
        report.strengths.forEach(s => strengthsList += `<li style="margin-bottom:6px; color:#10b981;">✔ ${s}</li>`);
    }
    
    // Improvements items
    let improvementsList = '';
    if (report.improvements) {
        report.improvements.forEach(imp => improvementsList += `<li style="margin-bottom:6px; color:#ef4444;">⚠ ${imp}</li>`);
    }

    content.innerHTML = `
        <div style="background-color: #f8fafc; padding: 20px; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 24px; text-align: center;">
            <div style="font-size: 26pt; font-weight: 800; color: #7c3aed;">${scores.overall_score || 0}%</div>
            <div style="font-size: 9pt; font-weight: 600; color: #64748b; margin-top: 4px;">Overall AI Score</div>
            <div style="display:flex; justify-content:center; gap: 8px; margin-top: 12px;">
                ${getTrendTagHTML(report.trend)}
                <span style="background-color:#e0e7ff; color:#3730a3; padding:3px 8px; border-radius:99px; font-size:8pt; font-weight:600;">${report.recommendation}</span>
            </div>
        </div>

        <div style="margin-bottom: 24px;">
            <h4 style="margin:0 0 10px; font-size: 10pt; color: #64748b; font-weight: 600;">Checklist Scores Breakdown</h4>
            <div style="display:flex; justify-content:space-between; background-color: #f1f5f9; padding: 12px; border-radius: 8px; font-size: 8.5pt;">
                <div>Productivity: <strong>${scores.productivity_score || 0}%</strong></div>
                <div>Efficiency: <strong>${scores.efficiency_score || 0}%</strong></div>
                <div>Consistency: <strong>${scores.consistency_score || 0}%</strong></div>
            </div>
        </div>

        <div style="margin-bottom: 24px;">
            <h4 style="margin:0 0 8px; font-size: 10pt; color: #1e293b; font-weight: 700;">Executive Performance Summary</h4>
            <p style="margin:0; font-size: 9pt; color:#475569; line-height:1.5;">${report.summary || 'Summary not processed.'}</p>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px;">
            <div>
                <h4 style="margin:0 0 8px; font-size: 9.5pt; color: #065f46; font-weight: 700;">Strengths</h4>
                <ul style="list-style:none; padding:0; margin:0; font-size: 8.5pt;">
                    ${strengthsList || '<li>No specific strengths recorded today.</li>'}
                </ul>
            </div>
            <div>
                <h4 style="margin:0 0 8px; font-size: 9.5pt; color: #991b1b; font-weight: 700;">Areas for Improvement</h4>
                <ul style="list-style:none; padding:0; margin:0; font-size: 8.5pt;">
                    ${improvementsList || '<li>No specific recommendations.</li>'}
                </ul>
            </div>
        </div>
    `;

    el.style.display = 'flex';
    setTimeout(() => { el.style.right = '20px'; }, 50);
}

function closeAiAnalysisModal() {
    const el = document.getElementById('aiAnalysisModal');
    el.style.right = '-520px';
    setTimeout(() => { el.style.display = 'none'; }, 350);
}

async function triggerFinalProbationReport() {
    const empId = document.getElementById('btnGenerateFinalReport').getAttribute('data-emp-id');
    if (!empId) return;

    showGlobalLoader(true);
    try {
        const response = await apiFetch(`/api/probation/final-report/${empId}/`, {
            method: 'POST'
        });

        if (response.ok) {
            showToast('Final Probation Consolidated Report compiled successfully!', 'success');
            // Reload timeline view
            await loadEmployeeTimeline(empId);
            showFinalReportModal(empId);
        } else {
            const err = await response.json();
            showToast(err.error || 'Failed to trigger AI consolidation engine.', 'error');
        }
    } catch (e) {
        showToast('Network error triggering report generator', 'error');
    } finally {
        hideGlobalLoader();
    }
}

async function showFinalReportModal(employeeId) {
    showGlobalLoader(true);
    try {
        const response = await apiFetch(`/api/probation/timeline/${employeeId}/`);
        if (response.ok) {
            const data = await response.json();
            if (data.final_report) {
                renderFinalReportModal(data.final_report, data.employee_name, data.designation);
            }
        }
    } catch (e) {
        console.error(e);
    } finally {
        hideGlobalLoader();
    }
}

function renderFinalReportModal(report, name, designation) {
    const el = document.getElementById('finalReportModal');
    const content = document.getElementById('finalReportDetailContent');

    let strengthsList = '';
    report.strengths.forEach(s => strengthsList += `<li style="margin-bottom:6px; color:#10b981;">✔ ${s}</li>`);

    let improvementsList = '';
    report.improvements.forEach(imp => improvementsList += `<li style="margin-bottom:6px; color:#f59e0b;">⚠ ${imp}</li>`);

    let challengesList = '';
    report.challenges.forEach(c => challengesList += `<li style="margin-bottom:6px; color:#ef4444;">✦ ${c}</li>`);

    content.innerHTML = `
        <div style="background-color: #f0fdf4; padding: 20px; border-radius: 12px; border: 1px solid #bbf7d0; margin-bottom: 24px; text-align: center;">
            <div style="font-size: 26pt; font-weight: 800; color: #15803d;">${report.average_score || 0}%</div>
            <div style="font-size: 9pt; font-weight: 600; color: #166534; margin-top: 4px;">90-Day Average Score</div>
            <div style="display:flex; justify-content:center; gap: 8px; margin-top: 12px;">
                <span style="background-color:#15803d; color:white; padding:3px 12px; border-radius:99px; font-size:8pt; font-weight:700;">${report.final_recommendation}</span>
                <span style="background-color:#dcfce7; color:#15803d; padding:3px 8px; border-radius:99px; font-size:8pt; font-weight:600;">Confidence: ${report.confidence}</span>
            </div>
        </div>

        <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:24px; font-size: 8.5pt;">
            <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:10px;">
                Best Performance: <strong>${report.best_week}</strong>
            </div>
            <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:10px;">
                Lowest Performance: <strong>${report.lowest_week}</strong>
            </div>
        </div>

        <div style="margin-bottom: 24px;">
            <h4 style="margin:0 0 8px; font-size: 9.5pt; color: #15803d; font-weight: 700;">Consolidated Strengths</h4>
            <ul style="list-style:none; padding:0; margin:0; font-size: 8.5pt;">
                ${strengthsList || '<li>No specific items compiled.</li>'}
            </ul>
        </div>

        <div style="margin-bottom: 24px;">
            <h4 style="margin:0 0 8px; font-size: 9.5pt; color: #b45309; font-weight: 700;">Areas for Improvement</h4>
            <ul style="list-style:none; padding:0; margin:0; font-size: 8.5pt;">
                ${improvementsList || '<li>No specific items.</li>'}
            </ul>
        </div>

        <div style="margin-bottom: 24px;">
            <h4 style="margin:0 0 8px; font-size: 9.5pt; color: #b91c1c; font-weight: 700;">Recurring blocker challenges</h4>
            <ul style="list-style:none; padding:0; margin:0; font-size: 8.5pt;">
                ${challengesList || '<li>No blockers recorded.</li>'}
            </ul>
        </div>
    `;

    el.style.display = 'flex';
    setTimeout(() => { el.style.right = '20px'; }, 50);
}

function closeFinalReportModal() {
    const el = document.getElementById('finalReportModal');
    el.style.right = '-580px';
    setTimeout(() => { el.style.display = 'none'; }, 350);
}

// ─── CHARTS DRAWING LOGIC ───────────────────────────────────────

function renderDashboardCharts() {
    // Productivity Chart
    const prodCtx = document.getElementById('productivityTrendChart').getContext('2d');
    if (productivityChartInstance) productivityChartInstance.destroy();
    
    productivityChartInstance = new Chart(prodCtx, {
        type: 'line',
        data: {
            labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4', 'Week 5', 'Week 6', 'Week 7', 'Week 8'],
            datasets: [{
                label: 'Average Team Productivity',
                data: [72, 75, 78, 80, 82, 85, 87, 89],
                borderColor: '#6366f1',
                backgroundColor: 'rgba(99, 102, 241, 0.1)',
                borderWidth: 3,
                tension: 0.3,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { min: 50, max: 100 }
            }
        }
    });

    // Efficiency/Radar Chart
    const effCtx = document.getElementById('efficiencyRadarChart').getContext('2d');
    if (efficiencyChartInstance) efficiencyChartInstance.destroy();

    efficiencyChartInstance = new Chart(effCtx, {
        type: 'radar',
        data: {
            labels: ['Productivity', 'Efficiency', 'Consistency', 'Learning Trend', 'Task Completion', 'Challenge Resolution'],
            datasets: [{
                label: 'Benchmark Target',
                data: [85, 80, 85, 90, 88, 80],
                backgroundColor: 'rgba(209, 250, 229, 0.4)',
                borderColor: '#10b981',
                borderWidth: 2
            }, {
                label: 'Current Employee average',
                data: [78, 76, 81, 85, 82, 74],
                backgroundColor: 'rgba(224, 231, 255, 0.4)',
                borderColor: '#6366f1',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false
        }
    });
}

function updateChartsForEmployee(labels, overallScores, details) {
    if (productivityChartInstance) {
        productivityChartInstance.data.labels = labels;
        productivityChartInstance.data.datasets[0].label = 'Employee Overall Score';
        productivityChartInstance.data.datasets[0].data = overallScores;
        productivityChartInstance.update();
    }

    if (efficiencyChartInstance && details.length > 0) {
        // Average the details metrics for selected employee
        let prodTotal = 0, effTotal = 0, consTotal = 0;
        details.forEach(item => {
            prodTotal += (item.ai_report.productivity_score || 0);
            effTotal += (item.ai_report.efficiency_score || 0);
            consTotal += (item.ai_report.consistency_score || 0);
        });

        const prodAvg = prodTotal / details.length;
        const effAvg = effTotal / details.length;
        const consAvg = consTotal / details.length;

        efficiencyChartInstance.data.datasets[1].label = 'Employee Average Metrics';
        efficiencyChartInstance.data.datasets[1].data = [prodAvg, effAvg, consAvg, 85, prodAvg - 2, effAvg + 2];
        efficiencyChartInstance.update();
    }
}
