#!/usr/bin/env python3
"""Refuse a link-home plan before its first change.

The plan lists every path the apply phase changes, including the SSH and
agent-kit helpers, in the order they change them. Paths are resolved with the
earlier steps already applied, because replacing a managed directory with a
link into the checkout redirects every alias that passes through it.

Usage: link-plan-preflight.py REPO_ROOT HOME_ROOT [OP DESTINATION SOURCE]...
SOURCE is an empty argument when an operation has none.
  link      replace DESTINATION with a link to SOURCE
  file      rewrite DESTINATION in place; it must not be a link (SSH config)
  dir       create a fresh directory named DESTINATION (backup roots)
  localize  replace a link resolving to SOURCE with a local directory
  retire    move away a link to SOURCE, or a real directory other than SOURCE
"""
import os
import sys

DIRECTORY = ("directory",)
FILE = ("file",)
ABSENT = ("absent",)


class Refusal(Exception):
    pass


def inside(path, root):
    return path == root or path.startswith(root + "/")


def entry(path, plan):
    """What is at PATH after the plan's earlier steps, without following it."""
    if path in plan:
        return plan[path]
    if os.path.islink(path):
        return ("link", os.readlink(path))
    if os.path.isdir(path):
        return DIRECTORY
    return FILE if os.path.lexists(path) else ABSENT


def resolve(path, plan, usable=False):
    """Resolve PATH like `realpath -m` after the plan's earlier steps.

    With usable=True, refuse paths that `mkdir -p` could not create: a
    component that is a file or a link that does not lead to a directory.
    """
    pending = os.path.join(os.getcwd(), path).split("/")
    current = "/"
    links = 0
    while pending:
        part = pending.pop(0)
        if part in ("", "."):
            continue
        if part == "..":
            current = os.path.dirname(current)
            continue
        candidate = os.path.join(current, part)
        kind = entry(candidate, plan)
        if kind[0] == "link":
            links += 1
            if links > 40:
                raise Refusal(f"Too many levels of links: {path}")
            if usable and entry(resolve(candidate, plan), plan) != DIRECTORY:
                raise Refusal(f"Destination parent is not a directory: {path}")
            if kind[1].startswith("/"):
                current = "/"
            pending = kind[1].split("/") + pending
            continue
        if usable and kind == FILE:
            raise Refusal(f"Destination parent is not a directory: {path}")
        current = candidate
    return current


def check(repo_root, home_root, steps):
    plan = {}
    touched = []
    for op, destination, source in steps:
        parent = resolve(os.path.dirname(destination), plan, usable=True)
        location = os.path.join(parent, os.path.basename(destination))
        current = entry(location, plan)
        if op == "localize":
            if current[0] != "link" or resolve(location, plan) != source:
                continue
            new = DIRECTORY
        elif op == "retire":
            if current[0] == "link":
                if current[1] != source and resolve(location, plan) != source:
                    continue
            elif current != DIRECTORY or resolve(location, plan) == source:
                continue
            new = ABSENT
        elif op == "link":
            new = ("link", source)
        elif op == "file":
            if current[0] == "link":
                raise Refusal(f"SSH config is a symlink; manage its Include directives in its source: {destination}")
            new = current
        elif op == "dir":
            new = current
        else:
            raise Refusal(f"Unknown plan operation: {op}")

        if inside(parent, repo_root) or inside(parent, home_root):
            raise Refusal(f"Destination parent points into shared repo: {destination}")
        if current == DIRECTORY and new != DIRECTORY:
            # Backing up a real directory moves everything inside it.
            if inside(repo_root, location):
                raise Refusal(f"Destination contains the config checkout: {destination}")
            for earlier, earlier_location, _ in touched:
                if earlier_location != location and inside(earlier_location, location):
                    raise Refusal(f"Destination would move the earlier destination {earlier}: {destination}")
        plan[location] = new
        touched.append((destination, location, parent))

    # A later step must not change where an earlier one wrote.
    for destination, _, parent in touched:
        if resolve(os.path.dirname(destination), plan) != parent:
            raise Refusal(f"Destination path changes during linking: {destination}")


def main():
    repo_root, home_root, *flat = sys.argv[1:]
    if len(flat) % 3:
        raise SystemExit("Plan arguments must be OP DESTINATION SOURCE triples")
    steps = [flat[index:index + 3] for index in range(0, len(flat), 3)]
    try:
        check(repo_root, home_root, steps)
    except Refusal as refusal:
        raise SystemExit(str(refusal)) from None


if __name__ == "__main__":
    main()
