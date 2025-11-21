from typing import Any

from lib.utils.events.actions.base import ActionBase
from lib.utils.events.uuu import render_template


class SendSmsAction(ActionBase):
    async def execute(self, context: dict[str, Any]) -> bool:
        print("STR9")
        if not self.check_conditions(context):
            print("STR10")
            return True  # Пропускаем если условия не выполнены

        receiver_template = self.config['receiver']
        print("STR13", receiver_template)
        receiver = render_template(receiver_template, context)
        print("STR17", receiver)

        # Здесь логика отправки SMS
        print(f"Sending SMS to {receiver}")
        return True
