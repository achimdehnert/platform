# shared_contracts/db_views.py — ADR-057 §2.8
# Versioned schemas for shared database views.
# View owner updates this file on every schema change.
# Consumers test against this schema.
#
# Usage (provider test):
#   from shared_contracts.db_views import VIEW_CONTRACTS
#   contract = VIEW_CONTRACTS["v_my_view"]
#   # assert actual DB columns match contract["columns"]
#
# Usage (consumer test):
#   Use @pytest.mark.django_db(transaction=True) for cross-DB view tests

VIEW_CONTRACTS: dict = {
    # Template — add actual view contracts per service
    # "v_active_assessments": {
    #     "owner": "risk-hub",
    #     "version": "1.0.0",
    #     "columns": {
    #         "id": "integer",
    #         "title": "character varying",
    #         "status": "character varying",
    #         "created_at": "timestamp with time zone",
    #         "zone_count": "integer",
    #     },
    # },
}
