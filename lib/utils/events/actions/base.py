from abc import ABC, abstractmethod
from typing import Dict, Any


class ActionBase(ABC):
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> bool:
        pass

    def check_conditions(self, context: Dict[str, Any]) -> bool:
        """Проверка условий выполнения действия"""
        conditions = self.config.get('conditions', [])

        if isinstance(conditions, bool):
            return conditions

        return True

        # for condition in conditions:
        #     field_value = context.get(condition['field'])
        #     if not self._check_condition(field_value, condition['operator'], condition['value']):
        #         return False
        # return True

    # def _check_condition(self, field_value: Any, operator: str, value: Any) -> bool:
    #     operators = {
    #         'eq': lambda a, b: a == b,
    #         'ne': lambda a, b: a != b,
    #         'gt': lambda a, b: a > b,
    #         'lt': lambda a, b: a < b,
    #         'contains': lambda a, b: b in a if a else False,
    #     }
    #     return operators[operator](field_value, value)
