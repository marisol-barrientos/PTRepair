# Scenario config
SRC_LABEL = "Confirm Order"
DST_LABEL = "Ship Item"

DEFAULT_CONTRADICTING_STATES = {
    "payment_received": "payment_missing",
    "payment_missing": "payment_received",
    "item_shipped": "item_not_shipped",
    "item_not_shipped": "item_shipped",
    "order_confirmed": "order_not_confirmed",
    "order_not_confirmed": "order_confirmed",
}

DEFAULT_CONTRADICTING_ACTIVITIES = {}

DEFAULT_ACTIVITIES = [
    "receive order",
    "confirm order",
    "receive payment",
    "notify customer",   # <-- add this because tree uses it
    "ship item",
    "archive order",
]

DEFAULT_ACTIVITY_PRECONDITIONS = {
    "receive order": "order_initial",
    "confirm order": "order_initial",
    "receive payment": "order_confirmed",
    "notify customer": "order_confirmed",
    "ship item": "payment_received",
    "archive order": "item_shipped",
}

DEFAULT_ACTIVITY_POSTCONDITIONS_POSITIVE = {
    "receive order": "order_initial",
    "confirm order": "order_confirmed",
    "receive payment": "payment_received",
    "notify customer": "customer_notified",
    "ship item": "item_shipped",
    "archive order": "order_archived",
}

DEFAULT_ACTIVITY_POSTCONDITIONS_NEGATIVE = {
    "ship item": "item_not_shipped",
}