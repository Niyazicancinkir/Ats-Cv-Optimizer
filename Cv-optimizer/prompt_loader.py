import json

from path_utils import project_path


def _load_prompt_templates(prompt_file="prompt.json"):
    with open(project_path(prompt_file), "r", encoding="utf-8") as file:
        return json.load(file)


def render_prompt(prompt_key, replacements, prompt_file="prompt.json"):
    templates = _load_prompt_templates(prompt_file)
    template = templates.get(prompt_key)
    if template is None:
        raise KeyError(f"Prompt key bulunamadi: {prompt_key}")

    rendered = template
    for key, value in replacements.items():
        rendered = rendered.replace("{{" + key + "}}", str(value))
    return rendered