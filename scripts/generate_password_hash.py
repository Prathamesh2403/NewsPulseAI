import sys
import bcrypt
import getpass

def main():
    if len(sys.argv) > 1:
        password = sys.argv[1]
    else:
        password = getpass.getpass("Enter password to hash: ")
        
    # Generate salt and hash password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    
    print("\nPassword Hash:")
    print(hashed.decode("utf-8"))
    print("\nCopy this hash and add it to your .env file as ADMIN_PASSWORD_HASH")

if __name__ == "__main__":
    main()
