import os
import requests
import json
import logging
from django.utils import timezone
from django.conf import settings
from .models import ChecklistAssignment, ChecklistResponse, AIReport, FinalProbationReport
from common.bitrix_client import BitrixClient

logger = logging.getLogger(__name__)

def notify_employee_via_bitrix24(assignment):
    """
    Sends a notification message to the employee in Bitrix24 with the checklist submission link.
    """
    webhook = BitrixClient.get_webhook_url()
    bitrix_user_id = assignment.employee.bitrix_user_id
    if not bitrix_user_id:
        logger.warning(f"Employee {assignment.employee} has no Bitrix24 User ID. Cannot notify.")
        return False

    # Construct the form URL. In production, we'd use the correct domain. We'll fallback to a local URL representation.
    domain = os.getenv('ALLOWED_HOSTS', 'localhost:8000').split(',')[0]
    protocol = "https" if "localhost" not in domain and "127.0.0.1" not in domain else "http"
    form_url = f"{protocol}://{domain}/probation/submit/{assignment.id}/"

    message = (
        f"Hello {assignment.employee.first_name},\n\n"
        f"A new Probation Checklist has been assigned to you: *{assignment.checklist.title}*.\n"
        f"Please fill out and submit the checklist form here: {form_url}\n\n"
        f"Thank you!"
    )

    api_url = f"{webhook}/im.message.add.json"
    payload = {
        "DIALOG_ID": bitrix_user_id,
        "MESSAGE": message
    }

    try:
        response = requests.post(api_url, json=payload, timeout=10)
        res_data = response.json()
        if response.status_code == 200 and "result" in res_data:
            logger.info(f"Bitrix24 notification sent successfully to employee {bitrix_user_id}")
            return True
        else:
            logger.error(f"Bitrix24 notification returned error: {res_data}")
            return False
    except Exception as e:
        logger.error(f"Failed to send Bitrix24 notification: {e}")
        return False


def run_gemini_analysis(assignment):
    """
    Performs AI performance analysis using Google Gemini.
    Compares:
    - Today's response
    - Last 7 daily checklists/responses
    - Previous weekly reports
    - Previous AI reports
    - Employee metadata (designation, department, joining date)
    Returns structured JSON output.
    """
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        logger.error("GEMINI_API_KEY environment variable is not set.")
        return None

    employee = assignment.employee
    # Retrieve previous submissions
    previous_assignments = ChecklistAssignment.objects.filter(
        employee=employee,
        status='Analyzed'
    ).exclude(id=assignment.id).order_by('-submitted_at')[:7]

    history = []
    for prev in previous_assignments:
        resp = getattr(prev, 'response', None)
        rep = getattr(prev, 'ai_report', None)
        history.append({
            "date": prev.submitted_at.strftime('%Y-%m-%d') if prev.submitted_at else "Unknown",
            "checklist_title": prev.checklist.title,
            "answers": resp.answers if resp else {},
            "previous_ai_scores": rep.scores if rep else {},
            "previous_ai_summary": rep.summary if rep.summary else ""
        })

    today_resp = getattr(assignment, 'response', None)
    today_answers = today_resp.answers if today_resp else {}

    # Prompt design
    prompt = f"""
Compare today's responses with all previous submissions for this employee.
Detect improvements, recurring issues, productivity trends, learning progress, consistency, and efficiency.
Highlight strengths, weaknesses, and generate a recommendation (e.g. "Continue", "Extend", "Confirm").

Employee Profile:
- Name: {employee.first_name} {employee.last_name or ''}
- Designation: {employee.designation or 'N/A'}
- Department: {employee.department_name or 'N/A'}
- Probation Start Date: {employee.joining_date or 'N/A'}

Today's Checklist Form: {assignment.checklist.title}
Today's Submissions:
{json.dumps(today_answers, indent=2)}

Historical Context (Last 7 submissions and reports):
{json.dumps(history, indent=2)}

Please return the response EXACTLY matching the requested JSON schema. Do not output anything else than JSON.
"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    headers = {"Content-Type": "application/json"}
    
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "object",
                "properties": {
                    "overall_score": {"type": "integer"},
                    "productivity_score": {"type": "integer"},
                    "efficiency_score": {"type": "integer"},
                    "consistency_score": {"type": "integer"},
                    "trend": {"type": "string"},
                    "strengths": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "improvements": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "recommendation": {"type": "string"},
                    "summary": {"type": "string"},
                    "insights": {
                        "type": "object",
                        "properties": {
                            "positive": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "negative": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        },
                        "required": ["positive", "negative"]
                    }
                ,
                "required": [
                    "overall_score", "productivity_score", "efficiency_score", "consistency_score", 
                    "trend", "strengths", "improvements", "recommendation", "summary", "insights"
                ]}
            }
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        res_data = response.json()
        if response.status_code == 200:
            text_response = res_data['candidates'][0]['content']['parts'][0]['text']
            parsed_json = json.loads(text_response)
            
            # Save the AI report
            ai_report, created = AIReport.objects.update_or_create(
                assignment=assignment,
                defaults={
                    "employee": employee,
                    "scores": {
                        "overall_score": parsed_json.get("overall_score", 0),
                        "productivity_score": parsed_json.get("productivity_score", 0),
                        "efficiency_score": parsed_json.get("efficiency_score", 0),
                        "consistency_score": parsed_json.get("consistency_score", 0),
                    },
                    "trend": parsed_json.get("trend", "Steady"),
                    "strengths": parsed_json.get("strengths", []),
                    "improvements": parsed_json.get("improvements", []),
                    "recommendation": parsed_json.get("recommendation", "Continue"),
                    "summary": parsed_json.get("summary", ""),
                    "insights": parsed_json.get("insights", {"positive": [], "negative": []}),
                }
            )
            assignment.status = 'Analyzed'
            assignment.save()
            return ai_report
        else:
            logger.error(f"Gemini API error: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error executing run_gemini_analysis: {e}")
        return None


def run_final_probation_analysis(employee):
    """
    At the end of the probation period, compiles all reports and asks Gemini to generate a final probation report.
    """
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        logger.error("GEMINI_API_KEY environment variable is not set.")
        return None

    reports = AIReport.objects.filter(employee=employee).order_by('created_at')
    if not reports.exists():
        logger.warning(f"No AI reports found for {employee}. Cannot generate final report.")
        return None

    history_summary = []
    total_score = 0
    scores_list = []
    
    for r in reports:
        overall = r.scores.get("overall_score", 0)
        total_score += overall
        scores_list.append(overall)
        history_summary.append({
            "date": r.created_at.strftime('%Y-%m-%d'),
            "scores": r.scores,
            "trend": r.trend,
            "recommendation": r.recommendation,
            "summary": r.summary
        })

    average_score = total_score / len(reports) if reports else 0
    
    prompt = f"""
Generate a consolidated final 90-day probation report for the following employee based on all historical daily/weekly AI reports.

Employee Profile:
- Name: {employee.first_name} {employee.last_name or ''}
- Designation: {employee.designation or 'N/A'}
- Department: {employee.department_name or 'N/A'}
- Joining Date: {employee.joining_date or 'N/A'}

Historical AI Analysis Reports:
{json.dumps(history_summary, indent=2)}

Please return a response matching the requested JSON schema. Highlight overall trends, strengths, areas of improvements, recurring challenges, confidence levels, and final recommendation.
"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "object",
                "properties": {
                    "best_week": {"type": "string"},
                    "lowest_week": {"type": "string"},
                    "overall_trend": {"type": "string"},
                    "strengths": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "improvements": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "challenges": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "final_recommendation": {"type": "string"},
                    "confidence": {"type": "string"}
                },
                "required": [
                    "best_week", "lowest_week", "overall_trend", "strengths", "improvements", 
                    "challenges", "final_recommendation", "confidence"
                ]
            }
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        res_data = response.json()
        if response.status_code == 200:
            text_response = res_data['candidates'][0]['content']['parts'][0]['text']
            parsed_json = json.loads(text_response)
            
            final_report, created = FinalProbationReport.objects.update_or_create(
                employee=employee,
                defaults={
                    "average_score": round(average_score, 1),
                    "best_week": parsed_json.get("best_week", "N/A"),
                    "lowest_week": parsed_json.get("lowest_week", "N/A"),
                    "overall_trend": parsed_json.get("overall_trend", "Steady"),
                    "strengths": parsed_json.get("strengths", []),
                    "improvements": parsed_json.get("improvements", []),
                    "challenges": parsed_json.get("challenges", []),
                    "final_recommendation": parsed_json.get("final_recommendation", "Confirm Employment"),
                    "confidence": parsed_json.get("confidence", "High"),
                }
            )
            return final_report
        else:
            logger.error(f"Gemini API error: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error executing run_final_probation_analysis: {e}")
        return None
