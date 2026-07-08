def remove_email():
    with open("tests/conftest.py", "r") as f:
        content = f.read()
    
    # Actually just re-assign the profile correctly without the first one.
    import re
    content = re.sub(r'profile = UserProfile\([\s\S]*?# email might not be in the model, let\'s just use what\'s required\n\s*# Looking at UserProfile, email is NOT there. user_id, tenant_id are required.\n\s*', '', content)
    
    with open("tests/conftest.py", "w") as f:
        f.write(content)
        
if __name__ == "__main__":
    remove_email()
