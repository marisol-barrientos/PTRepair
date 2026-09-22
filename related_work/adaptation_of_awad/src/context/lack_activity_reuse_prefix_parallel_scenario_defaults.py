# Scenario config
SRC_LABEL = "Confirm Order"
DST_LABEL = "Ship Item"

# -------------------------------
# 1) Contradicting data states
# -------------------------------
DEFAULT_CONTRADICTING_STATES = {
    "payment_received": "payment_missing",
    "payment_missing": "payment_received",
    "item_shipped": "item_not_shipped",
    "item_not_shipped": "item_shipped",
    "order_confirmed": "order_not_confirmed",
    "order_not_confirmed": "order_confirmed",
}

# -------------------------------
# 2) Contradicting activities
# -------------------------------
DEFAULT_CONTRADICTING_ACTIVITIES = {}

# -------------------------------
# 3) Activities in the domain
# -------------------------------
DEFAULT_ACTIVITIES = [
    "receive order",
    "confirm order",
    "receive payment",
    "notify customer",
    "ship item",
    "archive order",
]

# -------------------------------
# 4) Preconditions
# -------------------------------
DEFAULT_ACTIVITY_PRECONDITIONS = {
    "receive order": "order_initial",
    "confirm order": "order_initial",
    "receive payment": "order_confirmed",
    "notify customer": "order_confirmed",
    "ship item": "payment_received",
    "archive order": "item_shipped",
}

# -------------------------------
# 5) Positive effects
# -------------------------------
DEFAULT_ACTIVITY_POSTCONDITIONS_POSITIVE = {
    "receive order": "order_initial",
    "confirm order": "order_confirmed",
    "receive payment": "payment_received",
    "notify customer": "customer_notified",
    "ship item": "item_shipped",
    "archive order": "order_archived",
}

# -------------------------------
# 6) Negative effects
# -------------------------------
DEFAULT_ACTIVITY_POSTCONDITIONS_NEGATIVE = {
    "ship item": "item_not_shipped",
}
