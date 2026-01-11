#!/usr/bin/env python3
import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def load_json(path: Path):
    if not path.exists():
        return None
    return json.loads(path.read_text())


def save_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))


def clean_override(overrides, link_id):
    data = overrides.get(link_id, {})
    return {
        "replacement_url": (data.get("replacement_url") or "").strip(),
        "local_path": (data.get("local_path") or "").strip(),
        "disabled": bool(data.get("disabled")),
    }


def find_effective_url(item, overrides):
    override = clean_override(overrides, item.get("id"))
    if override["disabled"]:
        return None, "disabled"
    if override["local_path"]:
        return override["local_path"], "local"
    if override["replacement_url"]:
        return override["replacement_url"], "replacement"
    return item.get("url"), "original"


def check_http(url: str, timeout: int = 3):
    headers = {"User-Agent": "tlac-link-checker/1.0"}
    for method in ("HEAD", "GET"):
        if method == "GET":
            headers["Range"] = "bytes=0-0"
        try:
            req = Request(url, method=method, headers=headers)
            with urlopen(req, timeout=timeout) as response:
                return "ok", response.status
        except HTTPError as exc:
            if method == "HEAD" and exc.code in {403, 405}:
                continue
            return "error", exc.code
        except URLError:
            return "error", None
        except Exception:
            return "error", None
    return "error", None


def main():
    parser = argparse.ArgumentParser(description="Check handbook link registry health.")
    parser.add_argument("--manifest", default="web/lessons/manifest.json")
    parser.add_argument("--overrides", default="data/link-overrides.json")
    parser.add_argument("--write-manifest", action="store_true")
    parser.add_argument("--output", default="reports/link-check.json")
    parser.add_argument("--timeout", type=int, default=3)
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    overrides_path = Path(args.overrides)
    output_path = Path(args.output)

    manifest = load_json(manifest_path) or {}
    overrides = load_json(overrides_path) or {}
    items = (manifest.get("linksRegistry") or {}).get("items") or []

    results = []
    now = datetime.now(timezone.utc).isoformat()

    for item in items:
        if not isinstance(item, dict):
            continue
        link_id = item.get("id")
        effective_url, source = find_effective_url(item, overrides)
        status = "missing"
        http_status = None
        if source == "disabled":
            status = "disabled"
        elif effective_url and source == "local":
            path = Path(effective_url)
            if not path.is_absolute():
                path = Path.cwd() / path
            status = "local-ok" if path.exists() else "local-missing"
        elif effective_url:
            status, http_status = check_http(effective_url, timeout=args.timeout)

        results.append(
            {
                "id": link_id,
                "lesson_id": item.get("lessonId"),
                "title": item.get("title"),
                "url": item.get("url"),
                "effective_url": effective_url,
                "source": source,
                "status": status,
                "http_status": http_status,
                "checked_at": now,
            }
        )

        if args.write_manifest:
            item["status"] = status
            item["lastChecked"] = now

    save_json(output_path, {"checked_at": now, "items": results})

    if args.write_manifest:
        manifest_path.write_text(json.dumps(manifest, indent=2))

    print(f"Checked {len(results)} links. Report: {output_path}")


if __name__ == "__main__":
    main()
