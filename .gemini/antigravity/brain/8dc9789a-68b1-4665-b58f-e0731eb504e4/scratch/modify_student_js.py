# C:\Users\Pc\.gemini\antigravity\brain\8dc9789a-68b1-4665-b58f-e0731eb504e4\scratch\modify_student_js.py
import os

def main():
    filepath = r"C:\Users\Pc\Documents\Python\HR_Portal\static\js\features\student.js"
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    target = """async function loadStudentData() {
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
                    tbody.innerHTML = '<tr><td colspan="9" style="text-align:center; padding:30px; color:#64748b;">No ongoing students found.</td></tr>';
                    // Update pagination controls
                    updateStudentDirectoryPagination(0);
                    return;
                }
                
                tbody.innerHTML = studList.map((s, index) => `
                    <tr onclick="handleStudentRowClick(event, ${index})" style="cursor: pointer;">
                        <td>-</td>
                        <td>${s.name || '-'}</td>
                        <td>${s.email || '-'}</td>
                        <td>Student</td>
                        <td>${s.start_date || '-'}</td>
                        <td>${s.completion_date || '-'}</td>
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
}"""

    replacement = """async function loadStudentData() {
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
}"""

    if target in content:
        content = content.replace(target, replacement)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Replacement successful!")
    else:
        print("Target string not found in student.js!")

if __name__ == '__main__':
    main()
