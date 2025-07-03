# ModDB Comment Notifier

## 📜 Description

**ModDB Comment Notifier** is a Python script that checks for new comments on ModDB add-ons for specific users and sends email notifications. It's perfect for keeping add-on authors informed without needing to check ModDB manually.

## ✨ Features

* Monitors comments on ModDB add-ons of selected users
* Sends customizable email alerts
* Supports ModDB login for guest comments
* Runs periodically via scheduler
* Easy to configure via `config.toml` and `template.txt`

## 🛠️ Setup

1. **Clone the Repository**

```bash
git clone https://github.com/Tosox/moddb-comment-notifier.git
cd moddb-comment-notifier
```

2. **Install Dependencies**

```bash
pip install -r requirements.txt
```

3. **Create Config Files**

Before running the script, you must create a `config.toml` and `template.txt` file. There are a `config-example.toml` and `template-example.txt` provided which you can copy and edit.

* `config.toml`: stores credentials, SMTP settings, and monitored users
* `template.txt`: the email body (supports {name}, {author}, {content}, {url})

## 📁 `config.toml` Configuration

### ⌚ Script Schedule (`[schedule]`)

This is used to define the schedule on when the script should run.

```toml
[schedule]
interval = 30  # Interval in minutes
```

### 🧩 SMTP Settings (`[smtp]`)

These settings are used to send the email notifications.

```toml
[smtp]
server = "smtp.gmail.com"       # Your SMTP server (Gmail, Outlook, etc.)
port = 587                      # Usually 587 for TLS
email = "your-email@gmail.com"  # Sender address (must match login)
password = "your-app-password"  # App password or real password (not recommended)
```

**Gmail Users**: You must create an [App Password](https://support.google.com/accounts/answer/185833?hl=en) if you use 2FA. Do not use your real password.

### 📨 Email Settings (`[email]`)

This section is used to specify some options about the email messages.

```toml
[email]
subject = "{author} has commented on your add-on on ModDB"
sender = "Not ModDB <{email}>"
```

* Supported macros:
  * **subject**: `{author}` - Author of the comment
  * **sender**: `{email}` - Your defined email address

### 👤 Members to Monitor (`[members]`)

Each entry defines a ModDB user whose add-ons should be checked. If someone comments on their add-ons, an email will be sent.

```toml
[members]
uids = [
  { uid = "tosox", email = "my-email@gmail.com" }, # https://www.moddb.com/members/tosox
  { uid = "tosox-2", email = "my-other-email@mail.com" } # https://www.moddb.com/members/tosox-2
]
```

You can add or remove users by editing the list.
Each object requires:
* uid: the [slug](https://www.seobility.net/en/wiki/URL_Slug) of the ModDB member url
* email: where to send notifications

### 🔐 ModDB Credentials (`[moddb]`)

These are **optional** and used to log into ModDB to view comments by guest accounts. Make sure to disable 2FA for the ModDB account in the profile settings.

```toml
[moddb]
username = "some-moddb-username"
password = "some-moddb-password"
```

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
