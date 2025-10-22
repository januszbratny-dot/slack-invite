import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

# Wczytanie zmiennych środowiskowych
load_dotenv()

SLACK_TOKEN = os.getenv("SLACK_TOKEN")
CHANNEL_NAME = os.getenv("CHANNEL_NAME")

if not SLACK_TOKEN or not CHANNEL_NAME:
    raise ValueError("Brakuje SLACK_TOKEN lub CHANNEL_NAME w zmiennych środowiskowych.")

client = WebClient(token=SLACK_TOKEN)

def get_channel_id(channel_name):
    """Pobiera ID kanału po nazwie, obsługując paginację."""
    cursor = None
    while True:
        try:
            response = client.conversations_list(
                limit=200,
                cursor=cursor,
                types="public_channel,private_channel"
            )
        except SlackApiError as e:
            print(f"Błąd pobierania kanałów: {e.response['error']}")
            return None

        for channel in response['channels']:
            if channel['name'] == channel_name:
                return channel['id']

        cursor = response.get('response_metadata', {}).get('next_cursor')
        if not cursor:
            break

    print(f"Nie znaleziono kanału o nazwie: {channel_name}")
    return None

def get_all_users():
    """Pobiera wszystkich użytkowników w workspace Slack."""
    users = []
    cursor = None

    while True:
        try:
            response = client.users_list(limit=200, cursor=cursor)
        except SlackApiError as e:
            print(f"Błąd pobierania użytkowników: {e.response['error']}")
            break

        users.extend(response['members'])
        cursor = response.get('response_metadata', {}).get('next_cursor')
        if not cursor:
            break

    # Filtrujemy tylko prawdziwych członków
    real_users = [
        user for user in users
        if not user.get('is_bot', False) and not user.get('deleted', False)
    ]
    return real_users

def invite_users_to_channel(user_ids, channel_id):
    """Dodaje użytkowników do kanału w batchach po 30."""
    batch_size = 30
    for i in range(0, len(user_ids), batch_size):
        batch = user_ids[i:i + batch_size]
        try:
            client.conversations_invite(channel=channel_id, users=",".join(batch))
            print(f"Dodano użytkowników: {batch}")
        except SlackApiError as e:
            if e.response['error'] == 'already_in_channel':
                print(f"Niektórzy użytkownicy już są w kanale: {batch}")
            else:
                print(f"Błąd przy dodawaniu użytkowników: {e.response['error']}")

def main():
    channel_id = get_channel_id(CHANNEL_NAME)
    if not channel_id:
        return

    print(f"ID kanału '{CHANNEL_NAME}' to: {channel_id}")
    users = get_all_users()
    print(f"Liczba użytkowników do dodania: {len(users)}")

    user_ids = [user['id'] for user in users]
    invite_users_to_channel(user_ids, channel_id)

if __name__ == "__main__":
    main()
