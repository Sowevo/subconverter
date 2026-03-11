#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any
from urllib import error, request
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
SNIPPETS = ROOT / "Snippets"

BASE_FILE = SNIPPETS / "base.ini"
RULESET_DIR = SNIPPETS / "ruleset"
GROUP_DIR = SNIPPETS / "custom_proxy_group"
EMOJI_DIR = SNIPPETS / "emoji"
PROFILES_FILE = SNIPPETS / "profiles.yaml"


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def load_base_custom_and_flags() -> tuple[str, list[str]]:
    lines = read_lines(BASE_FILE)
    custom_line = ""
    flags: list[str] = []
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if s == "[custom]":
            custom_line = s
            continue
        flags.append(s)
    if not custom_line:
        raise ValueError(f"Missing [custom] in {BASE_FILE}")
    return custom_line, flags


def read_fragment(base_dir: Path, name: str) -> list[str]:
    return [l.strip() for l in read_lines(base_dir / f"{name}.txt") if l.strip()]


def fetch_url_fragment(url: str, timeout: int = 10) -> list[str]:
    with request.urlopen(url, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
    return [l.strip() for l in raw.splitlines() if l.strip()]


def normalize_fragment_line(line: str, key: str) -> str:
    if line.startswith(";") or line.startswith("#"):
        return line
    if line.startswith(f"{key}="):
        return line
    return f"{key}={line}"


def parse_scalar(value: str) -> Any:
    v = value.strip()
    if v.startswith(('"', "'")) and v.endswith(('"', "'")) and len(v) >= 2:
        return v[1:-1]
    if v.isdigit():
        return int(v)
    if v.lower() == "true":
        return True
    if v.lower() == "false":
        return False
    return v


def load_profiles() -> list[tuple[str, dict[str, Any]]]:
    profiles: list[tuple[str, dict[str, Any]]] = []
    current_name = ""
    current_cfg: dict[str, Any] = {}
    current_section = ""
    current_step: dict[str, Any] | None = None

    for raw in read_lines(PROFILES_FILE):
        if not raw.strip() or raw.strip().startswith("#"):
            continue
        s = raw.strip()
        if s == "profiles:":
            continue

        indent = len(raw) - len(raw.lstrip(" "))

        if indent == 2 and s.endswith(":"):
            if current_name:
                profiles.append((current_name, current_cfg))
            current_name = s[:-1]
            current_cfg = {}
            current_section = ""
            current_step = None
            continue

        if indent == 4:
            if s.endswith(":"):
                key = s[:-1]
                if key not in {"ruleset", "custom_proxy_group", "emoji"}:
                    raise ValueError(f"Unsupported section '{key}' in profile {current_name}")
                current_cfg[key] = []
                current_section = key
                current_step = None
            else:
                key, value = s.split(":", 1)
                current_cfg[key.strip()] = parse_scalar(value)
                current_section = ""
                current_step = None
            continue

        if indent == 6 and s.startswith("- "):
            if not current_section:
                raise ValueError(f"List item outside section in profile {current_name}: {s}")
            step: dict[str, Any] = {}
            tail = s[2:].strip()
            if tail:
                key, value = tail.split(":", 1)
                step[key.strip()] = parse_scalar(value)
            current_cfg[current_section].append(step)
            current_step = step
            continue

        if indent == 8:
            if current_step is None:
                raise ValueError(f"Step property without step in profile {current_name}: {s}")
            key, value = s.split(":", 1)
            current_step[key.strip()] = parse_scalar(value)
            continue

    if current_name:
        profiles.append((current_name, current_cfg))

    return profiles


def apply_steps(base_dir: Path, steps: list[dict[str, Any]], key: str) -> list[str]:
    lines: list[str] = []

    for step in steps:
        has_from = "from" in step
        has_url = "url" in step
        if has_from == has_url:
            raise ValueError(f"Each step must contain exactly one of 'from' or 'url': {step}")

        at = int(step.get("at", len(lines)))
        if at < 0:
            at = 0
        if at > len(lines):
            at = len(lines)

        if has_from:
            frag_lines = read_fragment(base_dir, str(step["from"]))
        else:
            url = str(step["url"])
            timeout = int(step.get("timeout", 10))
            optional = bool(step.get("optional", False))
            try:
                frag_lines = fetch_url_fragment(url, timeout=timeout)
            except (error.URLError, TimeoutError, ValueError) as exc:
                if optional:
                    frag_lines = []
                else:
                    raise RuntimeError(f"Failed to fetch url fragment: {url}") from exc

        frag = [normalize_fragment_line(x, key) for x in frag_lines]
        lines[at:at] = frag

    return lines


def parse_group_name(line: str) -> str:
    if not line.startswith("custom_proxy_group="):
        return ""
    body = line.split("=", 1)[1]
    return body.split("`", 1)[0]


def parse_ruleset_name(line: str) -> str:
    if not line.startswith("ruleset="):
        return ""
    body = line.split("=", 1)[1]
    return body.split(",", 1)[0]


def unique_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def wrap_items_comment(prefix: str, items: list[str], width: int = 60) -> list[str]:
    # 生成多行注释，避免单行过长难以阅读
    if not items:
        return [prefix]
    lines: list[str] = [prefix]
    current = ";   "
    for idx, item in enumerate(items):
        token = item if idx == 0 else f"、{item}"
        if len(current) + len(token) <= width:
            current += token
        else:
            lines.append(current)
            current = f";   {item}"
    lines.append(current)
    return lines


def build_intro_comments(profile_name: str, ruleset_lines: list[str], group_lines: list[str]) -> list[str]:
    ruleset_names = unique_keep_order([parse_ruleset_name(x) for x in ruleset_lines if x.startswith("ruleset=")])
    group_names = unique_keep_order([parse_group_name(x) for x in group_lines if x.startswith("custom_proxy_group=")])
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    intro = [
        "; ===== 自动生成说明 =====",
        f"; 配置名称: {profile_name}",
        f"; 生成时间: {generated_at}",
    ]
    intro.extend(wrap_items_comment(f"; 规则集({len(ruleset_names)}):", ruleset_names))
    intro.extend(wrap_items_comment(f"; 策略组({len(group_names)}):", group_names))
    intro.extend([
        "; ========================",
        "",
    ])
    return intro


def filter_group_options(group_lines: list[str]) -> list[str]:
    existing = {parse_group_name(l) for l in group_lines if l.startswith("custom_proxy_group=")}
    fixed = {"DIRECT", "REJECT"}

    out: list[str] = []
    for line in group_lines:
        if not line.startswith("custom_proxy_group="):
            out.append(line)
            continue

        parts = line.split("`")
        rebuilt: list[str] = []
        for idx, part in enumerate(parts):
            if idx < 2:
                rebuilt.append(part)
                continue
            if part.startswith("[]"):
                target = part[2:]
                if target in fixed or target in existing:
                    rebuilt.append(part)
                continue
            rebuilt.append(part)
        out.append("`".join(rebuilt))
    return out


def normalize_blank(lines: list[str]) -> list[str]:
    out: list[str] = []
    prev_blank = False
    for l in lines:
        blank = not l.strip()
        if blank and prev_blank:
            continue
        out.append(l)
        prev_blank = blank
    while out and not out[0].strip():
        out.pop(0)
    while out and not out[-1].strip():
        out.pop()
    return out


def resolve_output_path(output: str, write_config: bool) -> Path:
    rel = Path(output)
    if write_config:
        return ROOT / rel
    if str(rel).startswith("Config/"):
        return ROOT / "Snippets" / "generated-preview" / rel.name
    return ROOT / "Snippets" / "generated-preview" / rel.name


def build_one(profile_name: str, cfg: dict[str, Any], write_config: bool) -> Path:
    custom_line, flags = load_base_custom_and_flags()

    ruleset_steps = cfg.get("ruleset", [])
    group_steps = cfg.get("custom_proxy_group", [])
    emoji_steps = cfg.get("emoji", [])

    ruleset = apply_steps(RULESET_DIR, ruleset_steps, "ruleset")
    groups = filter_group_options(apply_steps(GROUP_DIR, group_steps, "custom_proxy_group"))
    emoji = apply_steps(EMOJI_DIR, emoji_steps, "emoji")
    intro = build_intro_comments(profile_name, ruleset, groups)

    all_lines: list[str] = []
    all_lines.extend(intro)
    all_lines.append(custom_line)
    all_lines.extend(ruleset)
    all_lines.append("")
    all_lines.extend(groups)
    all_lines.append("")
    all_lines.extend(flags)
    all_lines.append("")
    all_lines.extend(emoji)

    out_lines = normalize_blank(all_lines)
    out_text = "\n".join(out_lines) + "\n"

    out_path = resolve_output_path(str(cfg["output"]), write_config)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(out_text, encoding="utf-8")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build config files from snippets")
    parser.add_argument(
        "--write-config",
        action="store_true",
        help="Write output to Config/*.ini (default writes to Snippets/generated-preview)",
    )
    args = parser.parse_args()

    for name, cfg in load_profiles():
        if "output" not in cfg:
            raise ValueError(f"Missing output in profile: {name}")
        out = build_one(name, cfg, args.write_config)
        print(f"built {out}")


if __name__ == "__main__":
    main()
