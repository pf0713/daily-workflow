# -*- coding: utf-8 -*-
"""
每日自动化推文系统
每天14:00自动执行:
  1. 爬取当日热点
  2. 生成养生类推文
  3. 配图 + 推送公众号草稿
  4. 飞书通知用户审核
  5. 等待远程指令（发布/关机等）
"""
import json
import os
import sys
import io
import time
import datetime
import subprocess
import requests as req

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ============ 配置 ============
WORK_DIR = r"C:\Users\86151\Desktop\CC实验"
IMG_DIR = os.path.join(WORK_DIR, "推文配图")

# 公众号 — 从环境变量读取
WX_APP_ID = os.getenv("WX_APP_ID", "")
WX_APP_SECRET = os.getenv("WX_APP_SECRET", "")

# 飞书 Bot — 从环境变量读取
FS_APP_ID = os.getenv("FS_APP_ID", "")
FS_APP_SECRET = os.getenv("FS_APP_SECRET", "")
FS_CHAT_ID = os.getenv("FS_CHAT_ID", "")
FS_BASE = "https://open.feishu.cn/open-apis"

WX_BASE = "https://api.weixin.qq.com/cgi-bin"

LOG_FILE = os.path.join(WORK_DIR, "daily_log.txt")


def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ============ 热点爬取 ============
def fetch_hot_topics():
    """爬取今日热点，返回话题列表"""
    log("爬取今日热点...")

    topics = []

    # 尝试多个 API
    apis = [
        "https://api-hot.imsyy.top/douyin?cache=true",
        "https://tenapi.cn/v2/douyinhot",
    ]

    for url in apis:
        try:
            r = req.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200:
                data = r.json()
                items = data.get("data", [])
                for item in items[:20]:
                    t = item.get("title") or item.get("name") or item.get("word", "")
                    if t:
                        topics.append(t)
                if len(topics) >= 10:
                    break
        except Exception as e:
            log(f"  API失败: {url} -> {e}")

    if len(topics) < 5:
        # 备用固定热点
        today = datetime.date.today()
        topics = [
            f"{today.month}月{today.day}日 今日热搜",
            "小满节气养生正当时",
            "初夏养生祛湿指南",
            "夏季饮食安全提醒",
            "免疫力提升小妙招",
        ]

    log(f"  获取到 {len(topics)} 条热点")
    return topics


# ============ 图片生成 ============
def generate_images():
    """生成推文配图"""
    from PIL import Image, ImageDraw, ImageFont

    os.makedirs(IMG_DIR, exist_ok=True)
    today = datetime.date.today()
    date_str = f"{today.month}月{today.day}日"

    FONT_PATHS = [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/msyhbd.ttc",
    ]

    def load_font(size):
        for fp in FONT_PATHS:
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
        return ImageFont.load_default()

    # 封面
    w, h = 900, 500
    img = Image.new("RGB", (w, h), "#2d5016")
    draw = ImageDraw.Draw(img)
    for i in range(3):
        r = 200 - i * 50
        c = (45 + i * 20, 80 + i * 20, 22 + i * 15)
        draw.ellipse([w // 2 - r, h // 2 - r, w // 2 + r, h // 2 + r], outline=c, width=3)
    fb = load_font(52)
    title = "今日养生"
    bbox = draw.textbbox((0, 0), title, font=fb)
    tw = bbox[2] - bbox[0]
    draw.text(((w - tw) // 2, 130), title, fill="#ffffff", font=fb)
    fm = load_font(28)
    sub = f"{date_str} 热点养生指南"
    bbox = draw.textbbox((0, 0), sub, font=fm)
    sw = bbox[2] - bbox[0]
    draw.text(((w - sw) // 2, 230), sub, fill="#c8e6a0", font=fm)
    fs = load_font(22)
    tag = "人生小满胜万全"
    bbox = draw.textbbox((0, 0), tag, font=fs)
    tw2 = bbox[2] - bbox[0]
    draw.text(((w - tw2) // 2, 350), tag, fill="#90b860", font=fs)
    img.save(os.path.join(IMG_DIR, "cover.png"))

    # 段落配图
    sections = [
        ("今日热点 × 养生", f"{date_str} 热搜里的健康提醒", "section1.png"),
        ("热点解读", "这些新闻跟你身体有关", "section2.png"),
        ("养生干货", "简单实用的日常养生法", "section3.png"),
        ("今晚，关灯睡觉", "身体好，一切都好", "section4.png"),
    ]

    for title, sub, fname in sections:
        w2, h2 = 800, 400
        img2 = Image.new("RGB", (w2, h2), "#f5f0e8")
        draw2 = ImageDraw.Draw(img2)
        draw2.rectangle([0, 0, 8, h2], fill="#6ba33e")
        fbig = load_font(36)
        draw2.text((60, 130), title, fill="#2d5016", font=fbig)
        fsm = load_font(22)
        draw2.text((60, 200), sub, fill="#888888", font=fsm)
        img2.save(os.path.join(IMG_DIR, fname))

    log("  配图生成完毕")


# ============ 推文生成 ============
def build_article(topics, img_urls):
    """根据热点生成推文HTML"""
    today = datetime.date.today()
    date_str = f"{today.month}月{today.day}日"
    weekday = ["一", "二", "三", "四", "五", "六", "日"][today.weekday()]
    topic_str = "、".join(topics[:5])

    html = f"""<section style="margin:0;padding:0;">
  <p style="text-align:center;"><img src="{img_urls['cover.png']}" style="width:100%;display:block;"></p>
</section>

<section style="padding:10px 16px;">
  <p style="color:#333333;font-size:15px;line-height:1.8;">{date_str} 星期{weekday}，又到了每天的热点养生时间。<br>今天热搜上都在聊：<strong>{topic_str}</strong></p>
  <p style="color:#333333;font-size:15px;line-height:1.8;">别光看热闹。每一条热搜背后，都藏着一个健康提醒。</p>
</section>

<section style="padding:0 16px;margin-top:15px;">
  <p style="text-align:center;"><img src="{img_urls['section1.png']}" style="width:100%;display:block;"></p>
  <h2 style="color:#2d5016;font-size:18px;margin:10px 0;">热搜里的养生密码</h2>
  <p style="color:#333333;font-size:15px;line-height:1.8;">今天的热搜榜，咱们一条条拆开看。</p>
  <p style="color:#333333;font-size:15px;line-height:1.8;"><strong style="color:#2d5016;">天气类热搜 → 湿气警报。</strong>每年这个时候，全国多地暴雨、高温交替，湿邪最盛。你是不是也觉得浑身发沉、没精神、舌苔厚腻？那就是湿气在作怪。<br>记住三件事：少喝冰的、少吃甜的、晚上泡泡脚。</p>
  <p style="color:#333333;font-size:15px;line-height:1.8;"><strong style="color:#2d5016;">食品安全热搜 → 嘴要管严。</strong>天热了，食物变质快，外面吃的喝的都长个心眼。别贪便宜买来路不明的东西——你跟养生也一样，平时糊弄身体，迟早跟你算总账。</p>
  <p style="color:#333333;font-size:15px;line-height:1.8;"><strong style="color:#2d5016;">健康类热搜 → 免疫力是硬通货。</strong>不管什么病毒变异、什么疫情反复，免疫力才是你最好的防线。而免疫力靠什么？睡好、吃好、心情好——就这么简单。</p>
</section>

<section style="padding:0 16px;margin-top:20px;">
  <p style="text-align:center;"><img src="{img_urls['section2.png']}" style="width:100%;display:block;"></p>
  <h2 style="color:#2d5016;font-size:18px;margin:10px 0;">今日养生重点</h2>
  <p style="color:#333333;font-size:15px;line-height:1.8;">根据今天的热点和时节，给你划三个重点：</p>
  <p style="color:#2d5016;font-size:16px;"><strong>一、祛湿是头等大事</strong></p>
  <p style="color:#333333;font-size:15px;line-height:1.8;">姜枣茶喝起来。三片姜、两颗枣，早上煮一杯。从现在喝到三伏，效果你身体自己会告诉你。</p>
  <p style="color:#2d5016;font-size:16px;"><strong>二、管住嘴</strong></p>
  <p style="color:#333333;font-size:15px;line-height:1.8;">冰啤酒、冰奶茶、冰西瓜——你一时爽，脾胃哭一天。天气越热，越要吃温的。</p>
  <p style="color:#2d5016;font-size:16px;"><strong>三、睡个好觉</strong></p>
  <p style="color:#333333;font-size:15px;line-height:1.8;">晚上十点放下手机。睡好了，湿气少一半，脾气好一半，脸都嫩一截。</p>
</section>

<section style="padding:0 16px;margin-top:20px;">
  <p style="text-align:center;"><img src="{img_urls['section3.png']}" style="width:100%;display:block;"></p>
  <h2 style="color:#2d5016;font-size:18px;margin:10px 0;">今日小贴士</h2>
  <p style="color:#333333;font-size:15px;line-height:1.8;">· 午时（11-13点）眯15分钟，顶晚上两小时<br>· 晚饭后散步20分钟，助消化又祛湿<br>· 睡前艾叶泡脚，水温40度，15分钟就够<br>· 心情不好就放下手机，出门走两步</p>
</section>

<section style="padding:0 16px;margin-top:20px;">
  <p style="text-align:center;"><img src="{img_urls['section4.png']}" style="width:100%;display:block;"></p>
  <h2 style="color:#2d5016;font-size:18px;margin:10px 0;">最后一句</h2>
  <p style="color:#333333;font-size:15px;line-height:1.8;">热搜天天换，健康就那几条。<br>睡好、吃对、心放宽——比什么灵丹妙药都管用。</p>
  <p style="text-align:center;color:#2d5016;font-size:17px;margin:15px 0;"><strong>人生小满胜万全。对自己好一点，从今晚早睡开始。</strong></p>
  <p style="text-align:center;color:#333333;font-size:18px;margin:15px 0;"><strong>今晚十点，放下手机，关灯睡觉。</strong></p>
</section>

<section style="margin-top:25px;padding:15px 16px;background:#f5f0e8;">
  <p style="color:#999999;font-size:13px;text-align:center;">关注我，一个只说人话的养生号。<br>每天14:00自动生成，人工审核发布。</p>
</section>"""

    # 保存本地备份
    html_path = os.path.join(WORK_DIR, f"推文_{date_str}_公众号排版.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(f"<!DOCTYPE html><html><head><meta charset=\"utf-8\"></head><body>{html}</body></html>")

    return html, html_path


# ============ 公众号操作 ============
def get_wx_token():
    r = req.get(f"{WX_BASE}/token", params={
        "grant_type": "client_credential",
        "appid": WX_APP_ID,
        "secret": WX_APP_SECRET,
    })
    return r.json()["access_token"]


def upload_images(token):
    """上传配图到微信CDN"""
    img_urls = {}
    for f in ["cover.png", "section1.png", "section2.png", "section3.png", "section4.png"]:
        path = os.path.join(IMG_DIR, f)
        with open(path, "rb") as fp:
            r = req.post(
                f"{WX_BASE}/media/uploadimg?access_token={token}",
                files={"media": (f, fp, "image/png")},
            )
        resp = r.json()
        if "url" in resp:
            img_urls[f] = resp["url"]
        else:
            raise Exception(f"图片上传失败: {f} {resp}")
    return img_urls


def upload_cover(token):
    """上传封面永久素材"""
    path = os.path.join(IMG_DIR, "cover.png")
    r = req.post(
        f"{WX_BASE}/material/add_material?access_token={token}&type=image",
        files={"media": ("cover.png", open(path, "rb"), "image/png")},
    )
    resp = r.json()
    if "media_id" in resp:
        return resp["media_id"]
    raise Exception(f"封面上传失败: {resp}")


def create_draft(token, articles_data):
    """创建草稿"""
    body = json.dumps(articles_data, ensure_ascii=False).encode("utf-8")
    r = req.post(
        f"{WX_BASE}/draft/add?access_token={token}",
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    resp = r.json()
    if "media_id" in resp:
        return resp["media_id"]
    raise Exception(f"草稿创建失败: {resp}")


# ============ 飞书通知 ============
def get_fs_token():
    r = req.post(
        f"{FS_BASE}/auth/v3/tenant_access_token/internal",
        json={"app_id": FS_APP_ID, "app_secret": FS_APP_SECRET},
    )
    return r.json()["tenant_access_token"]


def send_fs_message(token, text):
    req.post(
        f"{FS_BASE}/im/v1/messages",
        headers={"Authorization": f"Bearer {token}"},
        params={"receive_id_type": "chat_id"},
        json={
            "receive_id": FS_CHAT_ID,
            "msg_type": "text",
            "content": json.dumps({"text": text}),
        },
    )


def get_fs_messages(token, page_size=5):
    r = req.get(
        f"{FS_BASE}/im/v1/messages",
        headers={"Authorization": f"Bearer {token}"},
        params={
            "container_id_type": "chat",
            "container_id": FS_CHAT_ID,
            "sort_type": "ByCreateTimeDesc",
            "page_size": page_size,
        },
    )
    return r.json().get("data", {}).get("items", [])


# ============ 远程命令 ============
def execute_command(cmd):
    """执行用户远程命令"""
    cmd = cmd.strip().lower()
    if cmd in ["发布", "发", "y", "yes", "ok", "publish"]:
        log("用户命令: 发布推文")
        return "publish"

    elif cmd in ["不发布", "不发", "n", "no", "否", "拒绝"]:
        log("用户命令: 不发布")
        return "reject"

    elif cmd in ["关机", "关", "shutdown", "sd"]:
        log("用户命令: 远程关机")
        return "shutdown"

    elif cmd in ["重写", "重来", "rewrite", "redo"]:
        log("用户命令: 重写推文")
        return "rewrite"

    elif cmd in ["状态", "status"]:
        return "status"

    else:
        return None


# ============ 主流程 ============
def main():
    log("=" * 50)
    log("每日推文自动化启动")
    today = datetime.date.today()
    date_str = f"{today.month}月{today.day}日"
    log(f"日期: {date_str}")

    try:
        # 1. 爬热点
        log("--- 第1步: 爬取热点 ---")
        topics = fetch_hot_topics()

        # 2. 生成配图
        log("--- 第2步: 生成配图 ---")
        generate_images()

        # 3. 获取公众号token + 上传图片
        log("--- 第3步: 上传图片到公众号 ---")
        wx_token = get_wx_token()
        log(f"  公众号Token: {wx_token[:20]}...")
        img_urls = upload_images(wx_token)
        log(f"  图片上传完毕 ({len(img_urls)}张)")

        # 4. 生成推文
        log("--- 第4步: 生成推文 ---")
        html, html_path = build_article(topics, img_urls)
        log(f"  推文已保存: {html_path}")

        # 5. 上传封面 + 创建草稿
        log("--- 第5步: 推送草稿到公众号 ---")
        thumb_id = upload_cover(wx_token)
        log(f"  封面media_id: {thumb_id[:40]}...")

        draft_data = {
            "articles": [{
                "title": f"{date_str} 热点养生 | 看完早点睡",
                "author": "杨",
                "digest": "人生小满胜万全，每晚十点关灯睡觉",
                "content": html,
                "content_source_url": "",
                "thumb_media_id": thumb_id,
                "need_open_comment": 1,
                "only_fans_can_comment": 0,
            }]
        }
        draft_id = create_draft(wx_token, draft_data)
        log(f"  草稿创建成功! media_id: {draft_id}")

        # 6. 飞书通知用户
        log("--- 第6步: 飞书通知 ---")
        fs_token = get_fs_token()
        log(f"  飞书Token: {fs_token[:20]}...")

        notify_msg = (
            f"【每日推文已生成】\n"
            f"日期: {date_str}\n"
            f"标题: {date_str} 热点养生 | 看完早点睡\n"
            f"状态: 已推送至公众号草稿箱\n"
            f"\n"
            f"回复以下命令:\n"
            f"  [发布] - 审核通过，发布推文\n"
            f"  [不发] - 不发布，丢弃本篇\n"
            f"  [重写] - 重新生成推文\n"
            f"  [关机] - 远程关闭电脑\n"
            f"  [状态] - 查看当前状态"
        )
        send_fs_message(fs_token, notify_msg)
        log("  已发送飞书通知")

        # 7. 等待用户指令（最长2小时）
        log("--- 第7步: 等待用户指令 ---")
        log("  轮询飞书消息，等待命令...")

        last_id = ""
        deadline = time.time() + 7200  # 2小时
        fs_token_refresh = time.time()

        while time.time() < deadline:
            # 每30分钟刷新飞书token
            if time.time() - fs_token_refresh > 1800:
                fs_token = get_fs_token()
                fs_token_refresh = time.time()

            try:
                msgs = get_fs_messages(fs_token)
                new_msgs = [
                    m for m in msgs
                    if m["message_id"] > (last_id or "")
                    and m.get("sender", {}).get("id_type") != "app"
                ]
                if new_msgs:
                    last_id = new_msgs[0]["message_id"]

                for msg in reversed(new_msgs):
                    try:
                        content = json.loads(msg["body"]["content"])
                        text = content.get("text", "").strip()
                    except Exception:
                        text = ""

                    if not text:
                        continue

                    log(f"  收到飞书消息: {text}")
                    cmd = execute_command(text)

                    if cmd == "publish":
                        send_fs_message(fs_token, "收到! 正在发布推文...")
                        # 尝试发布
                        pub_body = json.dumps({"media_id": draft_id}, ensure_ascii=False).encode("utf-8")
                        r = req.post(
                            f"{WX_BASE}/freepublish/submit?access_token={wx_token}",
                            data=pub_body,
                            headers={"Content-Type": "application/json; charset=utf-8"},
                        )
                        pub_resp = r.json()
                        if pub_resp.get("errcode") == 0:
                            send_fs_message(fs_token, "推文已提交发布审核!")
                            log("  推文已发布")
                        else:
                            send_fs_message(fs_token, f"自动发布失败，请手动去后台发布。\n错误: {pub_resp.get('errmsg', '')}")
                            log(f"  发布失败: {pub_resp}")
                        return

                    elif cmd == "reject":
                        send_fs_message(fs_token, "已收到，本篇推文不发布。")
                        log("  用户拒绝发布")
                        return

                    elif cmd == "rewrite":
                        send_fs_message(fs_token, "收到，正在重新生成推文...（暂未实现自动重写，请手动发起）")
                        # 这里可以调用Claude重新生成
                        log("  用户要求重写")
                        return

                    elif cmd == "shutdown":
                        send_fs_message(fs_token, "收到关机命令。电脑将在60秒后关机。\n回复 '取消关机' 可取消。")
                        log("  执行关机...")
                        os.system("shutdown /s /t 60 /c \"每日推文系统远程关机\"")
                        return

                    elif cmd == "status":
                        send_fs_message(fs_token,
                            f"当前状态:\n"
                            f"  日期: {date_str}\n"
                            f"  草稿ID: {draft_id[:30]}...\n"
                            f"  等待命令中..."
                        )

            except Exception as e:
                log(f"  轮询异常: {e}")

            time.sleep(5)

        # 超时
        log("  等待超时（2小时），自动结束")
        send_fs_message(fs_token, f"【超时提醒】{date_str}推文已等待2小时无指令，草稿保留在公众号后台，请手动处理。")

    except Exception as e:
        log(f"!!! 流程异常: {e}")
        import traceback
        log(traceback.format_exc())
        # 尝试通知用户
        try:
            fs_token = get_fs_token()
            send_fs_message(fs_token, f"【系统异常】{date_str}推文生成失败: {e}\n请检查电脑。")
        except Exception:
            pass


if __name__ == "__main__":
    main()
