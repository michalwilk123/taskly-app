FROM node:24.13.0-bookworm-slim
RUN npm install --global --ignore-scripts --no-audit --no-fund @earendil-works/pi-coding-agent@1.4.0
ENV HOME=/tmp/pi PI_CODING_AGENT_DIR=/tmp/pi/agent
WORKDIR /workspace
ENTRYPOINT ["pi"]
