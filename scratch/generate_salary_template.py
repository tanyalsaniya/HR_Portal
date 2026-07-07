import openpyxl

headers = [
    "Sr. No.", "Name", "Designation", "Month days", "Worked days", 
    "Weekend", "CL", "Extra", "Payable Days", "Month Salary", 
    "Payable Salary", "Extra days working", "Fine/Advance", "Net Payable", 
    "Bank A/c No.", "Bank"
]

wb = openpyxl.Workbook()
ws = wb.active
ws.title = "Salary Template"
ws.append(headers)

# Adding a dummy row as an example
ws.append([
    1, "John Doe", "Software Engineer", 30, 20, 
    8, 1, 1, 30, 50000, 
    50000, 0, 0, 50000, 
    "1234567890", "HDFC Bank"
])

wb.save('scratch/Salary_Import_Template.xlsx')
print("Template created at scratch/Salary_Import_Template.xlsx")
