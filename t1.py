import os
import sys
import minecraft_launcher_lib


MINECRAFT_DIR = os.path.expanduser("~/.minecraft")


def main():
    os.makedirs(MINECRAFT_DIR, exist_ok=True)

    print("Fetching Minecraft versions...")
    versions = minecraft_launcher_lib.utils.get_available_versions(MINECRAFT_DIR)

    if not versions:
        print("No Minecraft versions found.")
        return

    print()
    print("Minecraft Versions")
    print("=" * 50)

    for i, version in enumerate(versions, 1):
        version_id = version["id"]
        version_type = version.get("type", "")
        print(f"{i:4}. {version_id:<15} {version_type}")

    print()
    print("0. Exit")

    while True:
        choice = input("\nSelect a version to download: ").strip()

        if choice == "0":
            print("Exiting.")
            return

        try:
            index = int(choice) - 1

            if index < 0 or index >= len(versions):
                raise ValueError

            selected = versions[index]["id"]
            break

        except ValueError:
            print("Invalid selection.")

    print()
    print(f"Selected: Minecraft {selected}")
    print(f"Install directory: {MINECRAFT_DIR}")
    print()

    def callback(stage):
        print(f"\r{stage:<60}", end="", flush=True)

    print("Downloading...")
    print()

    try:
        minecraft_launcher_lib.install.install_minecraft_version(
            selected,
            MINECRAFT_DIR,
            callback=callback
        )

        print()
        print()
        print("=" * 60)
        print(f"Minecraft {selected} installed successfully!")
        print("=" * 60)

    except Exception as e:
        print()
        print()
        print("Installation failed:")
        print(e)


if __name__ == "__main__":
    main()
