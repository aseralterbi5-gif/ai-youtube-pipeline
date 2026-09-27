"""Generate a YouTube upload refresh token for local use, once."""

from getpass import getpass

from google_auth_oauthlib.flow import InstalledAppFlow


SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def main() -> None:
    client_id = input("Google OAuth Client ID: ").strip()
    client_secret = getpass("Google OAuth Client Secret: ").strip()
    if not client_id or not client_secret:
        raise SystemExit("Client ID and Client Secret are required.")

    flow = InstalledAppFlow.from_client_config(
        {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost"],
            }
        },
        SCOPES,
    )
    credentials = flow.run_local_server(port=0)
    if not credentials.refresh_token:
        raise SystemExit(
            "Google did not return a refresh token. Revoke prior access and try again."
        )

    print("\nYT_REFRESH_TOKEN (store this as a GitHub Actions secret):")
    print(credentials.refresh_token)


if __name__ == "__main__":
    main()
