from audible import Authenticator, create_login


# needs at least audible v0.4.0

# if you have a valid auth file already
password = input("Password for file: ")
auth = Authenticator.from_file(filename="FILENAME", password=password)


# or register a new device
login = create_login("YOUR_COUNTRY_CODE")
prompt = login.start()
print(f"Open {prompt.verification_url} and enter the code {prompt.public_code}")
auth = login.wait()


ab = auth.get_activation_bytes()
print(ab)
