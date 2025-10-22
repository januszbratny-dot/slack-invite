from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# ------------------------------
# Ustawienia
# ------------------------------
SLACK_TOKEN = "xoxb-xxxxxxxxxxxxxxxxxxxx"  # Twój Bot/User Token
CHANNEL_ID = "C0123456789"  # ID kanału, do którego dodajemy użytkowników
# ------------------------------

client = WebClient(token=SLACK_TOKEN)

def get_all_users():
    """Pobiera wszystkich użytkowników w workspace, obsługując paginację"""
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

    # Filtrujemy tylko prawdziwych członków, pomijając boty i deaktywowane konta
    real_users = [
        user for user in users
        if not user.get('is_bot', False) and user.get('deleted', False) == False
    ]
    return real_users

def invite_users_to_channel(user_ids, channel_id):
    """Dodaje użytkowników do wybranego kanału w batchach po 30 (limit Slack API)"""
    batch_size = 30
    for i in range(0, len(user_ids), batch_size):
        batch = user_ids[i:i + batch_size]
        try:
            response = client.conversations_invite(channel=channel_id, users=",".join(batch))
            print(f"Dodano użytkowników: {batch}")
        except SlackApiError as e:
            # Błędy np. 'already_in_channel' są ignorowane
            if e.response['error'] == 'already_in_channel':
                print(f"Niektórzy użytkownicy już są w kanale: {batch}")
            else:
                print(f"Błąd przy dodawaniu użytkowników: {e.response['error']}")

def main():
    users = get_all_users()
    print(f"Liczba użytkowników do dodania: {len(users)}")

    user_ids = [user['id'] for user in users]
    invite_users_to_channel(user_ids, CHANNEL_ID)

if __name__ == "__main__":
    main()
