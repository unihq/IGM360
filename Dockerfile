# syntax=docker/dockerfile:1
# Image IGM360: Python 3.12 bản gọn + Node.js 22 (để chạy Claude Code CLI, Codex CLI).
# Mã để chỉ đọc; mọi dữ liệu nằm ở ổ gắn ngoài /dulieu và 02 ổ giữ đăng nhập gói AI.
# Không cài thêm gói hệ điều hành nào ngoài image nền.

# Nguồn Node.js 22: lấy từ image chính thức, ghim bản vá bảo mật (22.23.4, phát hành 21/10/2026).
FROM node:22.23.4-bookworm-slim AS nguon_node

FROM python:3.12-slim

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

# Claude Code CLI: thư viện claude-agent-sdk cần nó để chạy bằng gói Claude.
# Luồng đóng image truyền số phiên bản thật (lấy bản mới nhất lúc đóng).
ARG CLAUDE_CLI_VERSION=latest
RUN npm install -g "@anthropic-ai/claude-code@${CLAUDE_CLI_VERSION}" \
    && npm cache clean --force \
    && claude --version

# Codex CLI: đăng nhập gói ChatGPT (nguồn thứ hai của Cổng AI).
ARG CODEX_CLI_VERSION=latest
RUN npm install -g "@openai/codex@${CODEX_CLI_VERSION}" \
    && npm cache clean --force \
    && codex --version

WORKDIR /app

# Thư viện Python để riêng 01 lớp: sửa mã không phải cài lại thư viện.
COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY VERSION LICENSE ./
COPY maychu ./maychu

# Chạy bằng người dùng thường, không phải root.
RUN useradd -u 10001 -m -d /home/igm igm \
    && mkdir -p /dulieu /home/igm/.claude /home/igm/.codex \
    && chown -R igm:igm /dulieu /home/igm

ENV IGM360_CONG=8360 \
    IGM360_THUMUC_DULIEU=/dulieu \
    HOME=/home/igm

USER igm

VOLUME ["/dulieu", "/home/igm/.claude", "/home/igm/.codex"]

EXPOSE 8360

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8360/suckhoe',timeout=4).status==200 else 1)" || exit 1

CMD ["python", "-m", "uvicorn", "maychu.khoidong:app", "--host", "0.0.0.0", "--port", "8360", "--proxy-headers", "--forwarded-allow-ips", "*"]
