"""Upload checks for team documents. No API keys or network needed."""
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.team_docs import TeamDocError, is_team_id, new_team_id, text_from_file


def test_team_ids_are_long_random_and_validated():
    ids = {new_team_id() for _ in range(50)}
    assert len(ids) == 50 and all(is_team_id(i) for i in ids)
    for bad in ["", "short", "../../etc/passwd", "a" * 23, "has space in it.......", None]:
        assert not is_team_id(bad), bad


def test_text_and_markdown_files_are_read():
    assert text_from_file("retro.md", "# Retro\nReviews took 4 days.".encode()) == "# Retro\nReviews took 4 days."
    assert "caf" in text_from_file("notes.txt", b"caf\xe9 broken byte")  # bad bytes don't crash it


def test_unsupported_and_oversized_files_are_refused():
    for name, data in [("slides.pptx", b"x"), ("doc.docx", b"x"), ("big.txt", b"x" * 2_000_001)]:
        try:
            text_from_file(name, data)
            raise AssertionError(f"{name} should have been refused")
        except TeamDocError:
            pass


def test_broken_pdf_gives_a_clear_message():
    try:
        text_from_file("report.pdf", b"not really a pdf")
        raise AssertionError("broken PDF should have been refused")
    except TeamDocError as e:
        assert "PDF" in str(e)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"PASS {name}")
