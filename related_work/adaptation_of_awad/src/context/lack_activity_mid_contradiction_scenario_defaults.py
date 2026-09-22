# Scenario config
SRC_LABEL = "Confirm Order"
DST_LABEL = "Ship Item"

DEFAULT_CONTRADICTING_STATES = {
    "order_confirmed": "order_cancelled",
    "order_cancelled": "order_confirmed",

    "payment_received": "payment_missing",
    "payment_missing": "payment_received",

    "item_shipped": "item_not_shipped",
    "item_not_shipped": "item_shipped",
}

# Shipping contradicts cancellation
DEFAULT_CONTRADICTING_ACTIVITIES = {
    "ship item": "cancel order",
}

DEFAULT_ACTIVITIES = [
    "receive order",
    "confirm order",
    "cancel order",
    "receive payment",
    "ship item",
    "archive order",
]

DEFAULT_ACTIVITY_PRECONDITIONS = {
    "receive order": "order_initial",
    "confirm order": "order_initial",

    "cancel order": "order_confirmed",
    "receive payment": "order_confirmed",

    "ship item": "payment_received and order_confirmed"
}

DEFAULT_ACTIVITY_POSTCONDITIONS_POSITIVE = {
    "receive order": "order_initial",
    "confirm order": "order_confirmed",

    "cancel order": "order_cancelled",
    "receive payment": "payment_received",

    "ship item": "item_shipped",
    "archive order": "order_archived",
}

DEFAULT_ACTIVITY_POSTCONDITIONS_NEGATIVE = {
    # canceling invalidates "confirmed" (blocks shipping)
    "cancel order": "order_confirmed",
    "ship item": "item_not_shipped",
}
