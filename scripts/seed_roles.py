# scripts/seed_roles.py
import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from employee_onboarding.models import Department
from django.contrib.auth import get_user_model
from roles.models import Role, Permission

def seed_database():
    print("1. Seeding default departments...")
    departments = [
        "Human Resources",
        "Information Technology",
        "Finance & Accounts",
        "Software Engineering",
        "UI/UX Design",
        "Sales & Marketing",
        "Operations"
    ]
    for name in departments:
        dept, created = Department.objects.get_or_create(name=name)
        if created:
            print(f"  Created department: {name}")

    print("\n2. Seeding dynamic permissions...")
    permissions_data = [
        # Onboarding
        ("View Employees", "onboarding.read", "onboarding"),
        ("Onboard New Employee", "onboarding.create", "onboarding"),
        ("Edit Employee Details", "onboarding.update", "onboarding"),
        ("Deactivate Employee", "onboarding.delete", "onboarding"),
        ("Download Onboarding Letters", "onboarding.generate_letters", "onboarding"),
        # Salary & Slips
        ("View Payroll Details", "salary.read", "salary"),
        ("Generate Slips & Setup Structure", "salary.create_slips", "salary"),
        ("Approve Salary Increments", "salary.approve_increments", "salary"),
        # Exits
        ("View Exits Directory", "exit.read", "exit"),
        ("Initiate Exits", "exit.create", "exit"),
        ("Update Exit Checklists", "exit.update", "exit"),
        ("Delete Exit Requests", "exit.delete", "exit"),
        ("Download Exit Letters", "exit.generate_letters", "exit"),
        ("Re-join Ex-Employees", "exit.rejoin", "exit"),
        # Students
        ("View Students List", "student.read", "student"),
        ("Add Students / Interns", "student.create", "student"),
        ("Log Fees Installments", "student.update", "student"),
        ("Delete Students List", "student.delete", "student"),
        ("Export Data & Bulk Certificates", "student.export", "student"),
        # Logs
        ("View System Audit Logs", "audit.read", "audit"),
        # RBAC
        ("Manage Roles & Permissions", "roles.manage", "roles"),
    ]

    all_permission_objs = []
    for name, codename, module in permissions_data:
        perm, created = Permission.objects.get_or_create(
            codename=codename,
            defaults={"name": name, "module": module}
        )
        all_permission_objs.append(perm)
        if created:
            print(f"  Created permission: {codename}")

    print("\n3. Seeding system roles...")
    # Create ADMIN role
    admin_role, created_admin = Role.objects.get_or_create(
        code="ADMIN",
        defaults={"name": "Super Admin", "is_system": True}
    )
    if created_admin:
        admin_role.permissions.set(all_permission_objs)
        print("  Created ADMIN role with all permissions.")
    else:
        # Sync all permissions for admin just in case
        admin_role.permissions.set(all_permission_objs)
        print("  ADMIN role synced with all permissions.")

    # Create HR role (Senior)
    hr_role, created_hr = Role.objects.get_or_create(
        code="HR",
        defaults={"name": "Senior HR Manager", "is_system": True}
    )
    if created_hr:
        # Assign HR permissions (No delete, no increment approval, no audit log, no roles management)
        hr_perms = [p for p in all_permission_objs if p.codename not in [
            "onboarding.delete",
            "salary.approve_increments",
            "exit.delete",
            "student.delete",
            "audit.read",
            "roles.manage"
        ]]
        hr_role.permissions.set(hr_perms)
        print("  Created HR role with default restricted permissions.")

    print("\n4. Seeding default users...")
    User = get_user_model()
    
    # Super Admin User
    admin_email = "admin@company.com"
    admin_user = User.objects.filter(email=admin_email).first()
    if not admin_user:
        admin_user = User.objects.create_superuser(
            email=admin_email,
            username=admin_email,
            password="admin123",
            role=admin_role
        )
        print("  Created Admin user: admin@company.com / admin123")
    else:
        admin_user.role = admin_role
        admin_user.save()
        print("  Linked existing admin@company.com user to ADMIN role.")

    # HR User
    hr_email = "hr@company.com"
    hr_user = User.objects.filter(email=hr_email).first()
    if not hr_user:
        hr_user = User.objects.create_user(
            email=hr_email,
            username=hr_email,
            password="hr123",
            role=hr_role
        )
        print("  Created HR user: hr@company.com / hr123")
    else:
        hr_user.role = hr_role
        hr_user.save()
        print("  Linked existing hr@company.com user to HR role.")

    print("\nSeeding finished successfully.")

if __name__ == '__main__':
    seed_database()
