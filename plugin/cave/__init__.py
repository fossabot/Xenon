# coding=utf-8
"""
Xenon
回声洞
灵感来源于PCL2内测群
"""
from graia.application import Member, MessageChain, GraiaMiraiApplication
from graia.application.message.elements.internal import Plain
from graia.saya import Saya, Channel
from graia.saya.builtins.broadcast import ListenerSchema

import lib
from lib import permission
from lib.command import CommandEvent
from .entry_parser import to_list, to_text

__version__ = "2.0.0"
__plugin_name__ = "cave"
__author__ = "BlueGlassBlock"
__plugin_doc__ = """\
回声洞（不要与PCL2的回声洞混淆了！）
.cave： 从回声洞抽取一条语录
.cave-a MESSAGE： 向回声洞添加一条语录
.cave-v ID：查看回声洞指定ID的语录
.cave-d ID：删除回声洞指定ID的语录
.cave-count：统计回声洞条数"""

saya = Saya.current()
channel = Channel.current()
db = lib.database.Database.current()


@channel.use(ListenerSchema(listening_events=[CommandEvent]))
async def cave(event: CommandEvent):

    if event.command == ".cave" and event.perm_lv >= permission.USER:
        db_cur = await db.open(
            "cave", "(id INTEGER PRIMARY KEY, name TEXT, message TEXT)"
        )
        async with db_cur:
            entry = await (
                await db_cur.execute(
                    "SELECT * FROM cave ORDER BY RANDOM() DESC LIMIT 1"
                )
            ).fetchone()
            msg = f"回声洞 #{entry[0]} by {entry[1]}\n"
            await event.send_result(await to_list(entry[2], [Plain(msg)]))


@channel.use(ListenerSchema(listening_events=[CommandEvent]))
async def cave_mgmt(app: GraiaMiraiApplication, event: CommandEvent):
    if event.command.startswith(".cave-") and event.perm_lv >= permission.FRIEND:
        db_cur = await db.open(
            "cave", "(id INTEGER PRIMARY KEY, name TEXT, message TEXT)"
        )
        async with db_cur:
            cmd = event.command.removeprefix(".cave-")
            if cmd.startswith("a ") and event.group:
                member: Member = await app.getMember(event.group, event.user)
                msg_id = (
                    await (
                        await db_cur.execute(
                            "SELECT MIN(id) + 1 FROM cave WHERE "
                            "id + 1 NOT IN (SELECT id FROM cave)"
                        )
                    ).fetchone()
                )[0]
                chain = event.msg_chain.asSendable().asMerged()
                await db_cur.execute(
                    "INSERT INTO cave VALUES (?, ?, ?)",
                    (
                        msg_id,
                        member.name,
                        await to_text(chain[(0, len(".cave-a ")) :]),
                    ),
                )
                reply = MessageChain.create([Plain(f"成功添加，ID为{msg_id}")])
            elif cmd.startswith("d "):
                try:
                    target_id = int(cmd.removeprefix("d "))
                    res = await (
                        await db_cur.execute(
                            "SELECT * FROM cave WHERE id = ?", (target_id,)
                        )
                    ).fetchone()
                    if not res:
                        raise ValueError(f"#{target_id}不存在")
                except ValueError as e:
                    reply = MessageChain.create([Plain(f"内容错误：{e.args}")])
                else:
                    await db_cur.execute("DELETE FROM cave WHERE id = ?", (target_id,))
                    reply = await to_list(res[2], [Plain(f"已删除#{target_id}：")])
            elif cmd.startswith("v "):
                try:
                    target_id = int(cmd.removeprefix("v "))
                    res = await (
                        await db_cur.execute(
                            "SELECT * FROM cave WHERE id = ?", (target_id,)
                        )
                    ).fetchone()
                    if not res:
                        raise ValueError(f"#{target_id}不存在")
                except ValueError as e:
                    reply = MessageChain.create([Plain(f"内容错误：{e.args}")])
                else:
                    reply = await to_list(res[2], [Plain(f"#{target_id} by {res[1]}：")])
            elif cmd == "count":
                cnt = await (
                    (await db_cur.execute("SELECT COUNT() FROM cave")).fetchone()
                )
                reply = MessageChain.create([Plain(f"Xenon 回声洞：\n共有{cnt[0]}条记录")])
            else:
                reply = "命令无效"
            await event.send_result(reply)
