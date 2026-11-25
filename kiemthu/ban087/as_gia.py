"""`codex app-server` giả cho bài kiểm N0 mốc 3 (không gọi hãng, không đọc mạng): nói JSON từng dòng qua stdin/stdout
theo các phương thức của bản ghim rust-v0.172.0. Chạy: python as_gia.py <kịch bản> <tệp ghi> [đối số...].
Tệp ghi nhận tham số `thread/start` và câu trả lời của bên gọi cho yêu cầu duyệt (để bài kiểm đối chiếu).
"""
import json
import sys
import time

KICH_BAN, GHI = sys.argv[1], sys.argv[2]
DA_GHI = {}


def ra(o, nghi=0.0):
    sys.stdout.write(json.dumps(o, ensure_ascii=False) + "\n")
    sys.stdout.flush()
    if nghi:
        time.sleep(nghi)


def luu():
    with open(GHI, "w", encoding="utf-8") as f:
        json.dump(DA_GHI, f, ensure_ascii=False)


def doc():
    dong = sys.stdin.readline()
    if not dong:
        sys.exit(0)
    return json.loads(dong)


def main():
    if KICH_BAN == "thoat":
        sys.exit(3)
    while True:
        m = doc()
        pt = m.get("method")
        if pt == "initialize":
            if KICH_BAN == "khong_tra_loi":
                time.sleep(120)
            ra({"id": m["id"], "result": {"userAgent": "gia"}})
        elif pt == "thread/start":
            DA_GHI["thread_start"] = m["params"]
            luu()
            ra({"id": m["id"], "result": {"thread": {"id": "luong-1"}, "model": m["params"].get("model") or "gpt-gia"}})
        elif pt == "turn/start":
            DA_GHI["cau"] = m["params"]["input"][0]["text"]
            luu()
            ra({"id": m["id"], "result": {"turn": {"id": "luot-1"}}})
            break
    tb = lambda pt, p, nghi=0.0: ra({"method": pt, "params": {"threadId": "luong-1", "turnId": "luot-1", **p}}, nghi)  # noqa: E731
    ra({"id": 99, "method": "item/commandExecution/requestApproval", "params": {"threadId": "luong-1"}})   # yêu cầu duyệt
    DA_GHI["tra_duyet"] = doc()
    luu()
    tb("item/started", {"item": {"type": "webSearch", "id": "w1"}})
    if KICH_BAN == "het_hanmuc":
        tb("turn/completed", {"turn": {"id": "luot-1", "status": "failed", "error": {"message": "You've hit your usage limit"}}})
        return
    for manh in ("Xin ", "chào ", "bạn"):
        tb("item/agentMessage/delta", {"itemId": "m1", "delta": manh}, 0.3)
    if KICH_BAN == "ngu":
        time.sleep(120)
    tb("item/completed", {"item": {"type": "agentMessage", "id": "m1", "text": "Xin chào bạn"}})
    tb("item/completed", {"item": {"type": "agentMessage", "id": "m2", "text": "Đoạn sau"}})
    tb("thread/tokenUsage/updated", {"tokenUsage": {"total": {"inputTokens": 7, "outputTokens": 2, "reasoningOutputTokens": 1},
                                                    "last": {}}})
    ra({"method": "account/rateLimits/updated", "params": {"rateLimits": {
        "primary": {"usedPercent": 40, "windowDurationMins": 300, "resetsAt": int(time.time()) + 3600}}}})
    tb("error", {"error": {"message": "mất kết nối, thử lại"}, "willRetry": True})
    tb("turn/completed", {"turn": {"id": "luot-1", "status": "completed"}})
    time.sleep(120)   # app-server thật vẫn chạy sau lượt: bên gọi phải tự dừng (K2)


if __name__ == "__main__":
    main()
