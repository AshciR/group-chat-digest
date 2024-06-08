def get_white_list() -> list[int]:
    return [
        -1001334294461,  # Gerousia
        -1002088317098,  # Girls chat
        -4257039919,     # Test group
        -1001598674948,  # Outside 4ever
        -4170925867,     # Staging Chat
        -4239122711,     # Dev Chat
        *get_admin_list()
    ]


def get_admin_list() -> list[int]:
    return [
        170626720,  # Richie
        320338590,  # Alrick
    ]


def is_whitelisted(chat_id: int) -> bool:
    """
    Checks if a chat has the permission to use the bot
    @param chat_id:
    @return: True if it does
    """
    return chat_id in get_white_list()


def is_admin(chat_id: int) -> bool:
    """
    Check if chat belongs to an admin.
    Typically, this is used for status or debug commands.
    @param chat_id:
    @return: True if it does
    """
    return chat_id in get_admin_list()
