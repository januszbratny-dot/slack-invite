import streamlit as st
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# --- Nagłówek aplikacji ---
st.title("🤖 Slack Invite Manager")
st.write("Aplikacja do dodawania użytkowników Slack do kanałów.")

# --- Wprowadzenie tokena ---
token = st.text_input(
    "Podaj swój Slack Bot Token (format: xoxb-...):",
    type="password",
    help="Token znajdziesz w Slack API → Your App → OAuth & Permissions → Bot User OAuth Token"
)

if not token:
    st.warning("Podaj token bota, aby kontynuować.")
    st.stop()

# --- Inicjalizacja klienta Slacka ---
client = WebClient(token=token)

# --- Funkcje pomocnicze ---

@st.cache_data(show_spinner=False)
def get_channel_id(channel_name):
    """Pobiera ID kanału po nazwie."""
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
            return None

        for channel in response['channels']:
            if channel['name'] == channel_name:
                return channel['id']

        cursor = response.get('response_metadata', {}).get('next_cursor')
        if not cursor:
            break
    return None


@st.cache_data(show_spinner=False)
def get_all_users():
    """Pobiera wszystkich użytkowników (bez botów i skasowanych)."""
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


def invite_users_to_channel(user_ids, channel_id):
    """Dodaje użytkowników do kanału w batchach po 30."""
    batch_size = 30
    results = []
    for i in range(0, len(user_ids), batch_size):
        batch = user_ids[i:i + batch_size]
        try:
            client.conversations_invite(channel=channel_id, users=",".join(batch))
            results.append(f"✅ Dodano użytkowników: {', '.join(batch)}")
        except SlackApiError as e:
            if e.response['error'] == 'already_in_channel':
                results.append(f"ℹ️ Część użytkowników już w kanale: {', '.join(batch)}")
            else:
                results.append(f"❌ Błąd: {e.response['error']} dla batcha {batch}")
    return results

# --- UI: kanał i użytkownicy ---

channel_name = st.text_input("Podaj nazwę kanału (bez #):", placeholder="np. projekty")

if channel_name:
    with st.spinner("🔍 Szukanie kanału..."):
        channel_id = get_channel_id(channel_name)

    if not channel_id:
        st.error(f"Nie znaleziono kanału **{channel_name}**.")
        st.stop()
    else:
        st.success(f"Znaleziono kanał `{channel_name}` (ID: {channel_id})")

        with st.spinner("📥 Pobieranie listy użytkowników..."):
            users = get_all_users()

        if users:
            st.write(f"👥 Znaleziono {len(users)} aktywnych użytkowników w workspace.")

            # Multiselect użytkowników
            selected_users = st.multiselect(
                "Wybierz użytkowników do dodania:",
                options=[u["id"] for u in users],
                format_func=lambda uid: next(u["name"] for u in users if u["id"] == uid)
            )

            col1, col2 = st.columns(2)

            # Przycisk: Dodaj wybranych
            with col1:
                if st.button("🚀 Dodaj wybranych użytkowników"):
                    if not selected_users:
                        st.warning("Nie wybrano żadnych użytkowników.")
                    else:
                        with st.spinner("Dodawanie wybranych użytkowników..."):
                            results = invite_users_to_channel(selected_users, channel_id)
                        for res in results:
                            st.write(res)

            # Przycisk: Dodaj wszystkich
            with col2:
                if st.button("👥 Dodaj wszystkich użytkowników"):
                    all_user_ids = [u["id"] for u in users]
                    with st.spinner("Dodawanie wszystkich użytkowników..."):
                        results = invite_users_to_channel(all_user_ids, channel_id)
                    for res in results:
                        st.write(res)
        else:
            st.error("Nie udało się pobrać listy użytkowników.")
