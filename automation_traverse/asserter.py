"""
module pertaining to asserting
"""
import pprint
from typing import Any, Dict

from assertpy import assert_that
from automation_entities.context import Context
from automation_entities.entities import Entity


class DictAsserter(Entity):
    """
    asserter for asserting on ``dict`` keys and values

    .. attribute:: val

        ``dict`` representing the dict values
    """

    val: Dict[Any, Any]

    def __init__(self, context: Context, val: dict) -> None:
        self.val = val
        super().__init__(context, pprint.pformat(val))

    def get_value(self, key: Any) -> Any:
        """
        get and return the value corresponding to the given *key*
        """
        with self.interaction():
            self.request(f"get_value {key}")

            assert_that(self.val).contains(key)

            with self.result() as result:
                val = self.val[key]
                result.log(f"Val: {pprint.pformat(val)}")

                if isinstance(val, dict):
                    val = self.__class__(self.context, val)
                return val

    def __getitem__(self, key):
        return self.get_value(key)
