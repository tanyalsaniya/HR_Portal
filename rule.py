# rule.py
# Alias for rules.py - imports all centralized business logic rules, validations, and choices.
# This file also documents the core rules and configurations followed during the implementation.

from rules import *

# ==============================================================================
#                      RULES WE FOLLOWED (DOCUMENTATION)
# ==============================================================================
# Below is a detailed summary of the rules, constraints, and business logic 
# implemented in the MTLV HR Portal V2.0 codebase.
#
# 1. ROLE-BASED ACCESS CONTROL (RBAC)
#    - Super Admin: Full permissions across all modules, including:
#      * Creating and modifying HR user accounts.
#      * Approving salary revisions/increments.
#      * Deleting employee or student records (soft-deletion).
#      * Viewing system-wide audit logs.
#    - HR Role: Restricted access. HR performs daily operations (onboarding, 
#      generating slips, managing exits, adding students), but cannot:
#      * Access Admin settings or view full audit logs.
#      * Approve salary increments.
#      * Hard-delete or soft-delete records.
#
# 2. DATA ENCRYPTION (REVERSIBLE AES-256)
#    - To comply with security requirements, sensitive data is encrypted at-rest 
#      in the PostgreSQL database, but must remain reversible so that authorized 
#      Admin/HR users can view and use the values for letters, calculations, and slip printing.
#    - Encrypted fields:
#      * Employee Aadhaar Number (EncryptedCharField)
#      * Employee PAN Number (EncryptedCharField)
#      * Employee Salary Components: Basic, HRA, Special Allowance, Gross (EncryptedDecimalField)
#    - Implementation uses Fernet cryptography symmetric cipher with a 32-byte secret key.
#
# 3. SEQUENTIAL UNIQUE ID GENERATION
#    - Employee ID format: EMP-YYYY-XXXX (e.g. EMP-2026-0001), resetting annually.
#    - Payslip Reference format: PS-YYYY-MM-XXXX (e.g. PS-2026-06-0012).
#    - Student Certificate Reference format: CERT-YYYY-XXXXXX (e.g. CERT-2026-000045).
#
# 4. EMPLOYEE ONBOARDING VALIDATIONS
#    - Minimum employment age: 18 years.
#    - Future joining date: Allowed up to 30 days in advance.
#    - Document uploads: Must upload Resume, Aadhaar, and PAN.
#    - Letter Generation: Automated PDF generation via WeasyPrint using standard templates:
#      * Offer Letter
#      * Appointment Letter
#      * Bond Letter / Notice Period Agreement
#
# 5. EXIT & Clearance Workflows
#    - HR initiates exits by specifying the resignation date.
#    - System calculates the last working day automatically based on notice period.
#    - Secure Token Link: A unique, secure UUID link is generated and sent to the employee.
#      * Expiry: Link is valid for exactly 7 days.
#      * Form: The questionnaire is a public page requiring no user login.
#      * On submission, status changes to Completed, and relieving/experience letters are unlocked.
#
# 6. EX-EMPLOYEE & REJOINING FLOW
#    - Allows searching ex-employees.
#    - Ex-employees can be re-onboarded under a new tenure.
#    - A fresh Employee ID and fresh tenure sequence are created, but historical records 
#      (documents, previous tenure contracts, payslips) are preserved and linked.
#
# 7. LOSS OF PAY (LOP) PAYSLIP CALCULATIONS
#    - Deductions are computed dynamically:
#      * LOP Deduction = (Gross Salary / Total Month Days) * (Total Month Days - Actual Worked Days).
#      * Net Salary = Gross Salary - LOP Deduction - PF/TDS/PT (if configured).
#    - Generates A4 size print-ready PDF payslips on approval.
#
# 8. SALARY INCREMENT NOTIFICATION & APPROVAL FLOW
#    - Automated anniversary check: Runs daily via celery scheduler tasks.
#    - Evaluates employees approaching 1 year from their joining date.
#    - Notifications sent to HR & Admin 15 days in advance (and repeated at -7 and 0 days).
#    - Admin Approval Required: HR cannot approve salary increases. An Admin must review 
#      and approve the revision for the new payroll structure to take effect.
#
# 9. STUDENT CERTIFICATES & FEES INSTALLMENTS
#    - Tracks student training, fees structure, and due installment schedules.
#    - Automated Fee Checkers: Overdue payment reminders sent to students and notifications logged for HR.
#    - Administrative tools: Export student lists to Excel, compile completion certificates in bulk ZIPs.
#
# 10. SYSTEM-WIDE AUDIT LOGGING
#     - System-wide logging tracks all CRUD actions using Django signals.
#     - Keeps immutable records of who performed which action on what model with a timestamp.
#     - Visible only to Super Admins.
