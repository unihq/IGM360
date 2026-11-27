# syntax=docker/dockerfile:1
# Image IGM360: Python 3.12 bản gọn + Node.js 22 (để chạy Claude Code CLI, Codex CLI).
# Mã để chỉ đọc; mọi dữ liệu nằm ở ổ gắn ngoài /dulieu và 02 ổ giữ đăng nhập gói AI.
# Gói hệ điều hành cài thêm ngoài image nền: chỉ git (0.10.0, QĐ474 – kho git bộ não), ghim đúng bản.

# 0.7.9 lớp 3 (QĐ213, QĐ215): ảnh liền trước trên kho ảnh (công khai, không cần khóa). Mã của nó được để sẵn ở
# /app/ban_truoc để nút "Quay về bản trước" chạy lại bản đó mà không cần mạng, không cần quyền Docker.
ARG ANH_TRUOC=ghcr.io/unihq/igm360:latest
FROM ${ANH_TRUOC} AS anh_truoc

# 0.8.2 (QĐ258, PTD-13): ảnh nền ghim theo mã sha256, không theo nhãn. Nhãn trên Docker Hub được phát hành lại không báo
# trước (0.8.1: nhãn python đổi giữa 02 lần đóng gói làm cả 17 lớp đổi, máy chủ tải lại 474,5 MB). Nâng nền có chủ đích:
# Dependabot (.github/dependabot.yml, mục docker, thứ Hai hằng tuần) đề xuất đổi mã sha256, anh duyệt gộp.

# Nguồn Node.js 22: lấy từ image chính thức, ghim bản vá bảo mật (22.23.4, phát hành 21/10/2026).
FROM node:22.23.4-bookworm-slim@sha256:5ec23b7c622b00547753bc6ffd78085dd868a68aeb41c8e0a1418f033e13d96d AS nguon_node

# 0.8.0 (QĐ229): ghim nhãn Debian trixie để giữ SQLite ≥ 3.43 (cụm tìm chữ H08 dùng `contentless_delete`).
FROM python:3.12-slim-trixie@sha256:37fc60d303cb9294d3718b5b48998a0210bb1c73611c1399ef5eb7964c0536e5

LABEL org.opencontainers.image.title="IGM360" \
      org.opencontainers.image.description="Phần mềm quản trị vận hành 360 thương mại điện tử" \
      org.opencontainers.image.source="https://github.com/unihq/IGM360" \
      org.opencontainers.image.licenses="AGPL-3.0-only"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

COPY --from=nguon_node /usr/local/bin/node /usr/local/bin/node
COPY --from=nguon_node /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/npm
RUN ln -sf /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -sf /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx \
    && node --version

WORKDIR /app

# 0.10.0 (QĐ474, QĐ626): git cho kho bộ não (`maychu/dulieu/bonao.py`: mỗi bộ não 01 kho git, hoàn tác từng mẻ học).
# Ghim đúng bản Debian trixie đã đo ở thử thật ⑤ (+35 MB tải, +140 MB đĩa); --no-install-recommends, xóa danh sách apt.
# Lớp ít đổi nên đặt trước thư viện Python (QĐ258). Nâng git = đổi số bản ở dòng dưới, anh duyệt.
RUN apt-get update \
    && apt-get install -y --no-install-recommends "git=1:2.47.3-0+deb13u1" \
    && rm -rf /var/lib/apt/lists/* \
    && git --version

# 0.8.2 (QĐ258): thứ tự lớp từ ít đổi đến hay đổi: thư viện Python → Codex CLI → Claude CLI → mã.
# Thư viện Python để riêng 01 lớp: sửa mã không phải cài lại thư viện.
COPY requirements.txt ./
RUN pip install -r requirements.txt

# 0.8.2 (QĐ258): 02 CLI ghim số bản, không lấy bản mới nhất mỗi lần đóng gói (trước đây gần như lần nào cũng gặp bản CLI
# mới → tải lại ≈ 383 MB). Nâng = đổi 02 dòng ARG dưới đây (cách nâng tự động, nút nâng ngay: chờ anh chốt sau KT-QĐ260).
# Codex ra bản ít hơn Claude (11 / 19 bản trong 30 ngày tới 24/11/2026) nên đặt trước.
# Codex CLI: đăng nhập gói ChatGPT (nguồn thứ hai của Cổng AI).
ARG CODEX_CLI_VERSION=0.172.0
RUN npm install -g "@openai/codex@${CODEX_CLI_VERSION}" \
    && npm cache clean --force \
    && codex --version

# Claude Code CLI: thư viện claude-agent-sdk cần nó để chạy bằng gói Claude.
ARG CLAUDE_CLI_VERSION=2.1.331
RUN npm install -g "@anthropic-ai/claude-code@${CLAUDE_CLI_VERSION}" \
    && npm cache clean --force \
    && claude --version

COPY VERSION LICENSE ./
COPY maychu ./maychu

# 0.7.9 lớp 3: chọn mã bản liền trước. Ảnh `latest` đã là chính bản này (đóng lại lần 02) thì lấy bản trước của nó;
# ảnh trước không có mã (lần đầu) thì không có nút quay về. Chỉ chép mã và số bản, không chép thư viện.
COPY --from=anh_truoc /app /tmp/anh_truoc
RUN set -e; t=/tmp/anh_truoc; dang="$(tr -d ' \n\r' < VERSION)"; \
    if [ -f "$t/VERSION" ] && [ "$(tr -d ' \n\r' < $t/VERSION)" = "$dang" ]; then t=/tmp/anh_truoc/ban_truoc; fi; \
    if [ -f "$t/VERSION" ] && [ -d "$t/maychu" ]; then \
        mkdir -p ban_truoc && cp -r "$t/maychu" "$t/VERSION" ban_truoc/ && echo "Bản trước: $(cat ban_truoc/VERSION)"; \
    else echo "Không có bản trước"; fi; \
    rm -rf /tmp/anh_truoc

# Chạy bằng người dùng thường, không phải root.
RUN useradd -u 10001 -m -d /home/igm igm \
    && mkdir -p /dulieu /home/igm/.claude /home/igm/.codex \
    && chown -R igm:igm /dulieu /home/igm

# QĐ173 (Y29): CLAUDE_CONFIG_DIR = ổ lưu /home/igm/.claude để tệp hồ sơ `.claude.json` của tài khoản Claude 01
# (tên, tên gói, email) nằm trong ổ lưu, không mất khi dựng lại vùng chứa. Tệp mã đăng nhập `.credentials.json`
# vẫn ở đúng chỗ cũ (CLI đặt trong thư mục này dù có biến hay không) nên đăng nhập hiện có dùng tiếp.
# Tài khoản 02 trở đi: phần mềm tự đặt lại biến về thư mục `taikhoan_NN` của từng tài khoản.
ENV IGM360_CONG=8360 \
    IGM360_THUMUC_DULIEU=/dulieu \
    HOME=/home/igm \
    CLAUDE_CONFIG_DIR=/home/igm/.claude

USER igm

VOLUME ["/dulieu", "/home/igm/.claude", "/home/igm/.codex"]

EXPOSE 8360

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8360/suckhoe',timeout=4).status==200 else 1)" || exit 1

# Chỉ tin địa chỉ IP thật do cổng HTTPS chuyển tới: địa chỉ cổng đặt ở biến FORWARDED_ALLOW_IPS (tệp compose).
# Mặc định chỉ tin chính máy, không tin nguồn nào khác.
ENV FORWARDED_ALLOW_IPS=127.0.0.1
# 0.7.9 lớp 3: `maychu.chay` chọn bản chạy (bản này, hoặc bản trước khi anh bấm Quay về bản trước) rồi chạy uvicorn.
CMD ["python", "-m", "maychu.chay"]
