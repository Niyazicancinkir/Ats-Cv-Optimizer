import json

from path_utils import project_path


def load_json(relative_path):
    with open(project_path(relative_path), "r", encoding="utf-8") as file:
        return json.load(file)


def load_text(relative_path):
    with open(project_path(relative_path), "r", encoding="utf-8") as file:
        return file.read()