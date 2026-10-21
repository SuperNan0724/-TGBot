"""
抖音 Cookie 接收 + 校验工具
==========================

用法（两种都行）：
  1. 双击同目录的「配置抖音Cookie.bat」，按提示粘贴
  2. 命令行：python setup_douyin_cookie.py "你的cookie字符串"

它会做四步检查，任何一步不过都会明确告诉你缺什么：
  ① 格式检查    —— 是不是 key=value; key=value 的形态
  ② 关键字段    —— 抖音风控要求的字段是否齐全
  ③ 写入配置    —— 写进 src/config.py（已被 .gitignore 忽略）
  ④ 真实请求实测 —— 直接打抖音 API，看是否还返回 403 风控

安全：脚本只打印 cookie 的**长度**和**字段名**，不打印完整值，
      避免凭据出现在终端回滚缓冲或日志里。
"""
import os
import re
import sqlite3  # noqa: F401  (不使用，仅保持导入顺序稳定)
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "src")
CONFIG = os.path.join(SRC, "config.py")

# 抖音风控真正依赖的字段。ttwid 是设备标识，缺了必然 403。
REQUIRED_ANY = ["ttwid"]                       # 必须至少有一个
RECOMMENDED = ["msToken", "odin_tt", "Uifid", "UIFID", "sessionid", "sid_tt",
               "passport_csrf_token", "ttwid"]

PLACEHOLDER = 'DOUYIN_COOKIE = ""'


def parse_cookie_string(raw: str) -> dict:
    """把 cookie 字符串解析成字典~"""
    out = {}
    for part in raw.split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        k, _, v = part.partition("=")
        k = k.strip()
        v = v.strip()
        if k:
            out[k] = v
    return out


def step1_format(raw: str) -> bool:
    print("[1/4] 格式检查")
    if not raw or not raw.strip():
        print("      ❌ 内容是空的")
        return False
    if "\n" in raw.strip():
        # 允许多行粘贴，合并
        raw = raw.strip()
    if "=" not in raw:
        print("      ❌ 没有找到 '=' —— 这看起来不是 cookie")
        print("         正确形态：名称=值; 名称=值; ...")
        return False
    cookies = parse_cookie_string(raw)
    if len(cookies) < 3:
        print(f"      ⚠️ 只解析出 {len(cookies)} 个字段，可能不完整")
    print(f"      ✅ 解析出 {len(cookies)} 个 cookie 字段")
    return True


def step2_required(cookies: dict) -> bool:
    print("[2/4] 关键字段检查")
    ok = True

    for key in REQUIRED_ANY:
        hit = [k for k in cookies if k.lower() == key.lower()]
        if hit:
            print(f"      ✅ {key} 存在（长度 {len(cookies[hit[0]])}）")
        else:
            print(f"      ❌ 缺少 {key} —— 抖音设备标识，没有它必然被风控拦截")
            ok = False

    present = [k for k in RECOMMENDED if any(kk.lower() == k.lower() for kk in cookies)]
    print(f"      其他字段: {', '.join(present) if present else '（无）'}")

    has_login = any(k.lower() in ("sessionid", "sid_tt", "sessionid_ss")
                    for k in cookies)
    if has_login:
        print("      ✅ 检测到登录态字段（sessionid / sid_tt）")
    else:
        print("      ⚠️ 没有登录态字段 —— 未登录的 cookie 可能不足以取到播放流")
        print("         建议先在浏览器里登录抖音再复制")

    return ok


def step3_write(raw: str) -> bool:
    print("[3/4] 写入配置")
    if not os.path.exists(CONFIG):
        print(f"      ❌ 找不到 {CONFIG}")
        return False

    with open(CONFIG, "r", encoding="utf-8") as f:
        content = f.read()

    # 转义，避免 cookie 里的引号破坏 python 语法
    safe = raw.replace("\\", "\\\\").replace('"', '\\"').strip()
    new_line = f'DOUYIN_COOKIE = "{safe}"'

    if PLACEHOLDER in content:
        content = content.replace(PLACEHOLDER, new_line)
    elif re.search(r'^DOUYIN_COOKIE\s*=', content, re.M):
        content = re.sub(r'^DOUYIN_COOKIE\s*=.*$', new_line, content, flags=re.M)
    else:
        content += f"\n\n# 抖音 Cookie（由 setup_douyin_cookie.py 写入）\n{new_line}\n"

    with open(CONFIG, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"      ✅ 已写入 {CONFIG}")
    print("         （该文件已被 .gitignore 忽略，不会提交到仓库）")
    return True


def step4_verify() -> bool:
    print("[4/4] 真实请求实测")
    # 清掉可能已加载的模块缓存，确保读到新配置
    for m in list(sys.modules):
        if m == "config" or m.startswith("modules."):
            del sys.modules[m]
    sys.path.insert(0, SRC)
    os.chdir(SRC)

    try:
        import asyncio

        import modules.third_party_parser as tp
        cookie = tp._douyin_cookie()
        if not cookie:
            print("      ❌ 配置里读不到 cookie（写入可能失败）")
            return False
        print(f"      配置读取成功，cookie 长度 {len(cookie)}")
        print("      正在请求抖音接口（用一个公开视频 ID 测试风控）…")

        async def probe():
            import aiohttp
            headers = tp._douyin_headers()
            api = ("https://www.douyin.com/aweme/v1/web/aweme/detail/"
                   "?aweme_id=7300000000000000000&device_platform=webapp&aid=6383")
            from modules.net_helpers import get_proxy_url
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30), trust_env=True
            ) as s:
                async with s.get(api, headers=headers,
                                proxy=get_proxy_url() or None) as r:
                    body = await r.text(errors="replace")
                    return r.status, body[:300]

        status, body = asyncio.run(probe())
        print(f"      HTTP {status}")
        if "ArgusSecurityPlugin" in body or "Uifid Not Found" in body:
            print("      ❌ 仍被风控拦截（ArgusSecurityPlugin / Uifid Not Found）")
            print("         说明这份 cookie 不足以通过风控，可能是：")
            print("           • 未登录（缺 sessionid）")
            print("           • cookie 不完整（缺 ttwid / Uifid）")
            print("           • cookie 已过期")
            return False
        if status == 200:
            print("      ✅ 风控已通过！接口正常返回")
            print("         现在可以给机器人发抖音链接试试了~")
            return True
        print(f"      ⚠️ 返回 HTTP {status}，响应片段：")
        print(f"         {body[:200]}")
        return False
    except Exception as e:
        import traceback
        print(f"      ❌ 实测时出错: {type(e).__name__}: {e}")
        traceback.print_exc()
        return False


def main():
    print("=" * 66)
    print("  抖音 Cookie 配置工具")
    print("=" * 66)
    print()
    print("⚠️ 重要：抖音链接当前**不会被解析**。")
    print("   最新表态见 README「🚫 明确不支持的平台」一节：抖音的风控要求在请求里带")
    print("   浏览器 JS 运行时生成的设备指纹（Uifid），普通 HTTP 请求带着完整 cookie")
    print("   也会被 403 拦掉，所以代码里会直接回复原因、不再尝试解析。")
    print("   本工具保留下来只用于：写入 DOUYIN_COOKIE 配置项、以及日后风控变化时")
    print("   重新做实测。它的第 4 步会真实请求一次接口，用来观察现在能不能过风控。")
    print()

    if len(sys.argv) > 1:
        raw = " ".join(sys.argv[1:])
    else:
        print("请粘贴抖音 cookie（一整行，形如 ttwid=xxx; msToken=yyy; ...）")
        print("粘贴后按回车。若终端支持，右键即可粘贴。")
        print()
        try:
            raw = input("cookie> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n已取消")
            return 1

    if not step1_format(raw):
        print()
        print("结果: ❌ 格式不对，未写入")
        return 1
    print()

    cookies = parse_cookie_string(raw)
    if not step2_required(cookies):
        print()
        print("结果: ❌ 关键字段缺失，未写入（请补齐后重试）")
        return 1
    print()

    if not step3_write(raw):
        print()
        print("结果: ❌ 写入失败")
        return 1
    print()

    ok = step4_verify()
    print()
    print("=" * 66)
    if ok:
        print("结果: ✅ cookie 写好了，而且这次实测确实过了风控")
        print("      但机器人仍然会拒绝抖音链接（LINK_UNSUPPORTED_PLATFORMS 在前拦截）")
        print("      想真正放开，需要先把它从 config.py 的该列表里去掉")
    else:
        print("结果: ⚠️ cookie 已写入，但实测未通过（详见上面的原因）")
        print("      这就是当前抖音不支持的原因；风控变化时可以重跑本脚本观察")
    print("=" * 66)
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
