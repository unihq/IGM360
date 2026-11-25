"""Công cụ AI giả cho bài kiểm N0 (không gọi hãng, không đọc mạng): in các dòng mẫu `stream-json` (Claude) hoặc
`--json` (Codex exec), có nghỉ giữa các dòng để kiểm việc đọc dần. Chạy: python cli_gia.py <kịch bản> [đối số CLI...].
"""
import json
import sys
import time


def in_dong(o, nghi=0.0):
    print(json.dumps(o, ensure_ascii=False), flush=True)
    if nghi:
        time.sleep(nghi)


def claude(cau):
    in_dong({"type": "system", "subtype": "init", "model": "claude-gia"})
    in_dong({"type": "stream_event", "event": {"type": "content_block_start", "content_block": {"type": "text"}}})
    for manh in ("Xin ", "chào ", "bạn"):
        in_dong({"type": "stream_event", "event": {"type": "content_block_delta",
                                                   "delta": {"type": "text_delta", "text": manh}}}, 0.3)
    in_dong({"type": "stream_event", "parent_tool_use_id": "con", "event": {
        "type": "content_block_delta", "delta": {"type": "text_delta", "text": "chữ tác tử con"}}})
    in_dong({"type": "stream_event", "event": {"type": "content_block_start",
                                               "content_block": {"type": "server_tool_use", "name": "web_search"}}})
    in_dong({"type": "result", "subtype": "success", "is_error": False, "result": "Xin chào bạn (" + str(len(cau)) + ")",
             "usage": {"input_tokens": 3, "output_tokens": 2}, "total_cost_usd": 0.0})


def codex(cau):
    in_dong({"type": "thread.started", "thread_id": "luong-gia"})
    in_dong({"type": "item.started", "item": {"type": "web_search"}}, 0.2)
    in_dong({"type": "item.completed", "item": {"type": "agent_message", "text": "Đoạn 01"}}, 0.3)
    in_dong({"type": "item.completed", "item": {"type": "agent_message", "text": "Đoạn 02"}})
    in_dong({"type": "turn.completed", "usage": {"input_tokens": 4, "output_tokens": 5}})


def ngu_lau(cau):
    in_dong({"type": "stream_event", "event": {"type": "content_block_delta",
                                               "delta": {"type": "text_delta", "text": "Bắt đầu"}}})
    time.sleep(120)


def main():
    kich_ban = sys.argv[1]
    cau = sys.stdin.read()
    {"claude": claude, "codex": codex, "ngu_lau": ngu_lau}[kich_ban](cau)


if __name__ == "__main__":
    main()
