
def get_white_list() -> list[int]:
    white_list = [
        -1001334294461,  # Gerousia
        -1002088317098,  # Girls chat
        -4257039919,     # Test group
        -1001598674948,  # Outside 4ever
        -4170925867,     # Staging Chat
        -4239122711,     # Dev Chat
        170626720,       # Richie
        320338590,       # Alrick
    ]

    return white_list


def is_whitelisted(chat_id:int) -> bool:
    white_list = get_white_list()
    return chat_id in white_list