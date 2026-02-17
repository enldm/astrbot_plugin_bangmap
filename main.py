# main.py
from astrbot.api.all import *
import aiohttp
import time

# 省份映射
PROVINCE_MAP = {
    "北京": "北京市", "天津": "天津市", "上海": "上海市", "重庆": "重庆市",
    "河北": "河北省", "山西": "山西省", "辽宁": "辽宁省", "吉林": "吉林省",
    "黑龙江": "黑龙江省", "江苏": "江苏省", "浙江": "浙江省", "安徽": "安徽省",
    "福建": "福建省", "江西": "江西省", "山东": "山东省", "河南": "河南省",
    "湖北": "湖北省", "湖南": "湖南省", "广东": "广东省", "海南": "海南省",
    "四川": "四川省", "贵州": "贵州省", "云南": "云南省", "陕西": "陕西省",
    "甘肃": "甘肃省", "青海": "青海省", "台湾": "台湾省",
    "广西": "广西壮族自治区", "西藏": "西藏自治区", "宁夏": "宁夏回族自治区",
    "新疆": "新疆维吾尔自治区", "内蒙古": "内蒙古自治区",
    "香港": "香港特别行政区", "澳门": "澳门特别行政区", "海外": "海外"
}

SINGLE_CHAR_ALIAS = {
    "京": "北京市", "津": "天津市", "沪": "上海市", "渝": "重庆市",
    "冀": "河北省", "晋": "山西省", "蒙": "内蒙古自治区", "辽": "辽宁省",
    "吉": "吉林省", "黑": "黑龙江省", "苏": "江苏省", "浙": "浙江省",
    "皖": "安徽省", "闽": "福建省", "赣": "江西省", "鲁": "山东省",
    "豫": "河南省", "鄂": "湖北省", "湘": "湖南省", "粤": "广东省",
    "桂": "广西壮族自治区", "琼": "海南省", "川": "四川省", "蜀": "四川省",
    "黔": "贵州省", "贵": "贵州省", "滇": "云南省", "云": "云南省",
    "陕": "陕西省", "秦": "陕西省", "甘": "甘肃省", "陇": "甘肃省",
    "青": "青海省", "宁": "宁夏回族自治区", "新": "新疆维吾尔自治区",
    "藏": "西藏自治区", "港": "香港特别行政区", "澳": "澳门特别行政区",
    "台": "台湾省",
}

@register("bang_map", "enldm", "全国邦群查询", "v0.1", "https://github.com/enldm/astrbot_plugin_bangmap")
class BangMapPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.config = self.context.get_config() or {}
        self._cache_data = None
        self._cache_time = 0  # Unix timestamp

    async def _get_bang_data(self):
        # 缓存有效期：3600 秒（1 小时）
        if self._cache_data is not None and (time.time() - self._cache_time) < 3600:
            return self._cache_data

        url = "https://mapapi.enldm.cyou/api/bandori"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        response = await resp.json()
                        # 转换新格式为旧格式，保持兼容性
                        if response.get("success") and "data" in response:
                            # 按省份分组
                            province_data = {}
                            for item in response["data"]:
                                province = item.get("province", "")
                                raw_text = item.get("raw_text", "")
                                if province and raw_text:
                                    if province not in province_data:
                                        province_data[province] = []
                                    province_data[province].append(raw_text)
                            self._cache_data = province_data
                            self._cache_time = time.time()
                            return province_data
                        else:
                            logger.error(f"邦邦地图：API 返回数据格式错误")
                            return None
                    else:
                        logger.error(f"邦邦地图：HTTP 请求失败，状态码 {resp.status}")
                        return None
        except Exception as e:
            logger.error(f"邦邦地图：获取数据失败 - {e}")
            return None

    def _resolve_province(self, inp: str) -> str:
        inp = inp.strip()
        if not inp:
            return ""
        full_set = set(PROVINCE_MAP.values())
        if inp in full_set:
            return inp
        if inp in PROVINCE_MAP:
            return PROVINCE_MAP[inp]
        if inp in SINGLE_CHAR_ALIAS:
            return SINGLE_CHAR_ALIAS[inp]
        return ""

    @command("邦邦地图")
    async def bang_map_command(self, event: AstrMessageEvent, province: str = ""):
        """
        查询邦邦群信息。
        
        参数:
            province(string, 可选): 省份名称或简称。留空则显示帮助。
        """
        if not province:
            yield event.plain_result(
                "欢迎使用全国邦邦地图查询！\n"
                "请输入：邦邦地图 省份\n"
                "支持省份全称或二字简称（例如：广东、粤、海外）。"
            )
            return

        province_full = self._resolve_province(province)
        if not province_full:
            yield event.plain_result(f"❌ 未识别省份「{province}」。请使用标准名称或简称（如：粤、江苏、北京）。")
            return

        data = await self._get_bang_data()
        if not data:
            yield event.plain_result("❌ 邦邦群数据加载失败，请稍后再试。")
            return

        if province_full not in data or not data[province_full]:
            yield event.plain_result(f"⚠️ 「{province_full}」暂无登记的邦邦群信息。")
            return

        lines = [f"📍{province_full} 的邦邦群如下："]
        for item in data[province_full]:
            clean = " ".join(item.split())
            lines.append(f"• {clean}")
        
        text = "\n".join(lines)
        if len(text) > 2000:
            text = text[:1990] + "\n...（内容过长已截断）"
        
        yield event.plain_result(text)