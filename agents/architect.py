"""Architect Agent: Handles worldbuilding, lore, rules, and core concepts."""

from typing import Any, Dict
from core.llm import LLMClient
from core.project import NovelProject
from core.prompts import ARCHITECT_SYSTEM, ARCHITECT_USER_TEMPLATE


class ArchitectAgent:
    """Agent responsible for setting, atmosphere, lore, and world rules."""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def generate_world_bible(self, project: NovelProject, user_note: str = "") -> Dict[str, Any]:
        """Generate a complete world bible based on project metadata, existing characters, and optional user note."""
        meta = project.metadata
        lang = meta.get("language", "Indonesian")

        characters_section = ""
        if project.characters:
            char_lines = []
            for c in project.characters:
                name = c.get("name", "Tanpa Nama")
                role = c.get("role", "Tokoh")
                goal = c.get("external_goal", "")
                backstory = c.get("backstory", "")
                char_lines.append(f"- {name} ({role}): Tujuan: {goal} | Latar Belakang: {backstory}")
            characters_section = "\nDaftar Karakter Aktif (Wajib dijadikan acuan latar & lore):\n" + "\n".join(char_lines)

        if user_note and user_note.strip():
            characters_section += f"\n\nCATATAN / REVISI WAJIB DARI PENULIS:\n{user_note.strip()}"

        system_prompt = ARCHITECT_SYSTEM.format(language=lang)
        user_prompt = ARCHITECT_USER_TEMPLATE.format(
            title=meta.get("title", "Tanpa Judul"),
            genre=meta.get("genre", "Fantasi / Fiksi Ilmiah"),
            tone=meta.get("tone", "Misterius dan Epik"),
            premise=meta.get("premise", ""),
            target_audience=meta.get("target_audience", "Umum"),
            characters_section=characters_section,
        )

        world_data = self.llm.generate_json(
            prompt=user_prompt,
            system_instruction=system_prompt,
            temperature=0.7,
        )

        project.save_world_bible(world_data)
        return world_data
