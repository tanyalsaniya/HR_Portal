from rest_framework import permissions

class HasModelPermission(permissions.BasePermission):
    """
    Dynamic RBAC Permission class checking user role permissions.
    """
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        # Superuser and Admin role can do everything
        if user.is_superuser or (user.role and user.role.code == 'ADMIN'):
            return True

        if not user.role or not user.role.is_active:
            return False

        # Get all permission codenames for this user's role
        user_perms = set(user.role.permissions.values_list('codename', flat=True))
        view_name = view.__class__.__name__
        action = getattr(view, 'action', None)

        # 1. Roles & Permissions module
        if 'Role' in view_name or 'Permission' in view_name:
            return 'roles.manage' in user_perms

        # 2. Audit Logs module
        if 'AuditLog' in view_name:
            return 'audit.read' in user_perms

        # 3. Employee Onboarding module
        if 'Employee' in view_name or 'Department' in view_name:
            # Check detail letter actions
            if action in ['generate_offer_letter_api', 'generate_appointment_letter_api', 'generate_bond_letter_api', 'preview_letter_api']:
                return 'onboarding.generate_letters' in user_perms
            if action in ['list', 'retrieve']:
                return 'onboarding.read' in user_perms
            if action == 'create':
                return 'onboarding.create' in user_perms
            if action in ['update', 'partial_update']:
                return 'onboarding.update' in user_perms
            if action == 'destroy':
                return 'onboarding.delete' in user_perms

        # 4. Salary & Payroll module
        if 'SalaryStructure' in view_name or 'SalarySlip' in view_name or 'SalaryIncrement' in view_name:
            if action in ['approve', 'approve_increment', 'approve_increment_api']:
                return 'salary.approve_increments' in user_perms
            if action in ['list', 'retrieve']:
                return 'salary.read' in user_perms
            if action in ['create', 'update', 'partial_update', 'bulk_generate']:
                return 'salary.create_slips' in user_perms

        # 5. Exit Formality module
        if 'ExitRequest' in view_name or 'ExitForm' in view_name or 'ExitSecureLink' in view_name or 'Rejoining' in view_name:
            if 'Rejoining' in view_name:
                return 'exit.rejoin' in user_perms
            if action in ['generate_relieving_api', 'generate_experience_api', 'generate_notice_api', 'preview_letter']:
                return 'exit.generate_letters' in user_perms
            if action == 'generate_noc_api':
                return False
            if action == 'rejoin_api':
                return 'exit.rejoin' in user_perms
            if action in ['list', 'retrieve']:
                return 'exit.read' in user_perms
            if action == 'create':
                return 'exit.create' in user_perms
            if action in ['update', 'partial_update', 'send_link_api', 'resend_link', 'update_clearances', 'update_it_checklist', 'process_ff', 'mark_fully_exited']:
                return 'exit.update' in user_perms
            if action in ['cancel', 'override', 'reopen', 'extend_lwd', 'approve_ff']:
                return False
            if action == 'destroy':
                return 'exit.delete' in user_perms

        # 6. Student Certificate module
        if 'Student' in view_name or 'Course' in view_name or 'Bitrix' in view_name:
            if action in ['export_excel', 'bulk_generate_zip']:
                return 'student.export' in user_perms
            if action in ['list', 'retrieve'] or (action is None and request.method == 'GET'):
                return 'student.read' in user_perms
            if action == 'create':
                return 'student.create' in user_perms
            if action in ['update', 'partial_update', 'record_payment', 'send_warning', 'generate_certificate']:
                return 'student.update' in user_perms
            if action == 'destroy':
                return 'student.delete' in user_perms

        return False
