"""Small shared widget builders."""

from PySide6.QtWidgets import QLabel


def page_header(title: str, subtitle: str) -> tuple[QLabel, QLabel]:
    heading = QLabel(title)
    heading.setObjectName("pageTitle")
    caption = QLabel(subtitle)
    caption.setObjectName("pageSubtitle")
    return heading, caption
