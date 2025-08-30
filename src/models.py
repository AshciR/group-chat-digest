from dataclasses import dataclass
from telegram import Update


@dataclass
class Message:
    """Stores the content of the messages"""
    message_id: int
    content: str
    owner_id: int
    owner_name: str
    created_at: str

    @staticmethod
    def convert_update_to_owner(update: Update):
        if not update.message.from_user.last_name:
            return f"{update.message.from_user.first_name}"

        return f"{update.message.from_user.first_name} {update.message.from_user.last_name}"