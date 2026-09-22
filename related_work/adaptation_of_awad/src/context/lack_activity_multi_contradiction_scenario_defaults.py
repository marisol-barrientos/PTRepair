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

# Ship Item contradicts two different activities
DEFAULT_CONTRADICTING_ACTIVITIES = {
    "ship item": "cancel order, return item",
}

DEFAULT_ACTIVITIES = [
    "receive order",
    "confirm order",
    "cancel order",
    "return item",
    "receive payment",
    "ship item",
]

DEFAULT_ACTIVITY_PRECONDITIONS = {
    "receive order": "order_initial",
    "confirm order": "order_initial",

    "cancel order": "order_confirmed",
    "return item": "order_confirmed and item_shipped",

    "receive payment": "order_confirmed",
    "ship item": "payment_received and order_confirmed",
}

DEFAULT_ACTIVITY_POSTCONDITIONS_POSITIVE = {
    "receive order": "order_initial",
    "confirm order": "order_confirmed",

    "cancel order": "order_cancelled",
    "return item": "item_returned",

    "receive payment": "payment_received",
    "ship item": "item_shipped",
}

DEFAULT_ACTIVITY_POSTCONDITIONS_NEGATIVE = {
    "cancel order": "order_confirmed",
    "ship item": "item_not_shipped",
}
