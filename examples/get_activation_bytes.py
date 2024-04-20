from audible import Authenticator


# needs at least audible v0.4.0

# if you have a valid auth file already
password = input("Password for file: ")
auth = Authenticator.from_file(filename="FILENAME", password=password)


# or use LoginAuthenticator (without register)
auth = Authenticator.from_login(
    username="USERNAME",
    password="PASSWORD",  # noqa: S106
    locale="YOUR_COUNTRY_CODE",
)


ab = auth.get_activation_bytes()
print(ab)
