# apps/student_certificate/utils.py
import datetime
import calendar

def calculate_completed_duration(start_date, end_date):
    """
    Calculates completed duration between start_date and end_date.
    Returns something like '2 Months Completed', '45 Days Completed', etc.
    """
    delta = end_date - start_date
    days = delta.days
    if days <= 0:
        return "0 Days Completed"
    
    months = 0
    temp_date = start_date
    
    # Increment month-by-month and see if we stay under end_date
    while True:
        next_month = temp_date.month + 1
        next_year = temp_date.year
        if next_month > 12:
            next_month = 1
            next_year += 1
        
        # Handle end of month day clipping (e.g. Jan 31 -> Feb 28)
        last_day_of_next_month = calendar.monthrange(next_year, next_month)[1]
        next_day = min(start_date.day, last_day_of_next_month)
        
        next_date = datetime.date(next_year, next_month, next_day)
        if next_date <= end_date:
            months += 1
            temp_date = next_date
        else:
            break
            
    remaining_days = (end_date - temp_date).days
    
    if months > 0:
        parts = []
        parts.append(f"{months} Month{'s' if months > 1 else ''}")
        if remaining_days > 0:
            parts.append(f"{remaining_days} Day{'s' if remaining_days > 1 else ''}")
        return " and ".join(parts) + " Completed"
    else:
        # Less than 1 month, show in weeks or days
        if days < 7:
            return f"{days} Day{'s' if days > 1 else ''} Completed"
        weeks = days // 7
        rem_days = days % 7
        parts = []
        parts.append(f"{weeks} Week{'s' if weeks > 1 else ''}")
        if rem_days > 0:
            parts.append(f"{rem_days} Day{'s' if rem_days > 1 else ''}")
        return " and ".join(parts) + " Completed"
