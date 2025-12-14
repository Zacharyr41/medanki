import genanki

CLOZE_MODEL_ID = 1607392319001
VIGNETTE_MODEL_ID = 1607392319003

CARD_CSS = """
.card {
    font-family: arial;
    font-size: 20px;
    text-align: center;
    color: black;
    background-color: white;
}

.cloze {
    font-weight: bold;
    color: blue;
}

.extra {
    font-size: 16px;
    color: #555;
    margin-top: 10px;
}

.source {
    font-size: 12px;
    color: #999;
    margin-top: 20px;
}
"""


def get_cloze_model() -> genanki.Model:
    return genanki.Model(
        CLOZE_MODEL_ID,
        "MedAnki Cloze",
        fields=[
            {"name": "Text"},
            {"name": "Extra"},
            {"name": "Source"},
        ],
        templates=[
            {
                "name": "Cloze Card",
                "qfmt": "{{cloze:Text}}",
                "afmt": "{{cloze:Text}}<br><div class='extra'>{{Extra}}</div><div class='source'>{{Source}}</div>",
            },
        ],
        css=CARD_CSS,
        model_type=genanki.Model.CLOZE,
    )


def get_vignette_model() -> genanki.Model:
    return genanki.Model(
        VIGNETTE_MODEL_ID,
        "MedAnki Vignette",
        fields=[
            {"name": "Front"},
            {"name": "Answer"},
            {"name": "Explanation"},
            {"name": "DistinguishingFeature"},
            {"name": "Source"},
        ],
        templates=[
            {
                "name": "Vignette Card",
                "qfmt": "{{Front}}",
                "afmt": """{{FrontSide}}<hr id='answer'>
<div class='answer'><b>{{Answer}}</b></div>
<div class='explanation'>{{Explanation}}</div>
<div class='distinguishing'>Key Feature: {{DistinguishingFeature}}</div>
<div class='source'>{{Source}}</div>""",
            },
        ],
        css=CARD_CSS,
        model_type=genanki.Model.FRONT_BACK,
    )
