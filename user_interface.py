class UserInterface:
    @staticmethod
    def success(message):
        print(f"✓ {message}")

    @staticmethod
    def error(message):
        print(f"✗ {message}")

    @staticmethod
    def progress(message):
        print(f"→ {message}")

    @staticmethod
    def info(message):
        print(f"ℹ {message}")

    @staticmethod
    def debug(message):
        print(f"➤ {message}")

    @staticmethod
    def warning(message):
        print(f"⚠ {message}")

    @staticmethod
    def print_requirements(requirements):
        print("\nKey Requirements:")
        print("=================")
        for idx, req in enumerate(requirements, start=1):
            print(f"{idx}. {req}")
        print("=================\n")
