# ModDB Comment Notifier

Get notified when someone comments on your [ModDB](https://www.moddb.com) add-ons, by email, Discord, Telegram, ntfy or [any of the 100+ services supported by Apprise](https://appriseit.com/services/).

- 🔔 One summary message per check
- 🧩 Configured entirely through environment variables
- 🔐 Optional ModDB login to also see guest comments
- ✏️ Customizable messages with Jinja2 templates
- 🐳 Ready-to-use Docker image

## 🚀 Quick start (Docker)

Create a `docker-compose.yaml`:

```yaml
services:
  moddb-comment-notifier:
    image: ghcr.io/tosox/moddb-comment-notifier:latest
    container_name: moddb-comment-notifier
    restart: unless-stopped
    environment:
      MCN_MEMBER: your-moddb-username
      MCN_NOTIFY_URL: mailtos://you:app-password@gmail.com
    volumes:
      - state:/app/state

volumes:
  state:
```

Then start it:

```bash
docker compose up -d
docker compose logs -f
```

On the first run the notifier only remembers the current time, so you won't get flooded with old comments. From then on, every new comment is reported.

## ⚙️ Configuration

| Variable | Required | Default | Description |
|---|---|---|---|
| `MCN_MEMBER` | ✅ | | ModDB member to watch. Use the name from the profile URL, e.g. `tosox` for `moddb.com/members/tosox`. |
| `MCN_NOTIFY_URL` | ✅ | | Where notifications are sent, as an [Apprise URL](https://appriseit.com/services/). |
| `MCN_MODDB_USERNAME` | | | ModDB account used to log in, which makes guest comments visible. 2FA must be disabled for it. |
| `MCN_MODDB_PASSWORD` | | | Password of that account. |
| `MCN_INTERVAL` | | `30` | Minutes between checks. |
| `MCN_MESSAGE_FORMAT` | | `markdown` | `markdown`, `html` or `text`, see *Custom messages* below. |
| `MCN_TEMPLATE_DIR` | | | Folder with your own message templates, see below. |
| `MCN_STATE_DIR` | | `./state` (`/app/state` in Docker) | Where the last check time and ModDB session are stored. |
| `MCN_LOG_LEVEL` | | `INFO` | `DEBUG`, `INFO`, `WARNING` or `ERROR`. Libraries used by the notifier only log warnings and errors. |

Missing or invalid values are listed at startup, so a bad configuration fails right away with a clear message.

One container watches one member and notifies one target. To watch more members, run one container per member, each with its own state volume.

### 📬 Notification URLs

A few examples, see the [Apprise documentation](https://appriseit.com/services/) for all services and their options:

| Service | URL |
|---|---|
| Gmail | `mailtos://you:app-password@gmail.com` ([create an app password](https://support.google.com/accounts/answer/185833)) |
| Other SMTP | `mailtos://user:password@smtp.example.com:465?to=someone@example.com` |
| Discord | `discord://webhook_id/webhook_token` |
| Telegram | `tgram://bot_token/chat_id` |
| ntfy | `ntfy://ntfy.sh/your-topic` |

Special characters in passwords must be [URL-encoded](https://www.urlencoder.org/), e.g. `@` becomes `%40`.

## ✏️ Custom messages

Messages are rendered from [Jinja2](https://jinja.palletsprojects.com/en/stable/templates/) templates: `title.j2` for the subject / title, and a body template that depends on `MCN_MESSAGE_FORMAT`:

| `MCN_MESSAGE_FORMAT` | Body template | Use for |
|---|---|---|
| `markdown` (default) | `body.md.j2` | Most services. Apprise converts it as needed, e.g. to HTML for email. |
| `html` | `body.html.j2` | Styled emails. Use inline styles (`style="..."`), since many mail clients ignore `<style>` blocks. |
| `text` | `body.txt.j2` | Services without any formatting, e.g. SMS. |

In `body.html.j2` all values are HTML-escaped automatically, so comment text can't inject markup into your emails.

To change them, put your own versions in a folder and point `MCN_TEMPLATE_DIR` to it. Files you don't provide fall back to the [built-in templates](src/moddb_comment_notifier/templates).

```yaml
    environment:
      MCN_TEMPLATE_DIR: /app/templates
    volumes:
      - ./templates:/app/templates:ro
```

Available in all templates:

| Variable | Description |
|---|---|
| `member` | Display name of the watched ModDB member |
| `comments` | List of new comments, oldest first |
| `comment.author` | Who wrote the comment |
| `comment.content` | Comment text |
| `comment.addon` | Name of the add-on |
| `comment.url` | Link to the add-on |
| `comment.date` | When it was posted (`datetime`, e.g. `{{ c.date.strftime("%d.%m.%Y") }}`) |

There is also a `quote` filter that turns text into a Markdown quote: `{{ c.content | quote }}`.

To see how your messages look, render them with sample data. Nothing is fetched or sent, and only `MCN_TEMPLATE_DIR` and `MCN_MESSAGE_FORMAT` are used:

```bash
docker run --rm -e MCN_MESSAGE_FORMAT=html -e MCN_TEMPLATE_DIR=/app/templates -v ./templates:/app/templates:ro \
  ghcr.io/tosox/moddb-comment-notifier:latest moddb-comment-notifier --preview
```

Template errors are reported with file name and line number.

## 🐍 Running without Docker

Requires Python 3.12+.

```bash
git clone https://github.com/Tosox/moddb-comment-notifier.git
cd moddb-comment-notifier
pip install .
cp .env.example .env              # then fill in your values
moddb-comment-notifier            # runs until stopped
moddb-comment-notifier --once     # checks a single time and exits
moddb-comment-notifier --preview  # shows the messages rendered with sample data
```

## 🛠️ Development

```bash
pip install -e ".[dev]"
pytest
ruff check . && ruff format .
```

## 📄 License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.
