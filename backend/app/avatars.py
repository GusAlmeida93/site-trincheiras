"""Fixed avatar catalogue.

Deploy-time constants tied to the PNGs in app/static/avatars/ — deliberately
not database content.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Avatar:
    id: str
    label: str
    url: str


_MALE_LABELS = [
    "Soldado britânico",
    "Soldado europeu",
    "Soldado americano",
    "Soldado asiático",
    "Soldado indiano",
    "Soldado irlandês",
    "Soldado otomano",
    "Soldado francês",
    "Soldado brasileiro",
    "Soldado colonial",
]
_FEMALE_LABELS = [
    "Enfermeira militar",
    "Auxiliar do exército",
    "Soldada latina",
    "Enfermeira asiática",
    "Auxiliar indiana",
    "Oficial loira",
    "Enfermeira indígena",
    "Enfermeira Cruz Vermelha",
    "Telegrafista militar",
    "Enfermeira mestiça",
]

AVATARS: list[Avatar] = [
    Avatar(id=f"m-{i}", label=label, url=f"/static/avatars/avatar_m{i}.png")
    for i, label in enumerate(_MALE_LABELS, start=1)
] + [
    Avatar(id=f"f-{i}", label=label, url=f"/static/avatars/avatar_f{i}.png")
    for i, label in enumerate(_FEMALE_LABELS, start=1)
]
