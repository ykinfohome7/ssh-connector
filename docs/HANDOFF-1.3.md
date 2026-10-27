# ЗАДАНИЕ ЗА НОВ ЧАТ — SSH Connector v1.3

## Език
- Говори и пиши САМО на български. Аз не разбирам португалски и други езици.
- Говори бавно и кратко, по една стъпка наведнъж. Изчаквай да кажа „готово“.
- Документацията в хранилището е на английски, с кратки бележки на български на важните места.
- Коментарите в кода (какво прави всеки ред) са на български.
- Графиките и обясненията — и на български, и на английски (отделни версии).

## Проект
- Хранилище: https://github.com/ykinfohome7/ssh-connector (клон main)
- Текуща версия: 1.2.0. Целта е версия 1.3.0.
- Основен код: plugins/ssh-connector/server.py; вход: server.py
- Конфигурация: servers.yaml, config/github-session.yaml
- Сървърът на конектора работи в GitHub Actions (.github/workflows/connector-session.yml), през тунел (MCP, Streamable HTTP).
- Tailscale е ОТДЕЛНО от тунела: частна мрежа до сървърите (BGDB е на 100.65.111.82).
- Два плъгина: за ChatGPT и за Claude Code.
- Поддръжка: Windows, Android, iPhone/iPad (на телефона се ползва през приложението на ChatGPT/Claude, свързано към сървъра в GitHub), Debian, Ubuntu, RHEL, Rocky, Windows OpenSSH.

## Какво трябва да направиш ПЪРВО
1. Прочети server.py и целия код.
2. Направи пълен списък на съществуващите команди с параметрите им.
3. Чак тогава пиши промени.

## Команди за v1.3 (около 41)
- 25 работещи: list_servers, run_command, run_on_many, run_on_group, list_snippets, run_snippet, history, start_job, job_status, shell_open, shell_send, shell_close, list_shells, sftp_list, sftp_read, sftp_write, sftp_upload, sftp_download, sftp_manage, port_forward, list_forwards, stop_forward, start_watch, stop_watch, get_events.
- 5 в кода, но не се виждат в интерфейса (провери защо): version_info, server_add, server_update, server_remove, server_test.
- 8 нови: server_get, server_rename, server_set_primary, server_failover, session_configure, credentials_set, credentials_rotate, health_status.
- Tailscale (нови): статус + версия на Tailscale + акаунт/потребител, с който се свързва; списък със свързани устройства; генериране на нов auth ключ; отнемане (revoke) на компрометиран ключ — само с изрично потвърждение.
- help: изрежда всички команди с кратко описание на български и английски.

## Шаблони
- Всяка команда има готов шаблон/пример: потребителят сменя само своите стойности и пуска.
- Може и свободно писане, без шаблон.
- Файл docs/COMMANDS.md (и docs/COMMANDS.bg.md) с всички команди, описание и пример.

## Версия
- ssh-connector -v / --version, python3 server.py -v / --version и командата version_info трябва да показват реалната версия (1.3.0), git commit SHA, статус и списък с възможности.
- Флагът -v е добавен в commit 63fa102a3a701fbc85621217cec2b03b8564d2c0 — провери дали е пуснат.

## Сигурност (виж docs/SECURITY-STANDARDS.md и .bg.md)
- SSH ключове: Ed25519 по подразбиране, RSA 4096 само за стари системи.
- Смяна на ключовете на 40–90 дни.
- Никога не показвай и не качвай пароли, ключове, токени. Host key проверката остава включена.
- Не трий сървърни профили и не пипай продукционни данни за достъп.

## Тестове и издаване
- Пусни тестовете, добави липсващите, раздели mock от реални тестове.
- Не твърди, че реална SSH връзка работи, без истинска проверка.
- Накрая: какво е готово, какво чака, какво е блокирано; инструкции за пускане и връщане назад.
