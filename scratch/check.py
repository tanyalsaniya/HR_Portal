import re
with open('templates/salary/salary_panel.html', 'r', encoding='utf-8') as f:
    html = f.read()

m = re.search(r'(<div id="salaryTabDismissed".*?)(?=<!-- MODAL 5: DEFINE SALARY STRUCTURE -->)', html, re.DOTALL)
if m:
    print(m.group(1))
else:
    print('Not found')
