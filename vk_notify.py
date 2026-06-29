import os
import requests

VK_TOKEN = os.environ["VK_TOKEN"]
TG_BOT_TOKEN = os.environ["TG_BOT_TOKEN"]
TG_CHAT_ID = os.environ["TG_CHAT_ID"]
LAST_MESSAGE_ID = int(os.environ.get("LAST_MESSAGE_ID") or "0")
GH_TOKEN = os.environ["GH_TOKEN"]
GH_REPO = os.environ["GH_REPO"]

def vk_get_new_messages():
    r = requests.get("https://api.vk.com/method/messages.getConversations", params={
        "access_token": VK_TOKEN,
        "v": "5.199",
        "count": 20,
        "filter": "unread",
    })
    data = r.json()
    if "error" in data:
        print(f"VK Error: {data['error']}")
        return []

    items = data.get("response", {}).get("items", [])
    messages = []
    for item in items:
        conv = item.get("conversation", {})
        last_msg = item.get("last_message", {})

        msg_id = last_msg.get("id", 0)
        if msg_id <= LAST_MESSAGE_ID:
            continue

        from_id = last_msg.get("from_id", 0)
        text = last_msg.get("text", "(без текста)")
        peer_id = conv.get("peer", {}).get("id", 0)

        if from_id > 0:
            user = requests.get("https://api.vk.com/method/users.get", params={
                "access_token": VK_TOKEN,
                "v": "5.199",
                "user_ids": from_id,
            }).json()
            u = user.get("response", [{}])[0]
            sender = f"{u.get('first_name', '')} {u.get('last_name', '')}".strip()
        else:
            sender = f"Группа/бот (id{abs(from_id)})"

        messages.append({
            "id": msg_id,
            "sender": sender,
            "text": text,
            "peer_id": peer_id,
        })

    return messages

def send_telegram(text):
    requests.post(
        f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage",
        json={
            "chat_id": TG_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
        }
    )

def save_last_id(new_id):
    requests.patch(
        f"https://api.github.com/repos/{GH_REPO}/actions/variables/LAST_MESSAGE_ID",
        headers={
            "Authorization": f"Bearer {GH_TOKEN}",
            "Accept": "application/vnd.github+json",
        },
        json={"name": "LAST_MESSAGE_ID", "value": str(new_id)},
    )

def main():
    messages = vk_get_new_messages()

    if not messages:
        print("Новых сообщений нет")
        return

    max_id = LAST_MESSAGE_ID
    for msg in messages:
        text = (
            f"📩 <b>Новое сообщение ВКонтакте</b>\n"
            f"👤 От: {msg['sender']}\n"
            f"💬 {msg['text']}\n"
            f"🔗 vk.com/im?sel={msg['peer_id']}"
        )
        send_telegram(text)
        max_id = max(max_id, msg["id"])

    if max_id > LAST_MESSAGE_ID:
        save_last_id(max_id)
        print(f"Отправлено {len(messages)} уведомлений, новый last_id={max_id}")

if __name__ == "__main__":
    main()
