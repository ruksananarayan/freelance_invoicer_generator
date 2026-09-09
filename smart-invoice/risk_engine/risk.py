from datetime import datetime, date

def calculate_invoice_risk(invoice, client_history, current_date_str=None):
    """
    Overdue Risk Scoring Engine for Freelance Invoices.
    Calculates an explainable risk score (0-100), risk level (Low, Medium, High),
    detailed breakdown of risk drivers, and recommended action.
    """
    if invoice.get("status") == "PAID":
        return {
            "status_label": "Paid",
            "is_overdue": False,
            "days_diff": 0,
            "risk_score": 0,
            "risk_level": "Low",
            "risk_color": "green",
            "explanations": ["Invoice has been fully settled."],
            "recommended_action": "No action needed. Invoice settled."
        }

    # Calculate date difference gracefully
    try:
        due_date = datetime.strptime(invoice["due_date"], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        due_date = date.today()

    if current_date_str:
        try:
            ref_date = datetime.strptime(current_date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            ref_date = date.today()
    else:
        ref_date = date.today()

    days_diff = (ref_date - due_date).days  # Positive if overdue, negative if remaining

    # 1. Determine Status Label & Color
    if days_diff > 0:
        is_overdue = True
        if days_diff == 1:
            status_label = "Overdue by 1 day"
        else:
            status_label = f"Overdue by {days_diff} days"
        status_color = "red"
    elif days_diff == 0:
        is_overdue = False
        status_label = "Due today"
        status_color = "amber"
    elif abs(days_diff) <= 2:
        is_overdue = False
        status_label = f"Due in {abs(days_diff)} days (Soon)"
        status_color = "amber"
    else:
        is_overdue = False
        status_label = f"Due in {abs(days_diff)} days"
        status_color = "blue"

    # 2. Risk Engine Factors Calculation
    score_overdue_days = 0
    score_late_freq = 0
    score_avg_delay = 0
    score_exposure = 0
    
    explanations = []

    # Factor A: Days Overdue (Max 40 points)
    if is_overdue:
        if days_diff <= 2:
            score_overdue_days = 12
            explanations.append(f"Recently overdue ({days_diff} day{'s' if days_diff > 1 else ''} past deadline)")
        elif days_diff <= 5:
            score_overdue_days = 22
            explanations.append(f"Moderate delay ({days_diff} days past deadline)")
        elif days_diff <= 10:
            score_overdue_days = 32
            explanations.append(f"Significant delay ({days_diff} days past deadline)")
        else:
            score_overdue_days = 40
            explanations.append(f"Severe delay ({days_diff} days past deadline)")
    else:
        if days_diff == 0:
            score_overdue_days = 5
            explanations.append("Invoice is due today")
        elif abs(days_diff) <= 2:
            score_overdue_days = 3
            explanations.append("Invoice due date is approaching soon")

    # Factor B: Client Historical Late Payment Frequency (Max 30 points)
    late_count = client_history.get("late_invoices_count", 0)
    paid_count = client_history.get("paid_invoices_count", 0)
    late_ratio = client_history.get("late_payment_ratio", 0.0)

    if paid_count > 0 and late_count > 0:
        score_late_freq = min(30, int(late_ratio * 30))
        explanations.append(f"Client history: {late_count} of {paid_count} past invoices were paid late ({int(late_ratio * 100)}% late rate)")
    elif paid_count == 0 and client_history.get("total_invoices", 0) > 1:
        score_late_freq = 15
        explanations.append("Client has no completed payment history yet")

    # Factor C: Client Average Payment Delay (Max 15 points)
    avg_delay = client_history.get("avg_delay_days", 0)
    if avg_delay > 10:
        score_avg_delay = 15
        explanations.append(f"Client historically delays late payments by an avg of {avg_delay} days")
    elif avg_delay >= 5:
        score_avg_delay = 10
        explanations.append(f"Client historically delays late payments by an avg of {avg_delay} days")
    elif avg_delay >= 1:
        score_avg_delay = 5
        explanations.append(f"Client historically delays payments by an avg of {avg_delay} days")

    # Factor D: Outstanding Amount & Financial Exposure (Max 15 points)
    grand_total = invoice.get("grand_total", 0.0)
    outstanding = client_history.get("outstanding_amount", grand_total)
    
    if grand_total >= 5000 or outstanding >= 7500:
        score_exposure = 15
        explanations.append(f"High financial exposure (Invoice: ${grand_total:,.2f}, Total Outstanding: ${outstanding:,.2f})")
    elif grand_total >= 2000 or outstanding >= 3000:
        score_exposure = 10
        explanations.append(f"Moderate financial exposure (${grand_total:,.2f})")
    elif grand_total >= 1000:
        score_exposure = 5
        explanations.append(f"Standard financial exposure (${grand_total:,.2f})")

    # 3. Final Score Synthesis
    raw_score = score_overdue_days + score_late_freq + score_avg_delay + score_exposure
    final_score = min(100, max(0, raw_score))

    # Determine Risk Level
    if not is_overdue and final_score < 40:
        risk_level = "Low"
        risk_color = "green"
    elif final_score <= 35:
        risk_level = "Low"
        risk_color = "green"
    elif final_score <= 69:
        risk_level = "Medium"
        risk_color = "amber"
    else:
        risk_level = "High"
        risk_color = "red"

    # 4. Recommended Action Determination
    if risk_level == "High":
        if is_overdue:
            recommended_action = "🚨 Immediate Action: Call client executive directly, send formal late payment notice with fee warning, and pause ongoing project deliverables."
        else:
            recommended_action = "⚠️ High Risk Watch: Send courtesy pre-due reminder email today and confirm payment processing status."
    elif risk_level == "Medium":
        if is_overdue:
            recommended_action = "✉️ Escalated Follow-up: Send polite payment reminder email with invoice PDF attached and request payment ETA."
        else:
            recommended_action = "ℹ️ Routine Monitoring: Ensure invoice was received and queued in client's AP department."
    else:
        if is_overdue:
            recommended_action = "✉️ Gentle Reminder: Send a quick check-in email regarding invoice status."
        else:
            recommended_action = "✅ Monitor Normally: Payment on track. No action needed at this time."

    return {
        "status_label": status_label,
        "is_overdue": is_overdue,
        "days_diff": days_diff,
        "risk_score": final_score,
        "risk_level": risk_level,
        "risk_color": risk_color,
        "explanations": explanations,
        "recommended_action": recommended_action,
        "breakdown": {
            "overdue_days_pts": score_overdue_days,
            "late_freq_pts": score_late_freq,
            "avg_delay_pts": score_avg_delay,
            "exposure_pts": score_exposure
        }
    }
