import os

def add_inits(root_dir):
    for root, dirs, files in os.walk(root_dir):
        init_path = os.path.join(root, "__init__.py")
        if not os.path.exists(init_path):
            with open(init_path, "w") as f:
                pass

if __name__ == "__main__":
    add_inits("tests")
