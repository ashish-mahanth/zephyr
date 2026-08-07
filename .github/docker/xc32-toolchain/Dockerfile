# XC32 compiler, prebaked so CI never has to install it on every run.
# Device Family Packs are deliberately NOT baked in here -- they're fetched
# fresh by xc32_samples.yaml on every run instead, so builds always pick up
# the latest DFP release without needing to rebuild this image. Build and
# push manually (or via .github/workflows/xc32_toolchain_image.yaml)
# whenever XC32_VERSION changes; the resulting image is pulled by
# .github/workflows/xc32_samples.yaml.
#
# Build locally:
#   docker build -t ghcr.io/<owner>/zephyr-xc32-toolchain:v6.00 \
#     .github/docker/xc32-toolchain
FROM ubuntu:24.04

ARG XC32_VERSION=v6.00
ARG XC32_TOOLCHAIN_PATH=/opt/microchip/xc32/v6.00

ENV XC32_TOOLCHAIN_PATH=${XC32_TOOLCHAIN_PATH}
ENV ZEPHYR_TOOLCHAIN_VARIANT=xc32

# python3/pip baked in here (not via actions/setup-python) because
# GitHub's hosted Python tool-cache doesn't work when a job runs inside a
# custom container: the mounted pip3 is a shebang script pointing at the
# runner VM's host path, which doesn't exist in here -> "cannot execute:
# required file not found". Controlling Python ourselves avoids that.
# sudo is also required: action-zephyr-setup's own setup script shells out
# to `sudo apt-get install ...` for OS build deps, and the base ubuntu
# image doesn't ship sudo. git/cmake/ninja-build are normally preinstalled
# on GitHub-hosted runner VMs but not inside an arbitrary container image,
# and west build/twister need all three.
# The EXTERNALLY-MANAGED removal works around PEP 668: Ubuntu 24.04's
# system Python refuses plain `pip3 install` outside a venv, but
# action-zephyr-setup's script calls pip3 directly with no venv and no
# --break-system-packages flag we could add, so the marker has to go.
#
# python3-pip is deliberately NOT installed via apt: Debian's pip package
# has no RECORD file (its own docs say so, by design), so a plain
# `pip3 install -U pip` — exactly what action-zephyr-setup runs — fails
# trying to uninstall itself: "Cannot uninstall pip, RECORD file not
# found." ensurepip is not a fallback either — Debian/Ubuntu patches
# CPython to disable it for the system interpreter outright ("ensurepip
# is disabled in Debian/Ubuntu for the system python"). PyPA's own
# get-pip.py bootstrap bypasses both: it isn't dpkg-tracked and isn't
# subject to the ensurepip patch, giving a normal, self-upgradable pip.
# python3-dev (Python.h) and build-essential (gcc/g++/make) are needed
# because some of west's/twister's own Python dependencies (e.g.
# tree-sitter-cmake) have native extensions that pip builds from source.
# gperf is required by Zephyr's own build system (syscall/Kconfig table
# generation); ccache speeds up rebuilds. Both are normally installed by
# action-zephyr-setup, which we don't use (see xc32_samples.yaml).
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl unzip xz-utils sudo \
        python3 python3-dev python3-venv python-is-python3 \
        build-essential git cmake ninja-build gperf ccache \
    && rm -rf /var/lib/apt/lists/* \
    && rm -f /usr/lib/python3.*/EXTERNALLY-MANAGED \
    && curl -sS https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py \
    && python3 /tmp/get-pip.py \
    && rm /tmp/get-pip.py

# ── XC32 compiler ────────────────────────────────────────────────────────
# Direct tarball download (verified reachable, ~1.3GB for v6.00). Archive
# contains a single top-level xc32-${XC32_VERSION}/ dir, hence
# --strip-components=1 to land contents directly under XC32_TOOLCHAIN_PATH
# (target.cmake expects ${XC32_TOOLCHAIN_PATH}/bin/xc32-gcc etc).
# Without a paid license this runs in free mode with capped optimization.
RUN set -eux; \
    TARBALL="xc32-${XC32_VERSION}-full-install-linux-x64.tar.xz"; \
    curl -fSL -o "/tmp/${TARBALL}" \
        "https://ww1.microchip.com/downloads/aemDocuments/documents/DEV/ProductDocuments/SoftwareTools/${TARBALL}"; \
    mkdir -p "${XC32_TOOLCHAIN_PATH}"; \
    tar -xJf "/tmp/${TARBALL}" -C "${XC32_TOOLCHAIN_PATH}" --strip-components=1; \
    rm "/tmp/${TARBALL}"

# GitHub's job-level `container:` runs the image as whatever user it
# specifies, defaulting to root when unset. The Zephyr SDK's own
# hosttools installer (invoked by action-zephyr-setup) explicitly
# refuses to run as root ("Sorry, you are not allowed to execute as
# root."), independent of directory permissions. Run as a real non-root
# user instead, with passwordless sudo so action-zephyr-setup's own
# `sudo apt-get install ...` calls keep working (now a real escalation
# rather than a no-op).
RUN useradd -m -s /bin/bash builder \
    && echo "builder ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/builder \
    && chmod 0440 /etc/sudoers.d/builder \
    && chmod -R a+rX /opt/microchip

USER builder

# pip installs done at container-runtime (west, etc., installed by
# action-zephyr-setup's own script) run as this non-root user, and can't
# write to the system site-packages that get-pip.py populated as root
# during image build -- pip silently falls back to a --user install.
# GitHub Actions containers override HOME to a fixed /github/home
# regardless of the image's own user (confirmed by an earlier pip
# warning referencing /github/home/.cache/pip), so the --user install
# lands in /github/home/.local/bin, not ~builder/.local/bin.
ENV PATH="/github/home/.local/bin:/home/builder/.local/bin:${PATH}"
