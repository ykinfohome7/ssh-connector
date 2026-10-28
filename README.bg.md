<div align="center">

# 🔐 SSH Connector

**Работа директно през SSH на много сървъри — от Claude и ChatGPT.**
Команди, интерактивни терминали, SFTP, тунели, резервни адреси, събития и сигурна `sudo` парола — без посредник.

[![Версия](https://img.shields.io/badge/версия-1.3.3-blue)](CHANGELOG.md)
[![Тестове](https://github.com/ykinfohome7/ssh-connector/actions/workflows/test.yml/badge.svg)](https://github.com/ykinfohome7/ssh-connector/actions/workflows/test.yml)
[![Лиценз: GPL-3.0](https://img.shields.io/badge/лиценз-GPL--3.0-green)](LICENSE)
[![Звезди](https://img.shields.io/github/stars/ykinfohome7/ssh-connector?style=social)](https://github.com/ykinfohome7/ssh-connector/stargazers)

[English](README.md) · **Български**

[Инсталиране](#-инсталиране) · [Бърз старт](#-бърз-старт) · [Команди](docs/COMMANDS.bg.md) · [Сигурност](docs/SECURITY-STANDARDS.bg.md) · [Промени](CHANGELOG.md)

</div>

---

## ✨ Какво прави

| | |
|---|---|
| 🖥️ **Много сървъри** | Debian и Red Hat, основен + резервни адреси, автоматично превключване, повторни опити, keepalive |
| ⌨️ **Истински терминал** | Интерактивен терминал (PTY), който пази състоянието (`cd`, променливи, работещи програми, Ctrl+C) |
| 🔑 **Сигурен sudo** | `sudo_password` — пишеш я на еднократна страница, взима се от профила или се генерира с *твоите* дължина и символи. Никога в чата |
| 📁 **Файлове** | SFTP: списък, четене, запис, качване, сваляне, папки, триене, преименуване |
| 🚇 **Тунели** | Пренасочване на портове, междинни сървъри (bastion) |
| 👀 **Събития** | Следи грешки, сривове / OOM и влизания — без да питаш |
| 🧩 **Групи и шаблони** | Една команда на цяла група; запазени команди |
| 🌐 **Tailscale** | Състояние, устройства, ключове — и постоянен HTTPS адрес чрез Funnel |
| 📖 **Вградена помощ** | `help` показва всички **48 команди** на БГ и EN с готов пример |

## 📦 Инсталиране

Избери начина, който ти пасва.

### Claude Code — плъгин (препоръчително)
```bash
claude plugin marketplace add ykinfohome7/ssh-connector
claude plugin install ssh-connector@ykinfohome7-tools
```
В сесия: `/plugin marketplace add ykinfohome7/ssh-connector`, после `/plugin install ssh-connector@ykinfohome7-tools`.
Първото пускане създава собствена виртуална среда (~30 сек, само веднъж).

### ChatGPT Codex — плъгин
```bash
codex plugin marketplace add ykinfohome7/ssh-connector
```
После включи **ssh-connector** от списъка с плъгини.

### Приложенията ChatGPT / Claude (уеб, телефон) — конектор през HTTPS
Трябва им публичен HTTPS адрес. Използвай [сървъра, който е винаги включен](#-сървър-винаги-включен) или [сесията в GitHub Actions](#%EF%B8%8F-сесия-в-github-actions), после добави конектора:
- **ChatGPT:** Settings → Apps & Connectors → Advanced → Developer mode → *Create* → URL `https://<адрес>/<ТОКЕН>/mcp`, без удостоверяване.
- **Claude:** Settings → Connectors → *Add custom connector* → URL `https://<адрес>/mcp`, заглавие `Authorization: Bearer <ТОКЕН>`.

След обновяване натисни **Refresh** на конектора, за да се заредят новите команди. С Tailscale Funnel адресът не се сменя.

### Изтегляне
- ⬇️ **[Последна версия (ZIP)](https://github.com/ykinfohome7/ssh-connector/archive/refs/heads/main.zip)**
- 🏷️ **[Издания (Releases)](https://github.com/ykinfohome7/ssh-connector/releases)**
- `git clone https://github.com/ykinfohome7/ssh-connector`

### Ръчно MCP (без плъгин)
```bash
git clone https://github.com/ykinfohome7/ssh-connector && cd ssh-connector
claude mcp add ssh -- sh $(pwd)/plugins/ssh-connector/bin/run.sh     # Claude Code
codex  mcp add ssh -- sh $(pwd)/plugins/ssh-connector/bin/run.sh     # Codex
```

## 🚀 Бърз старт

1. Създай `~/.ssh-connector/servers.yaml` по образеца [`servers.example.yaml`](servers.example.yaml) (или задай `SSH_CONNECTOR_CONFIG`). Нужен е `python3`.
2. Питай с обикновени думи, например *„покажи заетото място на всички уеб сървъри“* — или извикай команда директно:

```json
{"tool": "server_test", "arguments": {"name": "web1"}}
{"tool": "run_command", "arguments": {"server": "web1", "command": "df -h"}}
{"tool": "help", "arguments": {}}
```

Пълен списък с параметри и примери: **[docs/COMMANDS.bg.md](docs/COMMANDS.bg.md)**.

## 🧰 GitHub Codespaces (ново във v1.3.3)

Три нови MCP инструмента: `codespace_status(name="")` показва всички достъпни Codespaces или един по име; `codespace_start(name)` стартира съществуващ Codespace; `codespace_stop(name, confirm=true)` спира само след изрично потвърждение. Използват `gh` и официалния GitHub REST API, с права `codespace` или Codespaces lifecycle admin. Не изпращат GitHub токени като параметри.

**Важно:** ако MCP конекторът работи само вътре в спрян Codespace, не може сам да го събуди. За събуждане е нужен независим работещ конектор или GitHub.

## 🔑 sudo парола (ново във 1.3.3)

Когато команда иска `sudo`, конекторът не виси — пита те да избереш:

| Режим | Какво става |
|---|---|
| `prompt` | Получаваш **еднократна HTTPS връзка** (2 мин). Пишеш паролата там; проверява се на сървъра |
| `profile` | Взима предварително зададена стойност от променлива на средата / GitHub Secret. Пази се само **името** ѝ |
| `generate` | Случайна парола — **ти избираш** дължина (16–128) и символи. Показва се веднъж; задава се на сървъра едва след „Записах я“ |

Паролата никога не е в чата, в командата, в логовете или в историята. Стига до `sudo` през stdin.

## 🌍 Сървър винаги включен
Пусни веднъж на един от сървърите си (например от Termius):
```bash
curl -fsSL https://raw.githubusercontent.com/ykinfohome7/ssh-connector/main/install-server.sh | sudo bash
```
Инсталира systemd услуга, HTTPS тунел, токен и SSH ключ и показва какво да поставиш в Claude и ChatGPT. Покажи го пак: `sudo ssh-connector-info`.

## ☁️ Сесия в GitHub Actions
Временен сървър в GitHub Actions с **постоянен** адрес `https://ssh-connector.<tailnet>.ts.net` (Tailscale Funnel; резерва: временен тунел на Cloudflare).
- Старт / рестарт: промени [`control/session`](control/session) (`start` + нещо ново на ред 2) или *Actions → connector-session → Run workflow*.
- Спиране: напиши `stop` в `control/session`.
- Състояние и адрес: [`control/status.md`](control/status.md).

Пълна настройка (тайни, Tailscale, BGDB Codespaces): **[docs/GITHUB-SESSION.md](docs/GITHUB-SESSION.md)**.

## 🛡️ Сигурност
- Пароли, ключове и токени **никога** не се показват и не се записват във файлове — само имена на променливи и пътища.
- SSH ключове: **Ed25519**, RSA 4096 само за стари системи, смяна на **40–90 дни** (`credentials_rotate`).
- Заявки без токен получават `401`. Пази токена като SSH ключ.
- Откри уязвимост? Виж **[SECURITY.md](SECURITY.md)**.

## 📚 Документация
| Документ | English | Български |
|---|---|---|
| Команди | [COMMANDS.md](docs/COMMANDS.md) | [COMMANDS.bg.md](docs/COMMANDS.bg.md) |
| Стандарти за сигурност | [SECURITY-STANDARDS.md](docs/SECURITY-STANDARDS.md) | [SECURITY-STANDARDS.bg.md](docs/SECURITY-STANDARDS.bg.md) |
| Сесия в GitHub Actions | [GITHUB-SESSION.md](docs/GITHUB-SESSION.md) | [GITHUB-SESSION.md](docs/GITHUB-SESSION.md) |
| Промени по версии | [CHANGELOG.md](CHANGELOG.md) | [CHANGELOG.md](CHANGELOG.md) |
| Участие | [CONTRIBUTING.md](CONTRIBUTING.md) | [CONTRIBUTING.md](CONTRIBUTING.md) |

## ❤️ Харесваш? Искаш нещо?
- ⭐ **Харесвам** — дай [звезда](https://github.com/ykinfohome7/ssh-connector/stargazers) на проекта.
- 💡 **Искам** — [предложи нова функция](https://github.com/ykinfohome7/ssh-connector/issues/new?template=feature_request.yml).
- 🐞 **Има грешка** — [съобщи я](https://github.com/ykinfohome7/ssh-connector/issues/new?template=bug_report.yml).

## 📄 Лиценз
[GPL-3.0](LICENSE) © ykinfohome7
