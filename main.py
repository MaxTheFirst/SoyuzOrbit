"""Entry point for the one-window logic PC simulation."""


def main() -> None:
    try:
        from ui.attached_screen_app import AttachedScreenApp
    except ModuleNotFoundError as exc:
        if exc.name in {"_tkinter", "tkinter"}:
            raise SystemExit(
                "Tkinter is not available in this Python build. "
                "Install a Python distribution with Tk support and run again."
            ) from exc
        raise

    app = AttachedScreenApp()
    app.run()


if __name__ == "__main__":
    main()
