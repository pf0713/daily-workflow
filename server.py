"""
Feishu <-> Claude Code Bridge Server
接收飞书消息 → Claude CLI 处理 → 返回结果
"""
import json
import os
import subprocess
from pathlib import Path
from threading import Thread

import lark_oapi as lark
from lark_oapi.api.im.v1 import (
    CreateMessageRequest,
    CreateMessageRequestBody,
    P2ImMessageReceiveV1,
)
from lark_oapi.core.utils.decryptor import AESCipher
from dotenv import load_dotenv
from fastapi import FastAPI, Request
import uvicorn

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

APP_ID = os.getenv("FEISHU_APP_ID", "")
APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")
ENCRYPT_KEY = os.getenv("FEISHU_ENCRYPT_KEY", "")
WORK_DIR = Path(os.getenv("WORK_DIR", str(Path.home() / "Desktop")))

app = FastAPI(title="Feishu-Claude Bridge")
_processed: set[str] = set()

# Initialize decryptor if encrypt key is set
aes = AESCipher(ENCRYPT_KEY) if ENCRYPT_KEY else None


def get_client():
    return lark.Client.builder().app_id(APP_ID).app_secret(APP_SECRET).build()


def send_message(chat_id: str, content: str):
    """Send a text message back to Feishu chat."""
    client = get_client()
    body = CreateMessageRequestBody()
    body.receive_id = chat_id
    body.msg_type = "text"
    body.content = json.dumps({"text": content})
    req = (
        CreateMessageRequest.builder()
        .receive_id_type("chat_id")
        .request_body(body)
        .build()
    )
    resp = client.im.v1.message.create(req)
    if not resp.success():
        print(f"[ERROR] Send failed: code={resp.code} msg={resp.msg}")
    return resp


def run_claude(prompt: str) -> str:
    """Execute Claude CLI and return response."""
    try:
        result = subprocess.run(
            ["claude", "-p", prompt],
            cwd=str(WORK_DIR),
            capture_output=True,
            text=True,
            timeout=300,
            env={**os.environ, "NO_COLOR": "1"},
        )
        if result.returncode != 0:
            return f"[Claude 出错] {result.stderr[:500]}"
        return result.stdout.strip() or "[Claude 返回空结果]"
    except subprocess.TimeoutExpired:
        return "[Claude 请求超时 (5分钟)]"
    except FileNotFoundError:
        return "[未找到 Claude CLI，请先安装 Claude Code]"


def handle_message(event_data: dict):
    """Process im.message.receive_v1 event."""
    try:
        evt = P2ImMessageReceiveV1(event_data)
    except Exception as e:
        print(f"[WARN] Failed to parse event: {e}")
        return

    if not evt.event or not evt.event.message:
        return

    msg = evt.event.message
    msg_id = msg.message_id
    chat_id = msg.chat_id

    if msg_id in _processed:
        return
    _processed.add(msg_id)
    if len(_processed) > 1000:
        _processed.clear()

    # Parse message text
    try:
        content = json.loads(msg.content)
        user_text = content.get("text", "")
    except (json.JSONDecodeError, TypeError):
        user_text = msg.content or ""

    if not user_text or not user_text.strip():
        return

    print(f"[MSG] chat={chat_id} text={user_text[:100]}")

    # Send "thinking" indicator
    send_message(chat_id, "正在处理...")

    # Process with Claude
    reply = run_claude(user_text)

    # Send reply
    send_message(chat_id, reply)


@app.post("/feishu/event")
async def feishu_event(request: Request):
    """Receive and dispatch Feishu events."""
    body = await request.body()
    data = json.loads(body)

    # =========== Step 1: Decrypt if encrypted ===========
    encrypted = data.get("encrypt")
    if encrypted and aes:
        try:
            decrypted = aes.decrypt_str(encrypted)
            data = json.loads(decrypted)
        except Exception as e:
            print(f"[ERROR] Decrypt failed: {e}")
            return {"code": 1, "msg": "decrypt failed"}

    # =========== Step 2: URL verification ===========
    if data.get("type") == "url_verification":
        challenge = data.get("challenge", "")
        print(f"[INFO] URL verification, challenge={challenge[:20]}...")
        return {"challenge": challenge}

    # =========== Step 3: Dispatch event ===========
    schema = data.get("schema", "")
    evt_type = data.get("header", {}).get("event_type", "")
    print(f"[EVENT] schema={schema} type={evt_type}")

    if evt_type == "im.message.receive_v1":
        Thread(target=handle_message, args=(data,), daemon=True).start()

    return {"code": 0}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "app_id": APP_ID[:8] + "..." if APP_ID else "not set",
        "has_encrypt_key": bool(ENCRYPT_KEY),
        "work_dir": str(WORK_DIR),
    }


if __name__ == "__main__":
    print("Feishu-Claude Bridge starting...")
    print(f"  APP_ID: {APP_ID[:8]}..." if APP_ID else "  APP_ID: NOT SET")
    print(f"  Encrypt key: {'set' if ENCRYPT_KEY else 'NOT SET'}")
    print(f"  Work dir: {WORK_DIR}")
    uvicorn.run(app, host="0.0.0.0", port=8888)
