import moddb
import moddb.errors
import schedule
import datetime
import smtplib
import time
import toml
from dataclasses import dataclass
from email.message import EmailMessage
from typing import List

CONFIG = toml.load('config.toml')
EMAIL_TEMPLATE = open('template.txt', 'r', encoding='utf-8').read()
LAST_CHECKED_FILENAME = 'last_update.txt'

@dataclass
class Member:
    uid: str
    email: str

SCHEDULE_INTERVAL = CONFIG['schedule']['interval']
SMTP_SERVER = CONFIG['smtp']['server']
SMTP_PORT = CONFIG['smtp']['port']
EMAIL = CONFIG['smtp']['email']
EMAIL_PASSWORD = CONFIG['smtp']['password']
EMAIL_SUBJECT = CONFIG['email']['subject']
EMAIL_SENDER = CONFIG['email']['sender']
MODDB_USERNAME = CONFIG['moddb']['username']
MODDB_PASSWORD = CONFIG['moddb']['password']
MEMBERS = [Member(**m) for m in CONFIG['members']['uids']]

def get_last_checked() -> int:
    try:
        with open(LAST_CHECKED_FILENAME, 'r') as file:
            return int(file.readline())
    except Exception:
        return 0

def save_last_checked(timestamp: int):
    with open(LAST_CHECKED_FILENAME, 'w') as file:
        file.write(f'{timestamp}\n')

def create_email(member_name: str, member_email: str, author: str, content: str, url: str) -> EmailMessage:
    body = EMAIL_TEMPLATE.format(
        name=member_name,
        author=author,
        content=content.strip(),
        url=url
    )

    msg = EmailMessage()
    msg['Subject'] = EMAIL_SUBJECT.format(author=author)
    msg['From'] = EMAIL_SENDER.format(email=EMAIL)
    msg['To'] = member_email
    msg.set_content(body)
    return msg

def process_member_comments(member: Member, last_checked: int) -> List[EmailMessage]:
    print(f'Checking user {member.uid}')
    try:
        member_obj = moddb.parse_page(f'https://www.moddb.com/members/{member.uid}')
    except Exception as e:
        print(f'Failed to retrieve member page: {e}')
        return []

    messages = []

    for addon_thumb in member_obj.get_addons():
        print(f' Checking add-on: {addon_thumb.name}')
        try:
            comments = addon_thumb.parse().comments
        except Exception as e:
            print(f'Failed to retrieve comments: {e}')
            continue

        stop_early = False
        for page in range(comments.total_pages, 0, -1):
            for comment in reversed(comments.to_page(page)):
                ts = int(comment.date.timestamp())
                if ts <= last_checked:
                    stop_early = True
                    break
                if comment.author.name == member_obj.name:
                    continue
                print(f'  Found new comment by {comment.author.name}')
                msg = create_email(member_obj.name, member.email, comment.author.name, comment.content, addon_thumb.url)
                messages.append(msg)
            if stop_early:
                break

    return messages

def send_emails(messages: List[EmailMessage]):
    if not messages:
        return

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL, EMAIL_PASSWORD)
            for msg in messages:
                server.send_message(msg)
    except Exception as e:
        print(f'Unable to send emails: {e}')

def main():
    now = datetime.datetime.now()
    print(f'Running at {now:%d. %B %Y %H:%M:%S}')
    last_checked = get_last_checked()
    new_timestamp = int(now.timestamp())

    try:
        moddb.login(MODDB_USERNAME, MODDB_PASSWORD)
    except moddb.errors.AuthError as e:
        print(f'Unable to read guest comments: Please disable 2FA for this ModDB account. {e}')
    except ValueError as e:
        print(f'Unable to read guest comments: Invalid login credentials. {e}')

    all_messages = []
    for member in MEMBERS:
        all_messages.extend(process_member_comments(member, last_checked))

    send_emails(all_messages)
    save_last_checked(new_timestamp)
    print('Finished loop')

if __name__ == '__main__':
    main()
    schedule.every(SCHEDULE_INTERVAL).minutes.do(main)
    while True:
        schedule.run_pending()
        time.sleep(1)
