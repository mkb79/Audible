import audible

# needs at least audible v0.4.0

# if you have a valid auth file already
password = input("Password for file: ")
auth = audible.FileAuthenticator(
    filename="FILENAME",
    password=password
)

    
# or use LoginAuthenticator (without register)
auth = audible.LoginAuthenticator(
    username="USERNAME",
    password="PASSWORD",
    locale="YOUR_COUNTRY_CODE",
    register=False
)


ab = auth.get_activation_bytes()
print(ab)
