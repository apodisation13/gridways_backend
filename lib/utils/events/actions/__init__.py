from lib.utils.events.action_types import ActionType
from lib.utils.events.actions.action_one import SendSmsAction
from lib.utils.events.actions.action_two import SendEmailAction


ACTION_REGISTRY = {
    ActionType.SEND_SMS: SendSmsAction,
    ActionType.SEND_EMAIL: SendEmailAction,
    # ActionType.WEBHOOK: WebhookAction,
}
