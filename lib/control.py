# coding=utf-8
"""
Xenon 管理
"""
import time
from asyncio import Lock
from collections import defaultdict
from numbers import Real
from typing import DefaultDict, NoReturn, Optional, Union

from graia.application import Friend, Member, MessageChain
from graia.application.message.elements.internal import Plain
from graia.broadcast.builtin.decorators import Depend
from graia.broadcast.exceptions import ExecutionStop

from . import database
from .command import CommandEvent


class Permission:
    """
    用于管理权限的类，不应被实例化
    """

    cursor: Optional[database.Cursor] = None

    ADMIN = 50
    OPERATOR = 40
    MODERATOR = 30
    FRIEND = 20
    USER = 10
    BANNED = 0
    DEFAULT = USER

    levels = {
        "admin": ADMIN,
        "operator": OPERATOR,
        "op": OPERATOR,
        "moderator": MODERATOR,
        "mod": MODERATOR,
        "friend": FRIEND,
        "user": USER,
        "banned": BANNED,
        "default": DEFAULT,
    }

    @classmethod
    async def open_db(cls) -> NoReturn:
        """
        打开 Xenon 的 权限 数据库

        因为打开数据库是异步的，所以需要作为协程函数调用
        """
        db = database.Database.current()
        cls.cursor = await db.open(
            "permission", "(id INTEGER PRIMARY KEY," "level INTEGER)"
        )

    @classmethod
    async def get(cls, user: Union[Friend, Member, int]) -> int:
        """
        获取用户的权限

        :param user: 用户实例或QQ号
        :return: 等级，整数
        """
        if type(user) in (Friend, Member):
            user = user.id
        user: int
        res = await (await cls.cursor.select("level", (user,), "id = ?")).fetchone()
        if res is None:
            await cls.cursor.insert((user, cls.DEFAULT))
            return cls.DEFAULT
        return res[0]

    @classmethod
    async def set(cls, user: Union[Friend, Member, int], level: int) -> None:
        """
        设置用户的权限为特定等级

        :param user: 用户实例或QQ号
        :param level: 等级，整数
        """
        if type(user) in (Friend, Member):
            user = user.id
        user: int
        await cls.cursor.insert((user, level))

    @classmethod
    def require(cls, level: int) -> Depend:
        """
        指示需要 `level` 以上等级才能触发

        :param level: 限制等级
        """

        async def perm_check(event: CommandEvent):
            if event.perm_lv < level:
                raise ExecutionStop()

        return Depend(perm_check)


class Interval:
    """
    用于冷却管理的类，不应被实例化
    """
    next_exec: DefaultDict[int, float] = defaultdict(lambda: 0.0)
    lock: Lock = Lock()

    @classmethod
    def require(
            cls,
            suspend_time: Real,
            override_level: int = Permission.MODERATOR,
    ):
        """
        指示用户每执行一次后需要至少相隔 `suspend_time` 秒才能再次触发功能

        等级在 `override_level` 以上的可以无视限制

        :param suspend_time: 冷却时间
        :param override_level: 可超越限制的最小等级
        """

        async def cd_check(event: CommandEvent):
            cd: float = float(suspend_time)
            if event.perm_lv >= override_level:
                return
            current = time.time()
            async with cls.lock:
                next_exec = cls.next_exec[event.user]
                if current < next_exec:
                    await event.send_result(
                        MessageChain.create(
                            [
                                Plain(
                                    f"冷却还有{next_exec - current:.2f}秒结束"
                                )
                            ]
                        )
                    )
                    raise ExecutionStop()
                else:
                    cls.next_exec[event.user] = current + cd

        return Depend(cd_check)
