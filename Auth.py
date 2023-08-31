from msal import PublicClientApplication
#e1fe6dd8-ba31-4d61-89e7-88639da4683d
#1fadd20b-033c-40fa-a0a7-59d9b9069ec4
#
app = PublicClientApplication(
    "b6b714d1-8627-4706-b42c-f1e56167e559",#/.auth/login/aad/callback",
    authority="https://login.microsoftonline.com")

result = None  # It is just an initial value. Please follow instructions below.

# We now check the cache to see
# whether we already have some accounts that the end user already used to sign in before.
accounts = app.get_accounts()
if accounts:
    # If so, you could then somehow display these accounts and let end user choose
    print("Pick the account you want to use to proceed:")
    for a in accounts:
        print(a["username"])
    # Assuming the end user chose this one
    chosen = accounts[0]
    # Now let's try to find a token in cache for this account
    result = app.acquire_token_silent(["User.Read"], account=chosen)
    
if not result:
    # So no suitable token exists in cache. Let's get a new one from Azure AD.
    result = app.acquire_token_interactive(scopes=["User.Read"])

if "access_token" in result:
    print(result["access_token"])  # Yay!
else:
    print(result.get("error"))
    print(result.get("error_description"))
    print(result.get("correlation_id"))  # You may need this when reporting a bug
    
    