from app.db.models import Note


class VersionConflict(Exception):
    """Версия заметки у клиента устарела. Несёт актуальное состояние для ответа 409."""

    def __init__(self, note: Note):
        self.note = note