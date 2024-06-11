from white_list import is_whitelisted, is_admin


def test_is_admin():
    expected_admin_list = [170626720, 320338590]

    for chat_id in expected_admin_list:
        assert is_admin(chat_id)


def test_is_admin_returns_false():
    un_allowed_chat_id = 1234
    assert not is_admin(un_allowed_chat_id)


def test_is_whitelisted_returns_true():
    expected_whitelisted_ids = [
        -1001334294461,  # Gerousia
        -1002088317098,  # Girls chat
        -4257039919,  # Test group
        -1001598674948,  # Outside 4ever
        -4170925867,  # Staging Chat
        -4239122711,  # Dev Chat
        170626720,  # Richie (admin)
        320338590  # Alrick (admin)
    ]

    for chat_id in expected_whitelisted_ids:
        assert is_whitelisted(chat_id)


def test_is_whitelisted_returns_false():
    un_allowed_chat_id = 1234
    assert not is_whitelisted(un_allowed_chat_id)
