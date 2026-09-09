# Database Package
from .database import (
    init_db,
    create_user,
    verify_user,
    get_user_by_id,
    create_client,
    get_user_clients,
    get_next_invoice_number,
    create_invoice,
    get_all_invoices,
    get_invoice_by_id,
    mark_invoice_paid,
    get_client_history,
    create_service,
    get_user_services,
    update_service,
    delete_service,
    update_invoice_pdf_url,
    hydrate_sqlite_from_firestore,
    delete_client
)

__all__ = [
    "init_db",
    "create_user",
    "verify_user",
    "get_user_by_id",
    "create_client",
    "get_user_clients",
    "get_next_invoice_number",
    "create_invoice",
    "get_all_invoices",
    "get_invoice_by_id",
    "mark_invoice_paid",
    "get_client_history",
    "create_service",
    "get_user_services",
    "update_service",
    "delete_service",
    "update_invoice_pdf_url",
    "hydrate_sqlite_from_firestore",
    "delete_client"
]

