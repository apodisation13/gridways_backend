from enum import StrEnum


class ActionType(StrEnum):
    SEND_SMS = "ActionSendSms"
    SEND_EMAIL = "ActionSendEmail"
    WEBHOOK = "ActionWebhook"
