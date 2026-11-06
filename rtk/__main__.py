# Entry point: 'python -m rtk' starts the toolkit.

from rtk.ui.app import ToolkitApp


def main():
    # Create and run the app
    ToolkitApp().run()


if __name__ == "__main__":
    main()
