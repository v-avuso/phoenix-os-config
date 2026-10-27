"""Presentation defaults for Hue's native source-consent dialog."""
APP_ID = "org.phoenix.HueSync"


def picker_arguments(app_id, arguments):
    arguments = list(arguments)
    if app_id == APP_ID and "--allow-token" not in arguments:
        arguments.append("--allow-token")
    return arguments
