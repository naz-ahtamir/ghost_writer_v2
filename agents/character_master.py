"""Character Master Agent: Designs psychological character bibles and dynamics."""

from typing import Any, Dict, List
from core.llm import LLMClient
from core.project import NovelProject
from core.prompts import CHARACTER_SYSTEM, CHARACTER_USER_TEMPLATE


class CharacterMasterAgent:
    """Agent responsible for designing complex 3D characters."""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def generate_characters(self, project: NovelProject) -> List[Dict[str, Any]]:
        """Generate full cast of characters based on premise and world lore."""
        meta = project.metadata
        lang = meta.get("language", "Indonesian")

        world_summary = (
            f"Setting: {project.world_bible.get('setting_name', 'Dunia Cerita')}. "
            f"Atmosfer: {project.world_bible.get('atmosphere', '')}. "
            f"Aturan/Sistem: {project.world_bible.get('rules_and_systems', '')}"
        )

        system_prompt = CHARACTER_SYSTEM.format(language=lang)
        user_prompt = CHARACTER_USER_TEMPLATE.format(
            premise=meta.get("premise", ""),
            genre=meta.get("genre", ""),
            tone=meta.get("tone", ""),
            setting_summary=world_summary,
        )

        characters_data = self.llm.generate_json(
            prompt=user_prompt,
            system_instruction=system_prompt,
            temperature=0.75,
        )

        if isinstance(characters_data, dict):
            unpacked = None
            for key in ("characters", "cast", "tokoh", "daftar_karakter", "data"):
                if isinstance(characters_data.get(key), list):
                    unpacked = characters_data[key]
                    break
            if unpacked is None:
                for val in characters_data.values():
                    if isinstance(val, list) and val:
                        unpacked = val
                        break
            characters_data = unpacked if unpacked is not None else [characters_data]

        if not isinstance(characters_data, list):
            characters_data = [characters_data]

        project.save_characters(characters_data)
        return characters_data

    def regenerate_single_character(
        self,
        project: NovelProject,
        char_index: int,
        user_note: str = "",
    ) -> Dict[str, Any]:
        """Regenerate ONLY one specific character using AI based on a user note, preserving all others."""
        characters = list(project.characters or [])
        if not (0 <= char_index < len(characters)):
            raise IndexError("Indeks karakter tidak valid.")

        target = dict(characters[char_index])
        old_name = str(target.get("name", "")).strip()
        meta = project.metadata
        lang = meta.get("language", "Indonesian")

        other_chars = [
            f"- {c.get('name')} ({c.get('role')})"
            for idx, c in enumerate(characters)
            if idx != char_index
        ]
        other_summary = "\n".join(other_chars) or "(Tidak ada karakter lain)"

        system_prompt = CHARACTER_SYSTEM.format(language=lang)
        user_prompt = (
            f"Perbarui / rancang ulang HANYA SATU karakter berikut untuk novel '{meta.get('title', '')}' "
            f"({meta.get('genre', '')} | {meta.get('tone', '')}).\n\n"
            f"Premis Novel: {meta.get('premise', '')}\n"
            f"Latar Dunia: {project.world_bible.get('setting_name', '')}\n\n"
            f"KARAKTER SAAT INI YANG INGIN DIUBAH:\n"
            f"- Nama: {target.get('name', '')}\n"
            f"- Peran: {target.get('role', '')}\n"
            f"- Penampilan: {target.get('appearance', '')}\n"
            f"- Sifat: {target.get('personality', '')}\n"
            f"- Kelemahan (Flaw): {target.get('flaw', '')}\n"
            f"- Motivasi Dalam: {target.get('internal_motivation', '')}\n"
            f"- Tujuan Cerita: {target.get('external_goal', '')}\n"
            f"- Gaya Bicara: {target.get('speech_mannerism', '')}\n"
            f"- Backstory: {target.get('backstory', '')}\n\n"
            f"KARAKTER LAIN DALAM CERITA (JANGAN DIUBAH):\n{other_summary}\n\n"
            f"CATATAN PERBAIKAN PENULIS (WAJIB DIIKUTI):\n{user_note.strip() or 'Perdalam karakter agar lebih kuat dan hidup.'}\n\n"
            "Keluarkan HANYA 1 objek JSON karakter dengan field: "
            '{"name", "role", "archetype", "appearance", "personality", "flaw", '
            '"internal_motivation", "external_goal", "speech_mannerism", "backstory"}.'
        )

        new_char = self.llm.generate_json(
            prompt=user_prompt,
            system_instruction=system_prompt,
            temperature=0.75,
        )
        if isinstance(new_char, list) and new_char:
            new_char = new_char[0]
        if not isinstance(new_char, dict):
            raise ValueError("Respons AI untuk karakter baru bukan objek JSON yang valid.")

        new_char.setdefault("visual_dna", new_char.get("appearance", ""))
        characters[char_index] = new_char
        project.save_characters(characters)

        new_name = str(new_char.get("name", "")).strip()
        if old_name and new_name and new_name != old_name:
            project.sync_character_rename(old_name, new_name)

        return new_char

    def add_character_with_note(
        self,
        project: NovelProject,
        user_note: str,
    ) -> Dict[str, Any]:
        """Generate 1 new character from a user note and append to existing cast."""
        characters = list(project.characters or [])
        meta = project.metadata
        lang = meta.get("language", "Indonesian")

        existing_summary = "\n".join(f"- {c.get('name')} ({c.get('role')})" for c in characters) or "(Belum ada)"
        system_prompt = CHARACTER_SYSTEM.format(language=lang)
        user_prompt = (
            f"Ciptakan 1 karakter BARU untuk novel '{meta.get('title', '')}' ({meta.get('genre', '')}).\n"
            f"Premis: {meta.get('premise', '')}\n"
            f"Karakter yang sudah ada:\n{existing_summary}\n\n"
            f"ARAHAN KARAKTER BARU DARI PENULIS:\n{user_note.strip()}\n\n"
            "Keluarkan HANYA 1 objek JSON karakter dengan field: "
            '{"name", "role", "archetype", "appearance", "personality", "flaw", '
            '"internal_motivation", "external_goal", "speech_mannerism", "backstory"}.'
        )
        new_char = self.llm.generate_json(
            prompt=user_prompt,
            system_instruction=system_prompt,
            temperature=0.75,
        )
        if isinstance(new_char, list) and new_char:
            new_char = new_char[0]
        if not isinstance(new_char, dict):
            raise ValueError("Respons AI untuk karakter baru bukan objek JSON yang valid.")

        new_char.setdefault("visual_dna", new_char.get("appearance", ""))
        characters.append(new_char)
        project.save_characters(characters)
        return new_char
