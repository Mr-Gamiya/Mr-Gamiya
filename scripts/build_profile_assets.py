"""Render factual profile cards from the GitHub API. Run with GITHUB_TOKEN set."""

from __future__ import annotations

import datetime as dt
import html
import json
import os
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

OWNER = "Mr-Gamiya"
OUT = Path("assets/generated")
BG = "#0b1228"
PANEL = "#111c35"
CYAN = "#6ee7f9"
PURPLE = "#a78bfa"
TEXT = "#dbeafe"
MUTED = "#91a8c8"


def api(path: str, token: str, body: dict | None = None) -> dict | list:
    data = json.dumps(body).encode() if body is not None else None
    request = Request(
        "https://api.github.com" + path,
        data=data,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "Mr-Gamiya-profile-assets",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
    )
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def text(value: object) -> str:
    return html.escape(str(value), quote=True)


def shell(width: int, height: int, title: str, content: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{text(title)}">
<defs><linearGradient id="edge"><stop stop-color="{CYAN}"/><stop offset="1" stop-color="{PURPLE}"/></linearGradient></defs>
<rect x="2" y="2" width="{width-4}" height="{height-4}" rx="18" fill="{BG}" stroke="#365675"/>
<path d="M20 2H{width-20}" stroke="url(#edge)" stroke-width="3"/>
{content}
</svg>'''


def label(x: int, y: int, content: str, size: int = 14, color: str = MUTED, weight: int = 500) -> str:
    return f'<text x="{x}" y="{y}" fill="{color}" font-family="Segoe UI,Arial,sans-serif" font-size="{size}" font-weight="{weight}">{text(content)}</text>'


def save(name: str, svg: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(svg + "\n", encoding="utf-8")


def calendar(token: str) -> dict:
    query = '''query($login:String!) { user(login:$login) { contributionsCollection {
      contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } }
    } } }'''
    result = api("/graphql", token, {"query": query, "variables": {"login": OWNER}})
    if "errors" in result:
        raise RuntimeError("GitHub GraphQL rejected the contribution request")
    return result["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def streaks(days: list[dict]) -> tuple[int, int]:
    counts = {dt.date.fromisoformat(day["date"]): day["contributionCount"] for day in days}
    longest = run = 0
    for day in sorted(counts):
        run = run + 1 if counts[day] > 0 else 0
        longest = max(longest, run)
    cursor = dt.datetime.now(dt.timezone.utc).date()
    if counts.get(cursor, 0) == 0:
        cursor -= dt.timedelta(days=1)
    current = 0
    while counts.get(cursor, 0) > 0:
        current += 1
        cursor -= dt.timedelta(days=1)
    return current, longest


def render_stats(user: dict, repos: list[dict], cal: dict) -> str:
    own = [repo for repo in repos if not repo["fork"]]
    values = [
        ("PUBLIC REPOS", user["public_repos"]),
        ("STARS RECEIVED", sum(repo["stargazers_count"] for repo in own)),
        ("FORKS", sum(repo["forks_count"] for repo in own)),
        ("FOLLOWERS", user["followers"]),
        ("YEAR CONTRIBUTIONS", cal["totalContributions"]),
    ]
    blocks = [label(28, 39, "GITHUB / LIVE OVERVIEW", 15, CYAN, 700)]
    for index, (name, value) in enumerate(values):
        x = 28 + index * 166
        blocks += [f'<rect x="{x}" y="57" width="150" height="92" rx="12" fill="{PANEL}"/>',
                   label(x + 13, 93, value, 28, TEXT, 800), label(x + 13, 124, name, 11, MUTED, 700)]
    return shell(886, 171, "Live GitHub statistics for Mr-Gamiya", "\n".join(blocks))


def render_stats_mobile(user: dict, repos: list[dict], cal: dict) -> str:
    own = [repo for repo in repos if not repo["fork"]]
    values = [("PUBLIC REPOS", user["public_repos"]),
              ("STARS RECEIVED", sum(repo["stargazers_count"] for repo in own)),
              ("FORKS", sum(repo["forks_count"] for repo in own)),
              ("FOLLOWERS", user["followers"]),
              ("YEAR CONTRIBUTIONS", cal["totalContributions"])]
    blocks = [label(20, 36, "GITHUB / LIVE OVERVIEW", 14, CYAN, 700)]
    for index, (name, value) in enumerate(values):
        y = 50 + index * 49
        blocks += [f'<rect x="20" y="{y}" width="360" height="42" rx="8" fill="{PANEL}"/>',
                   label(34, y + 27, name, 12, MUTED, 700), label(310, y + 28, value, 21, TEXT, 800)]
    return shell(400, 313, "Live GitHub statistics for Mr-Gamiya, mobile layout", "\n".join(blocks))


def render_languages(totals: dict[str, int]) -> str:
    ranking = sorted(totals.items(), key=lambda item: item[1], reverse=True)[:5]
    denominator = sum(value for _, value in ranking) or 1
    blocks = [label(28, 39, "LANGUAGES / PUBLIC SOURCE", 15, CYAN, 700)]
    colors = [CYAN, PURPLE, "#60a5fa", "#c084fc", "#34d399"]
    for index, (name, amount) in enumerate(ranking):
        y = 72 + index * 31
        percent = round(amount / denominator * 100)
        blocks += [label(28, y, name, 13, TEXT, 600), label(428, y, f"{percent}%", 12, MUTED),
                   f'<rect x="156" y="{y-12}" width="252" height="9" rx="4" fill="#253857"/>',
                   f'<rect x="156" y="{y-12}" width="{round(amount / denominator * 252)}" height="9" rx="4" fill="{colors[index]}"/>']
    return shell(470, 243, "Languages in public original repositories", "\n".join(blocks))


def render_trophies(user: dict, repos: list[dict], cal: dict) -> str:
    own = [repo for repo in repos if not repo["fork"]]
    facts = [("REPOSITORIES", user["public_repos"]), ("STARS", sum(r["stargazers_count"] for r in own)),
             ("FOLLOWERS", user["followers"]), ("CONTRIBUTIONS", cal["totalContributions"])]
    blocks = [label(28, 39, "MILESTONES / LIVE GITHUB DATA", 15, CYAN, 700)]
    for index, (name, value) in enumerate(facts):
        x = 28 + index * 210
        blocks += [f'<rect x="{x}" y="56" width="194" height="98" rx="13" fill="{PANEL}" stroke="#253e5f"/>',
                   label(x + 15, 96, "✦", 25, PURPLE, 800), label(x + 54, 99, value, 27, TEXT, 800),
                   label(x + 15, 132, name, 12, MUTED, 700)]
    return shell(886, 177, "Live GitHub milestone cards", "\n".join(blocks))


def render_trophies_mobile(user: dict, repos: list[dict], cal: dict) -> str:
    own = [repo for repo in repos if not repo["fork"]]
    facts = [("REPOSITORIES", user["public_repos"]), ("STARS", sum(r["stargazers_count"] for r in own)),
             ("FOLLOWERS", user["followers"]), ("CONTRIBUTIONS", cal["totalContributions"])]
    blocks = [label(20, 36, "MILESTONES / GITHUB DATA", 14, CYAN, 700)]
    for index, (name, value) in enumerate(facts):
        x = 20 + (index % 2) * 185
        y = 50 + (index // 2) * 103
        blocks += [f'<rect x="{x}" y="{y}" width="175" height="93" rx="10" fill="{PANEL}" stroke="#253e5f"/>',
                   label(x + 14, y + 39, value, 28, TEXT, 800), label(x + 14, y + 70, name, 11, MUTED, 700)]
    return shell(400, 267, "Live GitHub milestone cards, mobile layout", "\n".join(blocks))


def render_activity(cal: dict) -> str:
    weeks = cal["weeks"][-53:]
    maximum = max((day["contributionCount"] for week in weeks for day in week["contributionDays"]), default=0)
    colors = ["#192744", "#254765", "#23688a", "#3aa9cf", CYAN]
    blocks = [label(28, 37, "CONTRIBUTION ACTIVITY / LAST YEAR", 15, CYAN, 700)]
    for wi, week in enumerate(weeks):
        for di, day in enumerate(week["contributionDays"]):
            count = day["contributionCount"]
            level = 0 if count == 0 else min(4, 1 + int(count / max(1, maximum) * 3))
            x, y = 28 + wi * 16, 60 + di * 16
            blocks.append(f'<rect x="{x}" y="{y}" width="12" height="12" rx="3" fill="{colors[level]}"/>')
    blocks.append(label(28, 193, f"{cal['totalContributions']} contributions in the past year", 12, MUTED))
    return shell(910, 213, "GitHub contribution activity calendar for Mr-Gamiya", "\n".join(blocks))


def render_projects(repos_by_name: dict[str, dict]) -> str:
    projects = [("school", "LUMIRA ’26", "Event tickets, QR scanning & admin tools"),
                ("MC-Cheat-detector", "Minecraft Cheat Scanner", "Read only local PowerShell scanner")]
    blocks = [label(28, 39, "FEATURED / ORIGINAL PROJECTS", 15, CYAN, 700)]
    for index, (key, title, summary) in enumerate(projects):
        repo = repos_by_name[key]
        x = 28 + index * 420
        blocks += [f'<rect x="{x}" y="57" width="404" height="130" rx="13" fill="{PANEL}" stroke="#253e5f"/>',
                   label(x + 17, 86, title, 17, CYAN, 700), label(x + 17, 114, summary, 12, TEXT),
                   label(x + 17, 152, f"{repo.get('language') or 'Repository'}  ·  ★ {repo['stargazers_count']}  ·  Forks {repo['forks_count']}", 12, MUTED)]
    return shell(886, 209, "Featured original GitHub repositories", "\n".join(blocks))


def render_projects_mobile(repos_by_name: dict[str, dict]) -> str:
    projects = [("school", "LUMIRA ’26", "Event tickets, QR scanning & admin tools"),
                ("MC-Cheat-detector", "Minecraft Cheat Scanner", "Read only local PowerShell scanner")]
    blocks = [label(20, 36, "FEATURED / ORIGINAL PROJECTS", 14, CYAN, 700)]
    for index, (key, title, summary) in enumerate(projects):
        repo = repos_by_name[key]
        y = 50 + index * 137
        blocks += [f'<rect x="20" y="{y}" width="360" height="125" rx="11" fill="{PANEL}" stroke="#253e5f"/>',
                   label(34, y + 29, title, 17, CYAN, 700), label(34, y + 58, summary, 11, TEXT),
                   label(34, y + 96, f"{repo.get('language') or 'Repository'}  ·  ★ {repo['stargazers_count']}  ·  Forks {repo['forks_count']}", 12, MUTED)]
    return shell(400, 345, "Featured original GitHub repositories, mobile layout", "\n".join(blocks))


def main() -> None:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN is required")
    user = api("/users/" + quote(OWNER), token)
    repos = api("/users/" + quote(OWNER) + "/repos?per_page=100&type=owner", token)
    cal = calendar(token)
    totals: dict[str, int] = {}
    for repo in repos:
        if repo["fork"]:
            continue
        languages = api("/repos/" + quote(OWNER) + "/" + quote(repo["name"]) + "/languages", token)
        for name, amount in languages.items():
            totals[name] = totals.get(name, 0) + amount
    by_name = {repo["name"]: repo for repo in repos}
    save("stats.svg", render_stats(user, repos, cal))
    save("stats-mobile.svg", render_stats_mobile(user, repos, cal))
    save("languages.svg", render_languages(totals))
    save("trophies.svg", render_trophies(user, repos, cal))
    save("trophies-mobile.svg", render_trophies_mobile(user, repos, cal))
    save("activity.svg", render_activity(cal))
    save("projects.svg", render_projects(by_name))
    save("projects-mobile.svg", render_projects_mobile(by_name))
    print("Generated eight factual SVG cards from GitHub API data")


if __name__ == "__main__":
    main()
