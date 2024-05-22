
def get_white_list() -> list[int]:
    white_list = [
        -1001334294461, #Gerousia
        -4170925867, #CNS
        170626720, #Richie
        320338590, #Alrick
    ]

    return white_list

def is_whitelisted(chat_id:int) -> bool:
    white_list = get_white_list()
    return chat_id in white_list