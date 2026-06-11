# rules.py
# Central configuration file for business logic, validation limits, and system rules.

# ---------- ROLES & ACCESS CONTROL ----------
ROLE_ADMIN = 'ADMIN'
ROLE_HR = 'HR'
ROLE_MANAGEMENT = 'MANAGEMENT'

ROLE_CHOICES = (
    (ROLE_ADMIN, 'Admin'),
    (ROLE_HR, 'HR'),
    (ROLE_MANAGEMENT, 'Management Member'),
)

# ---------- EMPLOYEE ONBOARDING VALIDATIONS ----------
MIN_EMPLOYMENT_AGE = 18
MAX_FUTURE_JOINING_DAYS = 30
DEFAULT_NOTICE_PERIOD_DAYS = 30

GENDER_CHOICES = (
    ('MALE', 'Male'),
    ('FEMALE', 'Female'),
    ('OTHER', 'Other'),
    ('PREFER_NOT', 'Prefer not to say'),
)

EMPLOYMENT_TYPE_CHOICES = (
    ('FULL_TIME', 'Full-time'),
    ('PART_TIME', 'Part-time'),
    ('CONTRACT', 'Contract'),
    ('INTERN', 'Intern'),
)

EMERGENCY_RELATION_CHOICES = (
    ('SPOUSE', 'Spouse'),
    ('PARENT', 'Parent'),
    ('SIBLING', 'Sibling'),
    ('FRIEND', 'Friend'),
    ('OTHER', 'Other'),
)

# ---------- DOCUMENT UPLOADS & FILE LIMITS ----------
MAX_DOCUMENT_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_PROFILE_PHOTO_SIZE_BYTES = 2 * 1024 * 1024  # 2 MB

VALID_DOC_TYPES = (
    ('RESUME', 'Resume'),
    ('AADHAAR', 'Aadhaar'),
    ('PAN', 'PAN'),
    ('OFFER_LETTER', 'Offer Letter'),
    ('APPOINTMENT_LETTER', 'Appointment Letter'),
    ('BOND_LETTER', 'Bond Letter'),
    ('OTHER', 'Other'),
)

# ---------- EXIT PROCESS RULES ----------
EXIT_LINK_EXPIRY_DAYS = 7
MIN_REASON_CHARACTERS = 20

EXIT_TYPE_CHOICES = (
    ('RESIGNATION', 'Resignation'),
    ('TERMINATION', 'Termination'),
    ('RETIREMENT', 'Retirement'),
    ('CONTRACT_END', 'Contract End'),
    ('ABSCONDING', 'Absconding'),
)

KT_STATUS_CHOICES = (
    ('COMPLETED', 'Completed'),
    ('IN_PROGRESS', 'In Progress'),
    ('NA', 'Not Applicable'),
)

EXIT_STATUS_CHOICES = (
    ('PENDING', 'Pending'),
    ('IN_PROGRESS', 'In Progress'),
    ('COMPLETED', 'Completed'),
)

# ---------- SALARY INCREMENT NOTIFICATIONS ----------
INCREMENT_LEAD_DAYS = 15
INCREMENT_REPEAT_DAYS = [15, 7, 0]  # Days before anniversary to send reminders

# ---------- STUDENT / INTERN CERTIFICATE RULES ----------
STUDENT_TYPE_CHOICES = (
    ('INTERN', 'Intern'),
    ('TRAINEE', 'Trainee'),
    ('PROJECT_STUDENT', 'Project Student'),
    ('INDUSTRIAL_VISIT', 'Industrial Visit'),
)

CERTIFICATE_TYPE_CHOICES = (
    ('INTERNSHIP_CERT', 'Internship Certificate'),
    ('TRAINING_CERT', 'Training Completion Certificate'),
    ('PROJECT_CERT', 'Project Completion Certificate'),
)

STUDENT_STATUS_CHOICES = (
    ('ACTIVE', 'Active'),
    ('COMPLETED', 'Completed'),
    ('DISCONTINUED', 'Discontinued'),
)

INSTALLMENT_STATUS_CHOICES = (
    ('UNPAID', 'Unpaid'),
    ('PAID', 'Paid'),
    ('PARTIALLY_PAID', 'Partially Paid'),
)

# ---------- INDIAN STATES MASTER LIST ----------
INDIAN_STATES = (
    ('AP', 'Andhra Pradesh'),
    ('AR', 'Arunachal Pradesh'),
    ('AS', 'Assam'),
    ('BR', 'Bihar'),
    ('CG', 'Chhattisgarh'),
    ('GA', 'Goa'),
    ('GJ', 'Gujarat'),
    ('HR', 'Haryana'),
    ('HP', 'Himachal Pradesh'),
    ('JH', 'Jharkhand'),
    ('KA', 'Karnataka'),
    ('KL', 'Kerala'),
    ('MP', 'Madhya Pradesh'),
    ('MH', 'Maharashtra'),
    ('MN', 'Manipur'),
    ('ML', 'Meghalaya'),
    ('MZ', 'Mizoram'),
    ('NL', 'Nagaland'),
    ('OD', 'Odisha'),
    ('PB', 'Punjab'),
    ('RJ', 'Rajasthan'),
    ('SK', 'Sikkim'),
    ('TN', 'Tamil Nadu'),
    ('TG', 'Telangana'),
    ('TR', 'Tripura'),
    ('UP', 'Uttar Pradesh'),
    ('UK', 'Uttarakhand'),
    ('WB', 'West Bengal'),
    ('DL', 'Delhi'),
    ('JK', 'Jammu & Kashmir'),
    ('PY', 'Puducherry'),
)

# ---------- STUDENT FEES OVERDUE EMAIL TEMPLATE ----------
STUDENT_FEES_WARNING_SUBJECT = "Action Required: Pending Fee Installment Payment"
STUDENT_FEES_WARNING_BODY = """Dear {student_name},

This is a reminder regarding your training program at MTLV. Our records indicate that your fee installment number {installment_number} of Rs. {amount:.2f} was due on {due_date}. 

As of today, we have not received the payment. Please process this installment as soon as possible. If you have already paid, please contact the HR department with the receipt to update your status.

If you have any questions or require assistance, please contact the HR office.

Sincerely,
HR Department
MTLV Development Team
"""
