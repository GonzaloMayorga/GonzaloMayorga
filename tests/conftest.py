import pytest


@pytest.fixture
def config():
    return {
        "profile": {"username": "example", "name": "Example", "role": "Engineer", "location": "Argentina"},
        "system": {"os": ["Debian"]},
        "skills": {"languages": ["Python"], "backend": [], "frontend": [], "tools": ["Git"]},
        "avatar": {"width": 26, "gamma": 0.9, "remove_background": False},
        "stats": {"repos": 1, "followers": 2, "stars": 3, "commits": "--", "contributions": "--", "lines_of_code": "--"},
    }
