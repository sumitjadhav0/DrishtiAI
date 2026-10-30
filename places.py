"""places.py - College chya jaga. Navin jaga add karaychi asel tar ethe ek block add kara.
prompt = CLIP la jagecha English description
name/tip = bolnyasathi (en / hi / mr)"""

PLACES = {
    "classroom": {
        "prompt": "a photo of a college classroom with benches, desks and a whiteboard",
        "name": {"en": "classroom", "hi": "कक्षा", "mr": "क्लासरूम"},
        "tip": {"en": "Benches and desks are around you. Walk slowly.",
                "hi": "आपके आसपास बेंच और डेस्क हैं. धीरे चलिए.",
                "mr": "तुमच्या आजूबाजूला बेंच आणि डेस्क आहेत. हळू चाला."},
    },
    "computer_lab": {
        "prompt": "a photo of a computer lab with rows of desktop computers and monitors on tables",
        "name": {"en": "computer lab", "hi": "कंप्यूटर लैब", "mr": "कॉम्प्युटर लॅब"},
        "tip": {"en": "Computer tables and wires may be around. Walk carefully.",
                "hi": "आसपास कंप्यूटर टेबल और तार हो सकते हैं. सावधानी से चलिए.",
                "mr": "आजूबाजूला कॉम्प्युटर टेबल आणि वायर असू शकतात. सावधपणे चाला."},
    },
    "science_lab": {
        "prompt": "a photo of a science laboratory with lab benches, equipment and glass apparatus",
        "name": {"en": "science lab", "hi": "विज्ञान प्रयोगशाला", "mr": "सायन्स लॅब"},
        "tip": {"en": "Lab equipment is on the tables. Do not touch anything.",
                "hi": "टेबल पर उपकरण हैं. कुछ भी मत छुइए.",
                "mr": "टेबलवर उपकरणे आहेत. काहीही हात लावू नका."},
    },
    "corridor": {
        "prompt": "a photo of a long college corridor with doors on the sides",
        "name": {"en": "corridor", "hi": "गलियारा", "mr": "कॉरिडॉर"},
        "tip": {"en": "Doors are on both sides. Keep walking straight.",
                "hi": "दोनों तरफ़ दरवाज़े हैं. सीधे चलिए.",
                "mr": "दोन्ही बाजूला दरवाजे आहेत. सरळ चाला."},
    },
    "library": {
        "prompt": "a photo of a library with bookshelves and reading tables",
        "name": {"en": "library", "hi": "पुस्तकालय", "mr": "ग्रंथालय"},
        "tip": {"en": "Bookshelves and tables are around. Please walk quietly.",
                "hi": "आसपास किताबों की अलमारियाँ और टेबल हैं. शांति से चलिए.",
                "mr": "आजूबाजूला पुस्तकांची कपाटे आणि टेबल आहेत. शांतपणे चाला."},
    },
    "canteen": {
        "prompt": "a photo of a college canteen cafeteria with tables, chairs and people eating",
        "name": {"en": "canteen", "hi": "कैंटीन", "mr": "कॅन्टीन"},
        "tip": {"en": "Many tables and people. Move slowly.",
                "hi": "बहुत टेबल और लोग हैं. धीरे चलिए.",
                "mr": "खूप टेबल आणि लोक आहेत. हळू चाला."},
    },
    "staircase": {
        "prompt": "a photo of a staircase inside a building",
        "name": {"en": "staircase", "hi": "सीढ़ियाँ", "mr": "जिना"},
        "tip": {"en": "Stairs ahead. Hold the railing.",
                "hi": "आगे सीढ़ियाँ हैं. रेलिंग पकड़िए.",
                "mr": "समोर जिना आहे. रेलिंग पकडा."},
    },
    "outdoor": {
        "prompt": "a photo of an outdoor college campus with a road, trees and buildings",
        "name": {"en": "outdoor campus", "hi": "कैंपस के बाहर", "mr": "कॅम्पसच्या बाहेर"},
        "tip": {"en": "You are outside. Watch for vehicles.",
                "hi": "आप बाहर हैं. गाड़ियों से सावधान रहिए.",
                "mr": "तुम्ही बाहेर आहात. गाड्यांपासून सावध रहा."},
    },
}
