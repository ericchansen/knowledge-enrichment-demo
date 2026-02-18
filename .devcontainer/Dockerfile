# Python 3.12 with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Install system dependencies required for devcontainer features
# Many features (Azure CLI, GitHub CLI, Node.js, etc.) require these packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    git \
    curl \
    wget \
    ca-certificates \
    gnupg2 \
    lsb-release \
    procps \
    apt-transport-https \
    software-properties-common \
    openssh-client \
    && rm -rf /var/lib/apt/lists/* \
    # Make /bin/sh point to bash instead of dash (required for nvm's source command)
    && ln -sf /bin/bash /bin/sh

SHELL ["/bin/bash", "-c"]

# Note: Azurite is installed via postCreateCommand after Node.js feature is available

# Set up uv environment
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Create non-root user for VS Code
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && apt-get update \
    && apt-get install -y sudo \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /workspaces

USER $USERNAME
