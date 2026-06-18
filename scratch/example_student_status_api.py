"""
Example usage of the new Student Status & Pipeline API endpoints

These examples show how to fetch and analyze student categorization
by their completion status and pipeline stage in Bitrix24.

Created: 2024
"""

import requests
import json
from typing import Dict, List

BASE_URL = "http://localhost:8000/api/students"


# ============================================================================
# EXAMPLE 1: Quick Stats - Best for Dashboards
# ============================================================================

def get_quick_stats():
    """
    Get lightweight statistics with percentages.
    Perfect for dashboard widgets.
    
    This is the FASTEST endpoint - use this for real-time dashboards.
    """
    response = requests.get(f"{BASE_URL}/status-stats/")
    if response.status_code == 200:
        data = response.json()
        print("📊 QUICK STATS")
        print("=" * 50)
        print(f"Total Students: {data['total_students']}")
        print(f"✅ Completed: {data['completed']['count']} ({data['completed']['percentage']:.1f}%)")
        print(f"❌ Incomplete: {data['incomplete']['count']} ({data['incomplete']['percentage']:.1f}%)")
        print(f"🔄 Ongoing: {data['ongoing']['count']} ({data['ongoing']['percentage']:.1f}%)")
        print()
        return data
    else:
        print(f"Error: {response.status_code}")
        return None


# ============================================================================
# EXAMPLE 2: Status Summary - Best for Detailed Lists
# ============================================================================

def get_status_summary():
    """
    Get students grouped by status with full details.
    Best for reports and detailed analysis.
    """
    response = requests.get(f"{BASE_URL}/status-summary/")
    if response.status_code == 200:
        data = response.json()
        print("📋 STATUS SUMMARY")
        print("=" * 50)
        
        # Show summary
        summary = data['summary']
        print(f"Total: {summary['total']}")
        print(f"Completed: {summary['completed']}")
        print(f"Incomplete: {summary['incomplete']}")
        print(f"Ongoing: {summary['ongoing']}")
        print()
        
        # Show completed students
        completed = data['students_by_status'].get('COMPLETED', [])
        print("✅ COMPLETED STUDENTS:")
        for student in completed[:5]:  # Show first 5
            print(f"  - {student['name']} ({student['bitrix_id']})")
            print(f"    Course: {student['course_name']}")
            print(f"    Completed: {student['completion_date']}")
        if len(completed) > 5:
            print(f"  ... and {len(completed) - 5} more")
        print()
        
        # Show stage summary
        print("📍 STAGE SUMMARY:")
        stage_summary = data['stage_summary']
        for stage_id, stage_info in stage_summary.items():
            print(f"  {stage_info['stage_name']}: {stage_info['count']} students")
        print()
        
        return data
    else:
        print(f"Error: {response.status_code}")
        return None


# ============================================================================
# EXAMPLE 3: Stage Breakdown - Best for Full Analysis
# ============================================================================

def get_stage_breakdown():
    """
    Get detailed stage-wise breakdown with status summary.
    Most comprehensive view of all students and stages.
    """
    response = requests.get(f"{BASE_URL}/stage-breakdown/")
    if response.status_code == 200:
        data = response.json()
        print("🔀 STAGE BREAKDOWN (Detailed)")
        print("=" * 50)
        
        # Show overall status summary
        status_summary = data['status_summary']
        print("Status Summary:")
        for status, info in status_summary.items():
            print(f"  {status}: {info['count']} students")
        print()
        
        # Show each stage
        print("Stages (sorted by count):")
        for stage in data['stage_breakdown']:
            print(f"\n  📊 {stage['stage_name']}")
            print(f"     Code: {stage['stage_code']}")
            print(f"     Count: {stage['count']}")
            print(f"     Students: {', '.join(stage['student_ids'][:5])}", end="")
            if len(stage['student_ids']) > 5:
                print(f", ... and {len(stage['student_ids']) - 5} more")
            else:
                print()
        print()
        
        return data
    else:
        print(f"Error: {response.status_code}")
        return None


# ============================================================================
# EXAMPLE 4: Get Specific Student Statuses
# ============================================================================

def get_completed_students():
    """Get list of all completed students with details."""
    response = requests.get(f"{BASE_URL}/status-summary/")
    if response.status_code == 200:
        data = response.json()
        completed = data['students_by_status'].get('COMPLETED', [])
        print(f"\n✅ COMPLETED STUDENTS ({len(completed)} total):")
        print("=" * 50)
        for student in completed:
            print(f"\nName: {student['name']}")
            print(f"  ID: {student['bitrix_id']}")
            print(f"  Email: {student['email']}")
            print(f"  Course: {student['course_name']}")
            print(f"  Institute: {student['institute']}")
            print(f"  Joined: {student['joining_date']}")
            print(f"  Completed: {student['completion_date']}")
            print(f"  Mentor: {student['mentor']}")
        return completed
    return None


def get_failed_students():
    """Get list of all failed/incomplete students."""
    response = requests.get(f"{BASE_URL}/stage-breakdown/")
    if response.status_code == 200:
        data = response.json()
        # Find FAIL stage
        failed_stage = next(
            (s for s in data['stage_breakdown'] if s['stage_code'] == 'FAIL'),
            None
        )
        if failed_stage:
            print(f"\n❌ FAILED/INCOMPLETE STUDENTS ({failed_stage['count']} total):")
            print("=" * 50)
            for student in failed_stage['students']:
                print(f"\nName: {student['name']}")
                print(f"  ID: {student['bitrix_id']}")
                print(f"  Email: {student['email']}")
                print(f"  Course: {student.get('course_name', 'N/A')}")
            return failed_stage['students']
    return None


def get_ongoing_students():
    """Get list of all ongoing students."""
    response = requests.get(f"{BASE_URL}/status-summary/")
    if response.status_code == 200:
        data = response.json()
        ongoing = data['students_by_status'].get('ONGOING', [])
        print(f"\n🔄 ONGOING STUDENTS ({len(ongoing)} total):")
        print("=" * 50)
        # Group by stage
        stages = {}
        for student in ongoing:
            stage = student.get('stage_name', 'Unknown')
            if stage not in stages:
                stages[stage] = []
            stages[stage].append(student)
        
        for stage, students in sorted(stages.items()):
            print(f"\n📍 {stage} ({len(students)} students)")
            for s in students[:3]:  # Show first 3
                print(f"  - {s['name']} ({s['bitrix_id']})")
            if len(students) > 3:
                print(f"  ... and {len(students) - 3} more")
        
        return ongoing
    return None


# ============================================================================
# EXAMPLE 5: Export Data to CSV
# ============================================================================

def export_to_csv():
    """Export status data to CSV file."""
    import csv
    
    response = requests.get(f"{BASE_URL}/status-summary/")
    if response.status_code == 200:
        data = response.json()
        
        # Flatten all students
        all_students = []
        for status, students in data['students_by_status'].items():
            for student in students:
                student_data = {
                    'bitrix_id': student['bitrix_id'],
                    'name': student['name'],
                    'email': student['email'],
                    'status': status,
                    'stage': student.get('stage_name', 'N/A'),
                    'course_name': student.get('course_name', 'N/A'),
                    'institute': student.get('institute', 'N/A'),
                    'mentor': student.get('mentor', 'N/A'),
                }
                all_students.append(student_data)
        
        # Write to CSV
        with open('student_status_report.csv', 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'bitrix_id', 'name', 'email', 'status', 'stage',
                'course_name', 'institute', 'mentor'
            ])
            writer.writeheader()
            writer.writerows(all_students)
        
        print(f"✅ Exported {len(all_students)} students to student_status_report.csv")
        return all_students
    return None


# ============================================================================
# EXAMPLE 6: Performance Comparison
# ============================================================================

def compare_endpoint_speeds():
    """Compare response times of all three endpoints."""
    import time
    
    print("\n⏱️  PERFORMANCE COMPARISON")
    print("=" * 50)
    
    endpoints = [
        ('status-stats', 'Lightweight stats (fastest)'),
        ('status-summary', 'Full student details'),
        ('stage-breakdown', 'Most detailed (slowest)'),
    ]
    
    for endpoint, description in endpoints:
        start = time.time()
        response = requests.get(f"{BASE_URL}/{endpoint}/")
        elapsed = (time.time() - start) * 1000  # Convert to ms
        
        size = len(response.text) / 1024  # Convert to KB
        print(f"{endpoint:20} {description:30} {elapsed:6.1f}ms ({size:.1f}KB)")


# ============================================================================
# EXAMPLE 7: Use in Dashboard Widget
# ============================================================================

def dashboard_widget_example():
    """
    Example of how to use status-stats for a dashboard widget.
    This would be rendered in HTML/template.
    """
    response = requests.get(f"{BASE_URL}/status-stats/")
    if response.status_code == 200:
        stats = response.json()
        
        # HTML-like output
        html = f"""
        <div class="student-stats-widget">
            <h2>Student Progress</h2>
            <div class="stats-grid">
                <div class="stat-card completed">
                    <span class="emoji">✅</span>
                    <span class="count">{stats['completed']['count']}</span>
                    <span class="label">Completed</span>
                    <span class="percentage">{stats['completed']['percentage']:.1f}%</span>
                </div>
                <div class="stat-card incomplete">
                    <span class="emoji">❌</span>
                    <span class="count">{stats['incomplete']['count']}</span>
                    <span class="label">Incomplete</span>
                    <span class="percentage">{stats['incomplete']['percentage']:.1f}%</span>
                </div>
                <div class="stat-card ongoing">
                    <span class="emoji">🔄</span>
                    <span class="count">{stats['ongoing']['count']}</span>
                    <span class="label">Ongoing</span>
                    <span class="percentage">{stats['ongoing']['percentage']:.1f}%</span>
                </div>
            </div>
            <div class="total">Total: {stats['total_students']} students</div>
        </div>
        """
        print(html)
        return stats


# ============================================================================
# EXAMPLE 8: Run All Examples
# ============================================================================

def run_all_examples():
    """Run all examples in sequence."""
    print("\n" + "=" * 60)
    print("STUDENT STATUS & PIPELINE API - USAGE EXAMPLES")
    print("=" * 60)
    
    try:
        # Example 1: Quick stats
        get_quick_stats()
        
        # Example 2: Status summary
        get_status_summary()
        
        # Example 3: Stage breakdown
        get_stage_breakdown()
        
        # Example 4: Specific statuses
        get_completed_students()
        get_failed_students()
        get_ongoing_students()
        
        # Example 5: Export
        export_to_csv()
        
        # Example 6: Performance
        compare_endpoint_speeds()
        
        # Example 7: Dashboard
        dashboard_widget_example()
        
        print("\n" + "=" * 60)
        print("✅ ALL EXAMPLES COMPLETED")
        print("=" * 60)
        
    except requests.exceptions.ConnectionError:
        print("❌ Error: Cannot connect to API server")
        print("   Make sure the Django server is running at http://localhost:8000")
    except Exception as e:
        print(f"❌ Error: {str(e)}")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        example = sys.argv[1]
        
        if example == "stats":
            get_quick_stats()
        elif example == "summary":
            get_status_summary()
        elif example == "breakdown":
            get_stage_breakdown()
        elif example == "completed":
            get_completed_students()
        elif example == "failed":
            get_failed_students()
        elif example == "ongoing":
            get_ongoing_students()
        elif example == "export":
            export_to_csv()
        elif example == "performance":
            compare_endpoint_speeds()
        elif example == "dashboard":
            dashboard_widget_example()
        elif example == "all":
            run_all_examples()
        else:
            print(f"Unknown example: {example}")
            print("Available: stats, summary, breakdown, completed, failed, ongoing, export, performance, dashboard, all")
    else:
        print("Usage: python example_student_status_api.py [example]")
        print("Examples: stats, summary, breakdown, completed, failed, ongoing, export, performance, dashboard, all")
        print("\nRunning all examples...\n")
        run_all_examples()
