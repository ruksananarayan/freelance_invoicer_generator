import os
import logging

# Configure logger
logger = logging.getLogger("smart-invoice-gcs")

def upload_pdf_to_gcs(pdf_bytes, filename, bucket_name=None):
    """
    Optional GCP Cloud Storage integration helper.
    Uploads generated PDF invoice byte buffers to a Google Cloud Storage bucket.
    """
    if bucket_name is None:
        bucket_name = os.environ.get("GCS_BUCKET_NAME", "smart-invoice-pdfs-extreme-gecko-472506-s9")
        
    try:
        from google.cloud import storage
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(f"invoices/{filename}")
        
        blob.upload_from_string(pdf_bytes, content_type="application/pdf")
        logger.info(f"Successfully uploaded {filename} to GCS bucket {bucket_name}")
        return blob.public_url
    except Exception as e:
        logger.warning(f"GCS PDF Upload skipped/deferred (GCP Credentials or Bucket not configured): {e}")
        return None

def download_pdf_from_gcs(filename, bucket_name=None):
    """
    Downloads invoice PDF byte streams privately from GCS.
    """
    if bucket_name is None:
        bucket_name = os.environ.get("GCS_BUCKET_NAME", "smart-invoice-pdfs-extreme-gecko-472506-s9")
    try:
        from google.cloud import storage
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(f"invoices/{filename}")
        return blob.download_as_bytes()
    except Exception as e:
        logger.error(f"Error downloading PDF from GCS privately: {e}")
        return None
