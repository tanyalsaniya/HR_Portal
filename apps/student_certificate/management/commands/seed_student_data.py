import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from employee_onboarding.models import Department
from student_certificate.models import Course, Student, StudentFeeInstallment, StudentCertificate
from decimal import Decimal

User = get_user_model()

class Command(BaseCommand):
    help = 'Seeds mock courses, students, installments, and certificate data for testing'

    def handle(self, *args, **options):
        self.stdout.write("Starting data seeding...")
        
        # 1. Ensure a default Department exists
        dept, created = Department.objects.get_or_create(name="Software Engineering")
        if created:
            self.stdout.write(f"Created default department: {dept.name}")
            
        # 2. Ensure a default Admin/User exists
        user = User.objects.filter(is_superuser=True).first()
        if not user:
            user = User.objects.first()
        if not user:
            self.stdout.write("Error: No users found in database. Please run migrations and create a user first.")
            return

        # 3. Seed Courses
        courses_data = [
            {
                "course_name": "Full Stack Web Development",
                "default_duration": "6 months",
                "skills_list": ["HTML/CSS", "JavaScript", "React.js", "Node.js", "Python/Django", "SQL/NoSQL", "Git/GitHub", "Deployment"]
            },
            {
                "course_name": "Data Science & Analytics",
                "default_duration": "6 months",
                "skills_list": ["Python", "Pandas & NumPy", "Data Visualization", "SQL", "Statistical Analysis", "Machine Learning", "Data Wrangling", "Tableau/PowerBI"]
            },
            {
                "course_name": "Quality Assurance & Testing",
                "default_duration": "3 months",
                "skills_list": ["Manual Testing", "Test Planning", "Bug Tracking (Jira)", "Automation (Selenium)", "Python/Java", "API Testing (Postman)", "SQL Basics", "CI/CD Concepts"]
            },
            {
                "course_name": "UI/UX Design",
                "default_duration": "3 months",
                "skills_list": ["Design Thinking", "User Research", "Wireframing", "Prototyping", "Figma", "UI Elements", "Usability Testing", "Information Architecture"]
            }
        ]

        seeded_courses = []
        for c_data in courses_data:
            course, created = Course.objects.get_or_create(
                course_name=c_data["course_name"],
                defaults={
                    "default_duration": c_data["default_duration"],
                    "skills_list": c_data["skills_list"]
                }
            )
            if created:
                self.stdout.write(f"Seeded Course: {course.course_name}")
            seeded_courses.append(course)

        # 4. Seed Students
        today = datetime.date.today()
        students_data = [
            {
                "name": "Aarav Sharma",
                "email": "aarav.sharma@example.com",
                "phone": "9876543210",
                "dob": datetime.date(2003, 5, 14),
                "institute": "Thapar University",
                "course_at_institute": "B.Tech CSE",
                "student_type": "INTERN",
                "program_name": "Full Stack Web Development",
                "department": dept,
                "mentor": "Amit Verma",
                "joining_date": today - datetime.timedelta(days=120),
                "completion_date": today + datetime.timedelta(days=60),
                "project_description": "Developing a secure and optimized portal for internal employee clearance and task tracking.",
                "cert_type": "INTERNSHIP_CERT",
                "status": "ACTIVE",
                "total_fees": Decimal("25000.00"),
                "gender": "MALE",
                "father_name": "Rajesh Sharma",
                "address": "123, Sector 15, Chandigarh",
                "enrolled_course": seeded_courses[0] # Web Dev
            },
            {
                "name": "Diya Patel",
                "email": "diya.patel@example.com",
                "phone": "8765432109",
                "dob": datetime.date(2004, 8, 22),
                "institute": "Nirma University",
                "course_at_institute": "MCA",
                "student_type": "TRAINEE",
                "program_name": "Data Science & Analytics",
                "department": dept,
                "mentor": "Neha Gupta",
                "joining_date": today - datetime.timedelta(days=150),
                "completion_date": today - datetime.timedelta(days=10), # Completed recently
                "project_description": "Building a machine learning model to predict customer churn in SaaS subscription platforms.",
                "cert_type": "TRAINING_CERT",
                "status": "COMPLETED",
                "total_fees": Decimal("30000.00"),
                "gender": "FEMALE",
                "father_name": "Mahesh Patel",
                "address": "456, GIDC Colony, Ahmedabad",
                "enrolled_course": seeded_courses[1] # Data Science
            },
            {
                "name": "Kabir Singh",
                "email": "kabir.singh@example.com",
                "phone": "7654321098",
                "dob": datetime.date(2002, 11, 3),
                "institute": "Chitkara University",
                "course_at_institute": "B.Tech IT",
                "student_type": "PROJECT_STUDENT",
                "program_name": "Quality Assurance & Testing",
                "department": dept,
                "mentor": "Vikram Rathore",
                "joining_date": today - datetime.timedelta(days=45),
                "completion_date": today + datetime.timedelta(days=45),
                "project_description": "Setting up automated regression testing suites for inventory tracking portals using Selenium and Pytest.",
                "cert_type": "PROJECT_CERT",
                "status": "ACTIVE",
                "total_fees": Decimal("15000.00"),
                "gender": "MALE",
                "father_name": "Gurdev Singh",
                "address": "789, Urban Estate, Patiala",
                "enrolled_course": seeded_courses[2] # QA
            },
            {
                "name": "Ananya Sen",
                "email": "ananya.sen@example.com",
                "phone": "6543210987",
                "dob": datetime.date(2003, 1, 30),
                "institute": "IIT Kharagpur",
                "course_at_institute": "B.Des Product Design",
                "student_type": "INTERN",
                "program_name": "UI/UX Design",
                "department": dept,
                "mentor": "Pooja Roy",
                "joining_date": today - datetime.timedelta(days=80),
                "completion_date": today + datetime.timedelta(days=10),
                "project_description": "Redesigning the onboarding checklist mobile application to improve self-onboarding flows.",
                "cert_type": "INTERNSHIP_CERT",
                "status": "ACTIVE",
                "total_fees": Decimal("20000.00"),
                "gender": "FEMALE",
                "father_name": "Sanjay Sen",
                "address": "90, Salt Lake, Kolkata",
                "enrolled_course": seeded_courses[3] # UI/UX
            }
        ]

        for s_data in students_data:
            student, created = Student.objects.get_or_create(
                email=s_data["email"],
                defaults={
                    "name": s_data["name"],
                    "phone": s_data["phone"],
                    "dob": s_data["dob"],
                    "institute": s_data["institute"],
                    "course_at_institute": s_data["course_at_institute"],
                    "student_type": s_data["student_type"],
                    "program_name": s_data["program_name"],
                    "department": s_data["department"],
                    "mentor": s_data["mentor"],
                    "joining_date": s_data["joining_date"],
                    "completion_date": s_data["completion_date"],
                    "project_description": s_data["project_description"],
                    "cert_type": s_data["cert_type"],
                    "status": s_data["status"],
                    "total_fees": s_data["total_fees"],
                    "gender": s_data["gender"],
                    "father_name": s_data["father_name"],
                    "address": s_data["address"],
                    "enrolled_course": s_data["enrolled_course"],
                    "created_by": user
                }
            )
            if created:
                self.stdout.write(f"Seeded Student: {student.name}")
                
                # Seed Fee Installments for this student
                # Divide total_fees into 3 equal installments
                num_installments = 3
                inst_amount = student.total_fees / num_installments
                
                for i in range(1, num_installments + 1):
                    due_date = student.joining_date + datetime.timedelta(days=30 * (i - 1))
                    
                    # Determine status and paid amount based on timing
                    if due_date < today:
                        if i == 1:
                            paid = inst_amount
                            status_val = "PAID"
                            paid_date = due_date + datetime.timedelta(days=2)
                        elif i == 2:
                            paid = inst_amount / 2
                            status_val = "PARTIALLY_PAID"
                            paid_date = due_date + datetime.timedelta(days=5)
                        else:
                            paid = Decimal("0.00")
                            status_val = "UNPAID"
                            paid_date = None
                    else:
                        paid = Decimal("0.00")
                        status_val = "UNPAID"
                        paid_date = None
                        
                    StudentFeeInstallment.objects.create(
                        student=student,
                        installment_number=i,
                        amount=inst_amount,
                        due_date=due_date,
                        paid_amount=paid,
                        paid_date=paid_date,
                        status=status_val,
                        remarks=f"Installment {i} of {num_installments}"
                    )
                self.stdout.write(f"  Created 3 fee installments for {student.name}")
                
                # If completed, seed a student certificate
                if student.status == 'COMPLETED':
                    cert_no = f"CERT-{student.joining_date.year}-000045"
                    
                    cert, created_cert = StudentCertificate.objects.get_or_create(
                        serial_no=cert_no,
                        defaults={
                            "student": student,
                            "course": student.enrolled_course,
                            "skill_ratings": {skill: 4 for skill in student.enrolled_course.skills_list[:4]},
                            "show_dates": True,
                            "issue_date": student.completion_date,
                            "cert_content": "Has successfully completed training course...",
                            "place": "Mohali"
                        }
                    )
                    self.stdout.write(f"  Generated completed certificate {cert.serial_no} for {student.name}")
                    
        self.stdout.write(self.style.SUCCESS("Database seeding completed successfully!"))
