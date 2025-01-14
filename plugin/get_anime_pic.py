# coding=utf-8
import json
from typing import Any, Callable, Coroutine, Dict, Tuple

import aiohttp
from graia.application import MessageChain
from graia.application.message.elements.internal import Image, Plain
from graia.application.message.parser.literature import Literature
from graia.saya import Channel, Saya
from graia.saya.builtins.broadcast import ListenerSchema

import lib
from lib.command import CommandEvent
from lib.control import Interval, Permission

__version__ = "1.0.0"
__author__ = "BlueGlassBlock"
__plugin_name__ = "get_anime_pic"
__usage__ = """
.get_anime_pic：从用户配置的API获取一张图片
.set_anime_api API_PROVIDER：设置用户的API为 API_PROVIDER
API PROVIDER的可用值为：
{ rainchan, lolicon, pic.re,
waifu.pics/waifu, waifu.pics/neko,
sola-acg, dmoe.cc }
"""

db = lib.database.Database.current()


async def get_lolicon() -> Tuple[bytes, str]:
    """
    Doc : https://api.lolicon.app
    """

    async with aiohttp.request(
        "GET", "https://api.lolicon.app/" "setu/v2?size=regular&r18=0"
    ) as response:
        json_str = await response.text()
        data = json.loads(json_str)
    if data["error"]:
        raise Exception(data["error"])
    data: dict = data["data"][0]
    async with aiohttp.request("GET", data["urls"]["regular"]) as img_resp:
        img_data = await img_resp.read()
        pid = str(data["pid"])
        return img_data, pid


async def get_rainchan() -> Tuple[bytes, str]:
    """
    Doc : https://api.lolicon.app/#/setu
    """

    async with aiohttp.request("GET", "https://pximg.rainchan.win/img") as response:
        img_data = await response.read()
        pid = response.url.raw_query_string.removeprefix("img_id=").removesuffix(
            "&web=true"
        )
        return img_data, pid


async def get_pic_re() -> Tuple[bytes, str]:
    """
    Doc: https://api.bi/docs/animeapi/
    """

    async with aiohttp.request(
        "GET", "https://pic.re/image?nin=male&nin=r-18"
    ) as response:
        img_data = await response.read()
        return img_data, "None"


async def get_waifu_pics_waifu() -> Tuple[bytes, str]:
    """
    Doc: https://waifu.pics/docs
    """

    async with aiohttp.request("GET", "https://api.waifu.pics/sfw/waifu") as response:
        json_str = await response.text()
        data = json.loads(json_str)
        async with aiohttp.request("GET", data["url"]) as img_resp:
            img_data = await img_resp.read()
        return img_data, "None"


async def get_waifu_pics_neko() -> Tuple[bytes, str]:
    """
    Doc: https://waifu.pics/docs
    """

    async with aiohttp.request("GET", "https://api.waifu.pics/sfw/neko") as response:
        json_str = await response.text()
        data = json.loads(json_str)
        async with aiohttp.request("GET", data["url"]) as img_resp:
            img_data = await img_resp.read()
        return img_data, "None"


async def get_sola_acg() -> Tuple[bytes, str]:
    """
    Doc: https://www.yingciyuan.cn/
    """

    async with aiohttp.request("GET", "https://www.yingciyuan.cn/pc.php") as response:
        img_data = await response.read()
        return img_data, "None"


async def get_dmoe_cc() -> Tuple[bytes, str]:
    """
    Doc: https://www.dmoe.cc
    """

    async with aiohttp.request("GET", "https://www.dmoe.cc/random.php") as response:
        img_data = await response.read()
        return img_data, "None"


_mapping: Dict[str, Callable[[], Coroutine[Any, Any, Tuple[bytes, str]]]] = {
    "lolicon": get_lolicon,
    "rainchan": get_rainchan,
    "pic.re": get_pic_re,
    "waifu.pics/waifu": get_waifu_pics_waifu,
    "waifu.pics/neko": get_waifu_pics_neko,
    "sola-acg": get_sola_acg,
    "dmoe.cc": get_dmoe_cc,
}

saya = Saya.current()
channel = Channel.current()


@channel.use(
    ListenerSchema(
        listening_events=[CommandEvent],
        inline_dispatchers=[Literature(".get_anime_pic")],
        headless_decorators=[
            Permission.require(Permission.USER),
            Interval.require(240.0),
        ],
    )
)
async def get_anime_pic(event: CommandEvent):
    api_cursor = await db.open("anime_pic_db", "(id INTEGER PRIMARY KEY, api TEXT)")
    async with api_cursor:
        res = await (await api_cursor.select("api", (event.user,), "id = ?")).fetchone()
        if res is None:
            await api_cursor.insert((event.user, "rainchan"))
            pref: str = "rainchan"
        else:
            pref: str = res[0]
        try:
            img_data, pid = await _mapping[pref]()
        except Exception as e:
            reply = MessageChain.create([Plain(f"{repr(e)}")])
        else:
            reply = MessageChain.create(
                [
                    Plain(f"API: {pref}\n"),
                    Plain(f"PID: {pid}\n"),
                    Image.fromUnsafeBytes(img_data),
                ]
            )
        await event.send_result(reply)


@channel.use(
    ListenerSchema(
        listening_events=[CommandEvent],
        inline_dispatchers=[Literature(".set_anime_api")],
        headless_decorators=[Permission.require(Permission.FRIEND)],
    )
)
async def set_anime_api_pref(event: CommandEvent):
    if len(event.command.split(" ")) == 2:
        api_cursor = await db.open("anime_pic_db", "(id INTEGER PRIMARY KEY, api TEXT)")
        async with api_cursor:
            _, pref = event.command.split(" ")
            if pref in _mapping:
                await api_cursor.insert(
                    (
                        event.user,
                        pref,
                    ),
                )
                reply = MessageChain.create([Plain(f"成功设置API为{pref}")])
            else:
                reply = MessageChain.create([Plain(f"{pref}不是可用的API！")])
            await event.send_result(reply)
