# data/emails.py
# Sample email dataset with ground truth labels

EMAILS = [
    {
        "id": 1,
        "sender": "boss@company.com",
        "subject": "Q4 Budget Review — Action Required",
        "body": (
            "Please review the attached Q4 budget document and send your "
            "department numbers by EOD Friday. This is a time-sensitive request "
            "and will affect planning for next year."
        ),
        "label": "work",
        "priority": "high",
        "action": "reply",
    },
    {
        "id": 2,
        "sender": "noreply@promo99.xyz",
        "subject": "YOU WON $5,000!! CLAIM NOW!!!",
        "body": (
            "Congratulations! You have been randomly selected to win $5,000 "
            "cash prize. Click here to claim your prize immediately before it "
            "expires tonight at midnight."
        ),
        "label": "spam",
        "priority": "low",
        "action": "ignore",
    },
    {
        "id": 3,
        "sender": "mom@gmail.com",
        "subject": "Dinner on Sunday?",
        "body": (
            "Hey beta, are you free for dinner this Sunday? I'm making biryani "
            "and your favourite kheer. Let me know if you're coming so I can "
            "plan the quantity."
        ),
        "label": "personal",
        "priority": "low",
        "action": "reply",
    },
    {
        "id": 4,
        "sender": "hr@company.com",
        "subject": "Mandatory Training: Security Awareness",
        "body": (
            "All employees must complete the annual security awareness training "
            "by December 31. Please log in to the learning portal and complete "
            "the 30-minute compliance module."
        ),
        "label": "work",
        "priority": "medium",
        "action": "reply",
    },
    {
        "id": 5,
        "sender": "alerts@bank0phishing.ru",
        "subject": "URGENT: Your account has been suspended",
        "body": (
            "Dear customer, we detected suspicious login activity. Your account "
            "access has been suspended. Click the link below to verify your "
            "credentials and restore access immediately."
        ),
        "label": "spam",
        "priority": "low",
        "action": "ignore",
    },
]
