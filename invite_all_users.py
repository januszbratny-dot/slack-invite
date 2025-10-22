import streamlit as st
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# --- Konfiguracja UI ---
st.set_page_config(page_title="Slack Invite Manager", page_icon="🤖", layout="wide")
st.title("🤖 Slack Invite Manager")
st.write("Aplikacja do dodawania użytkowników Slack do wybranych kanałów.")

# --- Token Slacka ---
slack_token = st.text_input(
    "Podaj swój Slack **Bot lub User Token** (xoxb-... lub xoxp-...):",
    type="password",
    placeholder="xoxb-1234567890-0987654321-AbCdEfGhIjKlMnOpQrStUvWx"
)

if not slack_token:
    st.info("🔑 Wprowadź token, aby kontynuować.")
    st.stop()

client = WebClient(token=slack_token)

# --- Funkcje pomocnicze ---

@st.cache_data(show_spinner=False)
def get_all_channels(token):
    """Pobiera wszystkie kanały (publiczne i prywatne)."""
    client = WebClient(token=token)
    channels = []
    cursor = None
    while True:
        try:
            response = client.conversations_list(
                limit=200,
                cursor=cursor,
                types="public_channel,private_channel"
            )
        except SlackApiError as e:
            st.error(f"Błąd pobierania kanałów: {e.response['error']}")
            break

        channels.extend(response['channels'])
        cursor = response.get('response_metadata', {}).get('next_cursor')
        if not cursor:
            break

    return [
        {"id": c["id"], "name": c["name"], "is_private": c.get("is_private", False)}
        for c in channels
    ]


@st.cache_data(show_spinner=False)
def get_all_users(token):
    """Pobiera wszystkich użytkowników (bez botów i skasowanych)."""
    client = WebClient(token=token)
    users = []
    cursor = None
    while True:
        try:
            response = client.users_list(limit=200, cursor=cursor)
        except SlackApiError as e:
            st.error(f"Błąd pobierania użytkowników: {e.response['error']}")
            break

        users.extend(response['members'])
        cursor = response.get('response_metadata', {}).get('next_cursor')
        if not cursor:
            break

    real_users = [
        {"id": u["id"], "name": u["profile"].get("real_name", "Nieznany użytkownik")}
        for u in users if not u.get("is_bot", False) and not u.get("deleted", False)
    ]
    return real_users


def invite_users_to_channels(token, user_ids, channel_ids):
    """Dodaje użytkowników do wielu kanałów."""
    client = WebClient(token=token)
    results = []

    for channel_id in channel_ids:
        # Spróbuj dołączyć bota do kanału (jeśli nie jest)
        try:
            client.conversations_join(channel=channel_id)
        except SlackApiError:
            pass  # ignorujemy błędy przy prywatnych kanałach

        for i in range(0, len(user_ids), 30):
            batch = user_ids[i:i + 30]
            try:
                client.conversations_invite(channel=channel_id, users=",".join(batch))
                results.append(f"✅ Dodano użytkowników: {', '.join(batch)} → kanał {channel_id}")
            except SlackApiError as e:
                if e.response['error'] == 'already_in_channel':
                    results.append(f"ℹ️ Użytkownicy już są w kanale {channel_id}: {', '.join(batch)}")
                elif e.response['error'] == 'not_in_channel':
                    results.append(f"❌ Bot nie jest w kanale {channel_id}. Dodaj go ręcznie: `/invite @bot`")
                else:
                    results.append(f"❌ Błąd: {e.response['error']} dla kanału {channel_id}")
    return results


# --- Sidebar: wybór kanałów ---
st.sidebar.header("📢 Wybierz kanały Slack")

with st.sidebar:
    with st.spinner("Pobieranie kanałów..."):
        channels = get_all_channels(slack_token)

    if channels:
        selected_channels = st.multiselect(
            "Kanały:",
            options=[c["id"] for c in channels],
            format_func=lambda cid: next(c["name"] + (" 🔒" if c["is_private"] else "") for c in channels if c["id"] == cid)
        )
    else:
        st.error("Nie udało się pobrać listy kanałów.")
        st.stop()

# --- Sekcja użytkowników ---
with st.spinner("Pobieranie użytkowników..."):
    users = get_all_users(slack_token)

if not users:
    st.error("Nie udało się pobrać użytkowników.")
    st.stop()

st.write(f"👥 Znaleziono {len(users)} aktywnych użytkowników w workspace.")
selected_users = st.multiselect(
    "Wybierz użytkowników do dodania:",
    options=[u["id"] for u in users],
    format_func=lambda uid: next(u["name"] for u in users if u["id"] == uid)
)

# --- Przycisk: dodaj użytkowników do kanałów ---
if selected_channels and selected_users:
    if st.button("🚀 Dodaj wybranych użytkowników do wybranych kanałów"):
        with st.spinner("Dodawanie użytkowników do kanałów..."):
            results = invite_users_to_channels(slack_token, selected_users, selected_channels)

        for res in results:
            st.write(res)
else:
    st.info("Wybierz przynajmniej jeden kanał i jednego użytkownika, aby rozpocząć.")
