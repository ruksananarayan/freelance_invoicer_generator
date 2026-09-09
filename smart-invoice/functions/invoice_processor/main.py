import functions_framework
from google.cloud import language_v1

@functions_framework.http
def process_invoice_notes(request):
    """HTTP Cloud Function to analyze invoice notes using Google Cloud Natural Language API."""
    request_json = request.get_json(silent=True)
    notes = request_json.get("notes", "") if request_json else ""
    
    if not notes:
        return {"sentiment_score": 0.0, "status": "no_notes_provided"}, 200

    try:
        client = language_v1.LanguageServiceClient()
        document = language_v1.Document(
            content=notes, 
            type_=language_v1.Document.Type.PLAIN_TEXT
        )
        sentiment = client.analyze_sentiment(request={'document': document}).document_sentiment
        return {
            "sentiment_score": round(sentiment.score, 2),
            "sentiment_magnitude": round(sentiment.magnitude, 2),
            "status": "success"
        }, 200
    except Exception as e:
        return {
            "sentiment_score": 0.0,
            "status": "analysis_fallback",
            "message": str(e)
        }, 200
