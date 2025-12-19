import pytest
from app.ml.summarizer import generate_short_description

def test_generate_short_description():
    title = "Event Title"
    description = "This is a long event description. It should be summarized."
    summary = generate_short_description(title=title, description=description)
    assert isinstance(summary, str)
    assert len(summary) > 0
