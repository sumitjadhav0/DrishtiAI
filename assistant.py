"""assistant.py - 'Mitra': friend sarkha bolnara assistant.
 * Voice command samajto (English / Hindi / Marathi)
 * Fakt model chya khara data varun uttar deto (kalpana nahi)
 * Jaga shikto (teach), blueprint save karto, ani 'mala baher jaych ahe' mhantlyavar step-by-step rasta sangto"""
import datetime
import random
import re
import threading

from navmap import norm
from places import PLACES

FRIEND = {"en": "my friend", "hi": "दोस्त", "mr": "मित्रा"}
TOD = {"en": ["morning", "afternoon", "evening", "night"],
       "hi": ["सुप्रभात", "नमस्कार", "शुभ संध्या", "शुभ रात्रि"],
       "mr": ["सुप्रभात", "नमस्कार", "शुभ संध्या", "शुभ रात्री"]}
GREET = {"en": "Good {}", "hi": "{}", "mr": "{}"}
WEEK = {"hi": ["सोमवार", "मंगलवार", "बुधवार", "गुरुवार", "शुक्रवार", "शनिवार", "रविवार"],
        "mr": ["सोमवार", "मंगळवार", "बुधवार", "गुरुवार", "शुक्रवार", "शनिवार", "रविवार"]}
MONTH = {"hi": ["जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर"],
         "mr": ["जानेवारी", "फेब्रुवारी", "मार्च", "एप्रिल", "मे", "जून", "जुलै", "ऑगस्ट", "सप्टेंबर", "ऑक्टोबर", "नोव्हेंबर", "डिसेंबर"]}

# ---------------------------------------------------------------- INTENTS
# Order mahatvacha: pahile match zalela intent ghetla jato. ASCII shabd 'whole word' mhanun match hotat.
INTENTS = {
    "lang_en": ["english", "इंग्लिश", "अंग्रेजी", "अंग्रेज़ी", "इंग्रजी"],
    "lang_hi": ["hindi", "हिंदी", "हिन्दी"],
    "lang_mr": ["marathi", "मराठी"],
    "nav_cancel": ["stop guiding", "cancel navigation", "stop navigation", "cancel route", "नेविगेशन बंद",
                   "रास्ता बताना बंद", "मार्गदर्शन बंद", "रस्ता सांगणे बंद", "रुक जाओ"],
    "pause": ["stop talking", "be quiet", "quiet", "silence", "चुप", "शांत", "बोलना बंद", "बोलणे बंद",
              "बंद कर", "गप्प"],
    "resume": ["start guiding", "start talking", "resume", "continue", "चालू करो", "शुरू करो", "सुरू कर",
               "सुरु कर", "गाइड"],
    "teach_stop": ["done teaching", "stop teaching", "finish teaching", "teaching done", "सिखाना खत्म",
                   "सिखाना बंद", "शिकवणे संपले", "शिकवणे बंद"],
    "save_place": ["remember this place", "save this place", "learn this place", "this place is",
                   "यह जगह याद", "यह जगह सेव", "ही जागा लक्षात", "ही जागा सेव"],
    "teach_start": ["start teaching", "teach you", "teach mode", "learn my home", "सिखाना शुरू", "सिखाता हूँ",
                    "सिखाऊं", "शिकवतो", "शिकवायचे", "शिकवायचं"],
    "forget": ["forget my notes", "forget everything", "delete my notes", "नोट्स मिटा", "भूल जाओ", "नोंदी पुसा"],
    "remember": ["remember that", "remember this", "note that", "याद रखो", "लक्षात ठेव", "लिख लो", "नोट कर"],
    "recall": ["what did i tell you", "what do you remember", "my notes", "read my notes", "क्या याद है",
               "मैंने क्या कहा", "काय लक्षात आहे", "मी काय सांगितले", "नोट्स"],
    "ask_name": ["what is my name", "who am i", "मेरा नाम क्या", "माझे नाव काय", "माझं नाव काय"],
    "set_name": ["my name is", "call me", "मेरा नाम", "माझे नाव", "माझं नाव"],
    "who": ["who are you", "your name", "तुम कौन", "तुम्हारा नाम", "तू कोण", "तुझे नाव", "तुमचे नाव", "तुम्ही कोण"],
    "places": ["what places", "which places", "places do you know", "कौन सी जगह", "कोणत्या जागा"],
    "hazard": ["stairs", "stair", "pothole", "hole", "सीढ़ी", "सीढ़ियां", "सीढ़ियाँ", "सीढी", "पायऱ्या",
               "पायरी", "जिना", "गड्ढा", "गड्डा", "खड्डा"],
    "navigate": ["take me", "go to", "i want to go", "want to go", "how do i get", "guide me to", "get me to",
                 "मुझे जाना", "जाना है", "ले चलो", "ले जाओ", "मला जायचं", "मला जायचे", "जायचं आहे",
                 "जायचे आहे", "जायचंय", "घेऊन चल", "घेऊन जा", "बाहर जाना", "बाहेर जायचं", "बाहेर जायचे"],
    "next_step": ["i reached", "reached", "next step", "next", "पहुँच गया", "पहुंच गया", "पहुँच गई", "अगला",
                  "पोहोचलो", "पोहोचले", "पुढचे", "पुढची पायरी"],
    "repeat": ["repeat", "say again", "once more", "फिर से", "दोबारा", "पुन्हा", "परत सांग"],
    "where": ["where am i", "which place", "where are we", "मैं कहाँ", "मैं कहां", "मै कहा", "कहाँ हूँ",
              "कहां हूं", "मी कुठे", "कुठे आहे", "कुठे आहोत"],
    "people": ["how many people", "anyone", "any one", "कितने लोग", "कितने व्यक्ति", "किती लोक", "किती माणसे",
               "कोई है", "कोणी आहे"],
    "ahead": ["in front", "ahead", "सामने", "समोर"],
    "around": ["around me", "surround", "around", "आसपास", "आस-पास", "आजूबाजू", "आजूबाजूला", "बाजूला"],
    "safe": ["safe", "clear", "can i walk", "रास्ता", "रस्ता", "सुरक्षित", "चल सकता", "चालू शकतो"],
    "time": ["what time", "time is it", "current time", "क्या समय", "कितने बजे", "टाइम", "किती वाजले",
             "वेळ काय", "किती वाजता"],
    "date": ["what day", "today's date", "what is the date", "date today", "आज कौन सा दिन", "आज की तारीख",
             "तारीख", "आज कोणता दिवस", "आजची तारीख"],
    "how_are_you": ["how are you", "कैसे हो", "कैसे हैं", "क्या हाल", "कसा आहेस", "कसे आहात", "तू कसा आहेस"],
    "thanks": ["thank you", "thanks", "शुक्रिया", "धन्यवाद", "थैंक"],
    "greet": ["hello", "hey mitra", "hi mitra", "good morning", "good afternoon", "good evening", "good night",
              "नमस्कार", "नमस्ते", "सुप्रभात", "हैलो", "हॅलो", "हाय", "शुभ संध्या", "शुभ रात्रि", "शुभ रात्री"],
    "help": ["help", "मदद", "मदत", "क्या कर सकते", "काय करू शकतोस", "काय करू शकता"],
}
AT_MARKERS = ["i am in", "i am at", "i'm in", "i'm at", "i am near", "मैं", "मै", "मी"]
MITRA_RE = re.compile(r"\bmitra\b|मित्र|मित्रा")
SKIP = {"skip", "no", "नहीं", "नही", "नको", "छोड़ो", "छोडो", "सोडा", "रहने दो", "राहू दे", "no thanks"}
CANCEL = {"cancel", "stop", "रद्द", "रहने दो", "राहू दे", "नको", "रुको", "थांब"}


def match_intent(text):
    t = text.lower()
    for intent, words in INTENTS.items():
        for w in words:
            if w.isascii():
                if re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", t):
                    return intent
            elif w in t:
                return intent
    return None


# ---------------------------------------------------------------- REPLIES (friend sarkhe)
R = {
 "en": {
  "hello": ["{tod}, {n}! I'm Mitra, right here with you. Tell me what you need.",
            "{tod} {n}! Good to hear you. I'm with you. What shall we do?"],
  "how_are_you": "I'm doing great, {n}. Thanks for asking! How about you?",
  "thanks": ["You're most welcome, {n}. That's what friends are for.", "Anytime, {n}! I'm always here."],
  "who_are_you": "I'm Mitra, your friend and guide. I can tell you what's around you, where you are, warn you about danger, and walk you to places I have learned.",
  "name_set": "Nice to meet you, {name}! I'll remember your name.",
  "name_known": "Your name is {name}.",
  "name_unknown": "I don't know your name yet. Tell me: my name is, and then your name.",
  "time": "It's {time} right now, {n}.",
  "date": "Today is {date}, {n}.",
  "note_ask": "Sure. What should I remember?",
  "note_ok": "Okay {n}, I'll remember that.",
  "notes_list": "You told me: {notes}.",
  "notes_none": "You haven't asked me to remember anything yet.",
  "notes_cleared": "Okay, I've forgotten your notes.",
  "where_node": "You're at the {node}, in the {site}, {n}.",
  "where_sure": "You're in the {place}, {n}.",
  "where_maybe": "I think you're in the {place}, {n}, but I'm not completely sure.",
  "where_unknown": "I'm not sure where you are right now, {n}.",
  "no_scene": "Place recognition isn't available right now.",
  "ahead": "In front of you: {items}.",
  "ahead_none": "I don't see anything in front of you right now.",
  "around": "Around you: {items}.",
  "around_none": "I don't see anything around you right now.",
  "people": "I can see {num} people.",
  "people_one": "I can see one person.",
  "people_none": "I don't see anyone right now.",
  "safe_obs": "Be careful, {n}. {items}.",
  "safe_none": "I don't see anything close to you, {n}, but I can miss things. Please walk carefully.",
  "paused": "Okay, I'll stay quiet. I'll still warn you if there is danger.",
  "resumed": "Okay {n}, I'm guiding you again.",
  "lang_ok": "Okay, I'll speak English now.",
  "hazard_found": "Careful! {items}.",
  "hazard_none": "I don't see stairs or holes right now.",
  "hazard_nomodel": "My stairs and hole model isn't installed, so I can't detect them. Please be careful.",
  "help": "You can talk to me like a friend. Ask: where am I, what's in front, what's around me, how many people, is it safe, what time is it. Say: take me outside, repeat, stop talking, start guiding. I can also remember things: say remember that, and then tell me.",
  "unknown": "Sorry {n}, I didn't catch that. Say help and I'll tell you what I can do.",
  "no_camera": "My camera isn't giving me a picture right now.",
  "repeat_none": "I have nothing to repeat yet.",
  "pos_set": "Okay {n}, I'll take it that you're at the {node}.",
  "places_known": "I know these places: {places}.",
  "nav_no_places": "I haven't learned any places yet, {n}. Please ask someone to teach me your home first.",
  "nav_unknown_target": "Where would you like to go, {n}? I know: {places}.",
  "nav_not_localized": "I'm not sure where you are right now, {n}. Please tell me, for example: I am in the {example}.",
  "nav_start": "Okay {n}, let's go to the {target}. I'll tell you step by step. First:",
  "nav_already": "You're already at the {target}, {n}.",
  "nav_no_route": "I don't know the way from the {a} to the {b} yet. Please ask someone to teach me that path.",
  "nav_next": "Good, you've reached the {node}. Next:",
  "nav_arrived": "We've arrived at the {target}, {n}. Well done!",
  "nav_lost": "I can't tell where you are right now, {n}. Please stop and tell me where you are, or say repeat to hear the last step.",
  "nav_remind": "Still heading to the {target}. Here's the step again:",
  "nav_replan": "I see you're at the {node} now. Let me guide you from here:",
  "nav_cancel": "Okay, I've stopped guiding. I'm still with you.",
  "nav_none_active": "I'm not guiding you anywhere right now.",
  "nav_generic": "Walk carefully towards the {b}.",
  "teach_start": "Okay, let's teach me a place. Which place is it, for example home or college?",
  "teach_site_set": "Alright, {site}. Now stand at a spot, hold the camera steady, and say: remember this place.",
  "teach_no_clip": "I can't learn places because my picture model isn't available.",
  "teach_no_camera": "My camera isn't giving me a picture. Please start the camera first.",
  "teach_ask_name": "What should I call this place?",
  "teach_hold": "Hold still, I'm taking pictures.",
  "teach_saved": "Saved {name}. I took {k} pictures.",
  "teach_ask_instr": "How do I walk from the {a} to the {b}? Tell me in your own words, or say skip.",
  "teach_ask_rev": "And how do I walk back, from the {b} to the {a}? Or say skip.",
  "teach_instr_saved": "Got it.",
  "teach_done": "Okay, teaching finished. I now know {num} places.",
  "teach_cancel": "Okay, cancelled.",
 },
 "hi": {
  "hello": "{tod} {n}! मैं मित्र हूँ, आपके साथ हूँ. बताइए, क्या करना है?",
  "how_are_you": "मैं बढ़िया हूँ {n}, पूछने के लिए शुक्रिया! आप कैसे हैं?",
  "thanks": ["कोई बात नहीं {n}, दोस्त किसलिए होते हैं!", "हमेशा {n}! मैं यहीं हूँ."],
  "who_are_you": "मैं मित्र हूँ, आपका दोस्त और गाइड. मैं बता सकता हूँ कि आपके आसपास क्या है, आप कहाँ हैं, खतरे से सावधान कर सकता हूँ, और सीखी हुई जगहों तक रास्ता बता सकता हूँ.",
  "name_set": "आपसे मिलकर अच्छा लगा {name}! मैं आपका नाम याद रखूँगा.",
  "name_known": "आपका नाम {name} है.",
  "name_unknown": "मुझे अभी आपका नाम नहीं पता. कहिए: मेरा नाम, और फिर अपना नाम.",
  "time": "समय है {time}, {n}.",
  "date": "आज {date} है, {n}.",
  "note_ask": "ज़रूर. मुझे क्या याद रखना है?",
  "note_ok": "ठीक है {n}, मैं याद रखूँगा.",
  "notes_list": "आपने मुझसे कहा था: {notes}.",
  "notes_none": "आपने अभी तक मुझे कुछ याद रखने को नहीं कहा.",
  "notes_cleared": "ठीक है, मैंने आपके नोट्स भुला दिए.",
  "where_node": "आप {site} में {node} पर हैं, {n}.",
  "where_sure": "आप {place} में हैं, {n}.",
  "where_maybe": "मुझे लगता है आप {place} में हैं, {n}, लेकिन पूरा यक़ीन नहीं है.",
  "where_unknown": "मुझे अभी पक्का नहीं पता कि आप कहाँ हैं, {n}.",
  "no_scene": "जगह पहचानने की सुविधा अभी उपलब्ध नहीं है.",
  "ahead": "आपके सामने: {items}.",
  "ahead_none": "मुझे अभी आपके सामने कुछ नहीं दिख रहा.",
  "around": "आपके आसपास: {items}.",
  "around_none": "मुझे अभी आपके आसपास कुछ नहीं दिख रहा.",
  "people": "मुझे {num} लोग दिख रहे हैं.",
  "people_one": "मुझे एक व्यक्ति दिख रहा है.",
  "people_none": "मुझे अभी कोई नहीं दिख रहा.",
  "safe_obs": "सावधान रहिए {n}. {items}.",
  "safe_none": "मुझे आपके पास कुछ नहीं दिख रहा {n}, लेकिन मुझसे कुछ छूट सकता है. कृपया सावधानी से चलिए.",
  "paused": "ठीक है, मैं चुप रहूँगा. खतरा हुआ तो फिर भी बताऊँगा.",
  "resumed": "ठीक है {n}, मैं फिर से रास्ता बता रहा हूँ.",
  "lang_ok": "ठीक है, अब मैं हिंदी में बोलूँगा.",
  "hazard_found": "सावधान! {items}.",
  "hazard_none": "मुझे अभी सीढ़ियाँ या गड्ढा नहीं दिख रहा.",
  "hazard_nomodel": "मेरा सीढ़ियाँ और गड्ढा पहचानने वाला मॉडल इंस्टॉल नहीं है, इसलिए मैं उन्हें नहीं पहचान सकता. कृपया सावधान रहिए.",
  "help": "आप मुझसे दोस्त की तरह बात कर सकते हैं. पूछिए: मैं कहाँ हूँ, सामने क्या है, आसपास क्या है, कितने लोग हैं, रास्ता सुरक्षित है, समय क्या हुआ. कहिए: मुझे बाहर जाना है, फिर से बोलो, चुप, गाइड शुरू करो. मैं कुछ याद भी रख सकता हूँ: कहिए याद रखो, और फिर बताइए.",
  "unknown": "माफ़ कीजिए {n}, मैं समझ नहीं पाया. मदद बोलिए, मैं बताऊँगा कि मैं क्या कर सकता हूँ.",
  "no_camera": "मेरे कैमरे से अभी तस्वीर नहीं आ रही.",
  "repeat_none": "अभी दोहराने के लिए कुछ नहीं है.",
  "pos_set": "ठीक है {n}, मैं मान लेता हूँ कि आप {node} पर हैं.",
  "places_known": "मैं ये जगहें जानता हूँ: {places}.",
  "nav_no_places": "मैंने अभी कोई जगह नहीं सीखी है {n}. पहले किसी से कहिए कि मुझे आपका घर सिखाए.",
  "nav_unknown_target": "आप कहाँ जाना चाहते हैं {n}? मैं ये जानता हूँ: {places}.",
  "nav_not_localized": "मुझे अभी पक्का नहीं पता कि आप कहाँ हैं {n}. कृपया बताइए, जैसे: मैं {example} में हूँ.",
  "nav_start": "ठीक है {n}, चलिए {target} चलते हैं. मैं कदम-कदम पर बताऊँगा. पहले:",
  "nav_already": "आप तो पहले से {target} पर हैं {n}.",
  "nav_no_route": "मुझे {a} से {b} तक का रास्ता अभी नहीं पता. कृपया किसी से कहिए कि मुझे वह रास्ता सिखाए.",
  "nav_next": "बहुत अच्छे, आप {node} पहुँच गए. अब:",
  "nav_arrived": "हम {target} पहुँच गए {n}. शाबाश!",
  "nav_lost": "मुझे अभी पता नहीं चल रहा कि आप कहाँ हैं {n}. कृपया रुकिए और बताइए आप कहाँ हैं, या फिर से बोलो कहिए.",
  "nav_remind": "अभी भी {target} की ओर जा रहे हैं. यह कदम फिर से:",
  "nav_replan": "मैं देख रहा हूँ कि आप अब {node} पर हैं. यहाँ से रास्ता बताता हूँ:",
  "nav_cancel": "ठीक है, मैंने रास्ता बताना बंद कर दिया. मैं आपके साथ ही हूँ.",
  "nav_none_active": "मैं अभी आपको कहीं नहीं ले जा रहा.",
  "nav_generic": "{b} की ओर सावधानी से चलिए.",
  "teach_start": "ठीक है, मुझे जगह सिखाइए. यह कौन सी जगह है, जैसे घर या कॉलेज?",
  "teach_site_set": "ठीक है, {site}. अब किसी जगह पर खड़े होइए, कैमरा स्थिर रखिए, और कहिए: यह जगह याद रखो.",
  "teach_no_clip": "मैं जगहें नहीं सीख सकता क्योंकि मेरा तस्वीर वाला मॉडल उपलब्ध नहीं है.",
  "teach_no_camera": "मेरे कैमरे से तस्वीर नहीं आ रही. पहले कैमरा शुरू कीजिए.",
  "teach_ask_name": "इस जगह को मैं क्या नाम दूँ?",
  "teach_hold": "स्थिर रहिए, मैं तस्वीरें ले रहा हूँ.",
  "teach_saved": "{name} सेव हो गया. मैंने {k} तस्वीरें ली.",
  "teach_ask_instr": "{a} से {b} तक कैसे जाना है? अपने शब्दों में बताइए, या छोड़ो कहिए.",
  "teach_ask_rev": "और {b} से वापस {a} तक कैसे जाना है? या छोड़ो कहिए.",
  "teach_instr_saved": "समझ गया.",
  "teach_done": "ठीक है, सिखाना पूरा हुआ. मैं अब {num} जगहें जानता हूँ.",
  "teach_cancel": "ठीक है, रद्द किया.",
 },
 "mr": {
  "hello": "{tod} {n}! मी मित्र, तुमच्या सोबत आहे. सांगा, काय करायचे?",
  "how_are_you": "मी मस्त आहे {n}, विचारल्याबद्दल धन्यवाद! तुम्ही कसे आहात?",
  "thanks": ["काही नाही {n}, मित्र कशासाठी असतात!", "कधीही {n}! मी इथेच आहे."],
  "who_are_you": "मी मित्र, तुमचा मित्र आणि मार्गदर्शक. तुमच्या आजूबाजूला काय आहे, तुम्ही कुठे आहात ते सांगतो, धोक्याची सूचना देतो आणि शिकलेल्या जागांपर्यंत रस्ता दाखवतो.",
  "name_set": "तुम्हाला भेटून आनंद झाला {name}! मी तुमचे नाव लक्षात ठेवीन.",
  "name_known": "तुमचे नाव {name} आहे.",
  "name_unknown": "मला अजून तुमचे नाव माहीत नाही. म्हणा: माझे नाव, आणि मग तुमचे नाव.",
  "time": "वेळ आहे {time}, {n}.",
  "date": "आज {date} आहे, {n}.",
  "note_ask": "नक्कीच. मी काय लक्षात ठेवू?",
  "note_ok": "ठीक आहे {n}, मी लक्षात ठेवीन.",
  "notes_list": "तुम्ही मला सांगितले होते: {notes}.",
  "notes_none": "तुम्ही अजून मला काही लक्षात ठेवायला सांगितले नाही.",
  "notes_cleared": "ठीक आहे, मी तुमच्या नोंदी विसरलो.",
  "where_node": "तुम्ही {site} मध्ये {node} जवळ आहात, {n}.",
  "where_sure": "तुम्ही {place} मध्ये आहात, {n}.",
  "where_maybe": "मला वाटते तुम्ही {place} मध्ये आहात, {n}, पण मला पूर्ण खात्री नाही.",
  "where_unknown": "तुम्ही कुठे आहात हे मला आत्ता नक्की सांगता येत नाही, {n}.",
  "no_scene": "जागा ओळखण्याची सुविधा सध्या उपलब्ध नाही.",
  "ahead": "तुमच्या समोर: {items}.",
  "ahead_none": "मला आत्ता तुमच्या समोर काही दिसत नाही.",
  "around": "तुमच्या आजूबाजूला: {items}.",
  "around_none": "मला आत्ता तुमच्या आजूबाजूला काही दिसत नाही.",
  "people": "मला {num} लोक दिसत आहेत.",
  "people_one": "मला एक व्यक्ती दिसत आहे.",
  "people_none": "मला आत्ता कोणी दिसत नाही.",
  "safe_obs": "सावध रहा {n}. {items}.",
  "safe_none": "मला तुमच्या जवळ काही दिसत नाही {n}, पण माझ्याकडून काही चुकू शकते. कृपया सावधपणे चाला.",
  "paused": "ठीक आहे, मी शांत राहतो. धोका असेल तर तरी सांगेन.",
  "resumed": "ठीक आहे {n}, मी पुन्हा मार्गदर्शन करतो.",
  "lang_ok": "ठीक आहे, आता मी मराठीत बोलेन.",
  "hazard_found": "सावधान! {items}.",
  "hazard_none": "मला आत्ता पायऱ्या किंवा खड्डा दिसत नाही.",
  "hazard_nomodel": "माझे पायऱ्या आणि खड्डा ओळखणारे मॉडेल इन्स्टॉल केलेले नाही, म्हणून मी ते ओळखू शकत नाही. कृपया सावध रहा.",
  "help": "तुम्ही माझ्याशी मित्रासारखे बोलू शकता. विचारा: मी कुठे आहे, समोर काय आहे, आजूबाजूला काय आहे, किती लोक आहेत, रस्ता सुरक्षित आहे का, किती वाजले. म्हणा: मला बाहेर जायचं आहे, पुन्हा सांग, गप्प, गाइड सुरू कर. मी काही लक्षात पण ठेवू शकतो: म्हणा लक्षात ठेव, आणि मग सांगा.",
  "unknown": "माफ करा {n}, मला समजले नाही. मदत म्हणा, मी काय करू शकतो ते सांगतो.",
  "no_camera": "माझ्या कॅमेऱ्यातून सध्या चित्र येत नाही.",
  "repeat_none": "सध्या पुन्हा सांगण्यासारखे काही नाही.",
  "pos_set": "ठीक आहे {n}, तुम्ही {node} जवळ आहात असे मी धरतो.",
  "places_known": "मला या जागा माहीत आहेत: {places}.",
  "nav_no_places": "मी अजून कोणतीही जागा शिकलेली नाही {n}. आधी कोणाला तरी माझ्याकडून तुमचे घर शिकवायला सांगा.",
  "nav_unknown_target": "तुम्हाला कुठे जायचे आहे {n}? मला माहीत आहे: {places}.",
  "nav_not_localized": "तुम्ही कुठे आहात हे मला आत्ता नक्की माहीत नाही {n}. कृपया सांगा, उदाहरणार्थ: मी {example} मध्ये आहे.",
  "nav_start": "ठीक आहे {n}, चला {target} कडे जाऊया. मी पावला-पावलाने सांगतो. आधी:",
  "nav_already": "तुम्ही आधीच {target} जवळ आहात {n}.",
  "nav_no_route": "मला {a} पासून {b} पर्यंतचा रस्ता अजून माहीत नाही. कृपया कोणाला तरी तो रस्ता मला शिकवायला सांगा.",
  "nav_next": "छान, तुम्ही {node} ला पोहोचलात. आता:",
  "nav_arrived": "आपण {target} ला पोहोचलो {n}. शाब्बास!",
  "nav_lost": "तुम्ही कुठे आहात हे मला आत्ता कळत नाही {n}. कृपया थांबा आणि कुठे आहात ते सांगा, किंवा पुन्हा सांग म्हणा.",
  "nav_remind": "अजूनही {target} कडे जात आहोत. ही पायरी पुन्हा:",
  "nav_replan": "मला दिसते आहे की तुम्ही आता {node} जवळ आहात. इथून रस्ता सांगतो:",
  "nav_cancel": "ठीक आहे, मी रस्ता सांगणे थांबवले. मी तुमच्या सोबतच आहे.",
  "nav_none_active": "मी सध्या तुम्हाला कुठेही नेत नाही.",
  "nav_generic": "{b} कडे सावधपणे चाला.",
  "teach_start": "ठीक आहे, मला जागा शिकवा. ही कोणती जागा आहे, उदाहरणार्थ घर किंवा कॉलेज?",
  "teach_site_set": "ठीक आहे, {site}. आता एका जागी उभे राहा, कॅमेरा स्थिर धरा, आणि म्हणा: ही जागा लक्षात ठेव.",
  "teach_no_clip": "मी जागा शिकू शकत नाही कारण माझे चित्र ओळखणारे मॉडेल उपलब्ध नाही.",
  "teach_no_camera": "माझ्या कॅमेऱ्यातून चित्र येत नाही. आधी कॅमेरा सुरू करा.",
  "teach_ask_name": "या जागेला मी काय नाव देऊ?",
  "teach_hold": "स्थिर राहा, मी फोटो घेत आहे.",
  "teach_saved": "{name} सेव्ह झाले. मी {k} फोटो घेतले.",
  "teach_ask_instr": "{a} पासून {b} पर्यंत कसे जायचे? तुमच्या शब्दांत सांगा, किंवा सोडा म्हणा.",
  "teach_ask_rev": "आणि {b} पासून परत {a} ला कसे जायचे? किंवा सोडा म्हणा.",
  "teach_instr_saved": "समजले.",
  "teach_done": "ठीक आहे, शिकवणे पूर्ण झाले. मला आता {num} जागा माहीत आहेत.",
  "teach_cancel": "ठीक आहे, रद्द केले.",
 },
}
ALLOWED_FIELDS = {"n", "name", "tod", "time", "date", "place", "items", "notes", "node", "site", "target",
                  "a", "b", "k", "num", "places", "example"}


def time_text(lang, now):
    h12, m = now.hour % 12 or 12, now.minute
    if lang == "en":
        return "%d:%02d %s" % (h12, m, "AM" if now.hour < 12 else "PM")
    h = now.hour
    if lang == "hi":
        part = "सुबह" if 5 <= h < 12 else "दोपहर" if h < 16 else "शाम" if h < 20 else "रात"
        return "%s के %d बजे" % (part, h12) if m == 0 else "%s के %d बजकर %d मिनट" % (part, h12, m)
    part = "सकाळी" if 5 <= h < 12 else "दुपारी" if h < 16 else "संध्याकाळी" if h < 20 else "रात्री"
    return "%s %d वाजले" % (part, h12) if m == 0 else "%s %d वाजून %d मिनिटे" % (part, h12, m)


def date_text(lang, now):
    if lang == "en":
        return now.strftime("%A, %d %B %Y")
    return "%s, %d %s %d" % (WEEK[lang][now.weekday()], now.day, MONTH[lang][now.month - 1], now.year)


def extract_name(text):
    """'माझे नाव आकाश आहे' / 'my name is Akash' / 'call me Akash' -> Akash"""
    m = re.search(r"मला\s+(\S+)\s+म्हणा", text)
    if m:
        return m.group(1)
    low = text.lower()
    for mk in ("my name is", "call me", "मेरा नाम", "माझे नाव", "माझं नाव"):
        i = low.find(mk)
        if i >= 0:
            rest = text[i + len(mk):].strip(" .,!?")
            words = [w for w in rest.split() if w not in ("है", "आहे", "hai", "is", "हैं")]
            return " ".join(words[:2]).strip() or None
    return None


class Dialog:
    def __init__(self, p):
        self.p = p
        self.lock = threading.RLock()
        self.state = None          # None | ("site",) ("name",) ("instr",a,b) ("rev",b,a) ("note",)
        self.teaching = False
        self.site = "home"
        self.prev = None

    # ---------- helpers ----------
    def addr(self):
        return self.p.store.d.get("name") or FRIEND[self.p.lang]

    def _r(self, key, **kw):
        L = self.p.lang
        v = R[L][key]
        txt = random.choice(v) if isinstance(v, list) else v
        kw.setdefault("n", self.addr())
        return (txt.format(**kw), L)

    def _nname(self, nid):
        nd = self.p.navmap.nodes.get(nid)
        return nd["name"] if nd else ""

    def _instr(self, a, b):
        e = self.p.navmap.edge(a, b)
        if e and e.get("text"):
            return [(e["text"], e.get("lang") or self.p.lang)]
        return [self._r("nav_generic", b=self._nname(b))]

    def _speak(self, segs, priority=0):
        if segs:
            self.p.speaker.speak_segments(segs, priority)

    def greet(self):
        h = datetime.datetime.now().hour
        i = 0 if h < 12 else 1 if h < 16 else 2 if h < 20 else 3
        tod = GREET[self.p.lang].format(TOD[self.p.lang][i])
        self._speak([self._r("hello", tod=tod)])

    # ---------- main entry ----------
    def handle(self, text, from_voice=True):
        with self.lock:
            t = (text or "").strip()
            if not t:
                return []
            if self.state:
                segs = self._state_step(t)
            else:
                intent = match_intent(t)
                if intent is None and self.p.navmap.match(t) and any(m in t.lower() for m in AT_MARKERS):
                    intent = "i_am_at"
                if intent is None:
                    if from_voice and not MITRA_RE.search(t.lower()):
                        return []                      # command nahi -> durlaksh
                    segs = [self._r("unknown")]
                else:
                    segs = self._route(intent, t)
            self._speak(segs)
            return segs or []

    # ---------- intents ----------
    def _route(self, intent, t):
        p, nm = self.p, self.p.navmap
        if intent in ("lang_en", "lang_hi", "lang_mr"):
            p.set_language(intent[-2:])
            p.store.set("lang", intent[-2:])
            return [self._r("lang_ok")]
        if intent == "help":
            return [self._r("help")]
        if intent == "pause":
            p.guide_enabled = False
            return [self._r("paused")]
        if intent == "resume":
            p.guide_enabled = True
            return [self._r("resumed")]
        if intent == "repeat":
            return p.speaker.last_segments or [self._r("repeat_none")]
        if intent == "greet":
            h = datetime.datetime.now().hour
            i = 0 if h < 12 else 1 if h < 16 else 2 if h < 20 else 3
            return [self._r("hello", tod=GREET[p.lang].format(TOD[p.lang][i]))]
        if intent == "how_are_you":
            return [self._r("how_are_you")]
        if intent == "thanks":
            return [self._r("thanks")]
        if intent == "who":
            return [self._r("who_are_you")]
        if intent == "time":
            return [self._r("time", time=time_text(p.lang, datetime.datetime.now()))]
        if intent == "date":
            return [self._r("date", date=date_text(p.lang, datetime.datetime.now()))]
        if intent == "set_name":
            name = extract_name(t)
            if not name:
                return [self._r("name_unknown")]
            p.store.set("name", name)
            return [self._r("name_set", name=name)]
        if intent == "ask_name":
            nm_ = p.store.d.get("name")
            return [self._r("name_known", name=nm_)] if nm_ else [self._r("name_unknown")]
        if intent == "remember":
            rest = t
            for mk in INTENTS["remember"]:
                i = t.lower().find(mk)
                if i >= 0:
                    rest = t[i + len(mk):]
                    break
            rest = rest.strip(" .,!?")
            if len(rest) < 2:
                self.state = ("note",)
                return [self._r("note_ask")]
            p.store.add_note(rest)
            return [self._r("note_ok")]
        if intent == "recall":
            notes = p.store.d.get("notes", [])
            if not notes:
                return [self._r("notes_none")]
            return [self._r("notes_list", notes=". ".join(x["text"] for x in notes[-5:]))]
        if intent == "forget":
            p.store.clear_notes()
            return [self._r("notes_cleared")]
        if intent == "places":
            return [self._r("places_known", places=", ".join(nm.names()))] if nm.nodes else [self._r("nav_no_places")]
        if intent == "where":
            return self._where()
        if intent == "i_am_at":
            ids = nm.match(t)
            p.set_manual_node(ids[0])
            return [self._r("pos_set", node=self._nname(ids[0]))]
        # ---- teaching ----
        if intent == "teach_start":
            self.state = ("site",)
            return [self._r("teach_start")]
        if intent == "teach_stop":
            self.teaching, self.prev, self.state = False, None, None
            return [self._r("teach_done", num=len(nm.nodes))]
        if intent == "save_place":
            if p.scene is None:
                return [self._r("teach_no_clip")]
            if p.raw_frame is None:
                return [self._r("teach_no_camera")]
            self.state = ("name",)
            return [self._r("teach_ask_name")]
        # ---- navigation ----
        if intent == "navigate":
            return self._navigate(t)
        if intent == "nav_cancel":
            if not p.navigator.active:
                return [self._r("nav_none_active")]
            p.navigator.cancel()
            return [self._r("nav_cancel")]
        if intent == "next_step":
            if not p.navigator.active:
                return [self._r("nav_none_active")]
            ev = p.navigator.manual_next()
            self.announce(ev)
            return []
        # ---- camera based ----
        res = p.recent_results(1.5)
        if not res:
            return [self._r("no_camera")]
        eng = p.engine
        if intent == "people":
            n = eng.count_people(res)
            return [self._r("people_none" if n == 0 else "people_one" if n == 1 else "people", num=n)]
        if intent == "ahead":
            items = eng.describe(res, front_only=True)
            return [self._r("ahead", items=", ".join(items))] if items else [self._r("ahead_none")]
        if intent == "around":
            items = eng.describe(res)
            return [self._r("around", items=", ".join(items))] if items else [self._r("around_none")]
        if intent == "safe":
            items = eng.describe(res, max_level=1)
            return [self._r("safe_obs", items=", ".join(items))] if items else [self._r("safe_none")]
        if intent == "hazard":
            if p.robin.hazard is None:
                return [self._r("hazard_nomodel")]
            items = eng.describe(res, only_danger=True)
            return [self._r("hazard_found", items=", ".join(items))] if items else [self._r("hazard_none")]
        return [self._r("unknown")]

    def _where(self):
        p = self.p
        nid = p.current_node()
        if nid:
            nd = p.navmap.nodes[nid]
            return [self._r("where_node", node=nd["name"], site=nd["site"])]
        if p.scene is None:
            return [self._r("no_scene")]
        if not p.place:
            return [self._r("where_unknown")]
        name = PLACES[p.place]["name"][p.lang]
        return [self._r("where_sure" if p.place_conf >= 0.6 else "where_maybe", place=name)]

    def _navigate(self, t):
        p, nm = self.p, self.p.navmap
        if not nm.nodes:
            return [self._r("nav_no_places")]
        targets = nm.match(t)
        if not targets:
            return [self._r("nav_unknown_target", places=", ".join(nm.names()))]
        cur = p.current_node()
        if cur is None:
            return [self._r("nav_not_localized", example=nm.names()[0])]
        others = [x for x in targets if x != cur]
        if not others:
            return [self._r("nav_already", target=self._nname(cur))]
        best = None
        for x in others:
            r = nm.route(cur, x)
            if r and (best is None or len(r) < len(best[1])):
                best = (x, r)
        if best is None:
            return [self._r("nav_no_route", a=self._nname(cur), b=self._nname(others[0]))]
        p.navigator.start(cur, best[0])
        r = best[1]
        return [self._r("nav_start", target=self._nname(best[0]))] + self._instr(r[0], r[1])

    # ---------- navigator events -> speech ----------
    def announce(self, ev):
        if not ev:
            return
        kind, data = ev
        nav = self.p.navigator
        if kind == "arrived":
            segs = [self._r("nav_arrived", target=self._nname(nav.target))]
        elif kind == "lost":
            segs = [self._r("nav_lost")]
        else:
            intro = {"reached": lambda: self._r("nav_next", node=self._nname(data)),
                     "replan": lambda: self._r("nav_replan", node=self._nname(data)),
                     "remind": lambda: self._r("nav_remind", target=self._nname(nav.target))}[kind]()
            segs = [intro] + self._instr(nav.route[nav.i], nav.route[nav.i + 1])
        self._speak(segs, 1.5)

    # ---------- teach flows ----------
    def _state_step(self, t):
        p, nm = self.p, self.p.navmap
        st, low = self.state, norm(t).strip(" .!?,")
        if low in CANCEL:
            self.state = None
            return [self._r("teach_cancel")]
        if st[0] == "site":
            self.site, self.teaching, self.prev, self.state = t.strip(" .!?,"), True, None, None
            return [self._r("teach_site_set", site=self.site)]
        if st[0] == "note":
            p.store.add_note(t.strip())
            self.state = None
            return [self._r("note_ok")]
        if st[0] == "name":
            name = t.strip(" .!?,")
            self._speak([self._r("teach_hold")])
            try:
                nid, k = p.capture_waypoint(name, self.site)
            except RuntimeError as e:
                self.state = None
                return [self._r("teach_no_clip" if str(e) == "no_clip" else "teach_no_camera")]
            self.teaching, prev, self.prev = True, self.prev, nid
            segs = [self._r("teach_saved", name=name, k=k)]
            if prev and prev != nid:
                self.state = ("instr", prev, nid)
                segs.append(self._r("teach_ask_instr", a=self._nname(prev), b=self._nname(nid)))
            else:
                self.state = None
            return segs
        if st[0] in ("instr", "rev"):
            a, b = st[1], st[2]
            if low in SKIP:
                self.state = None
                return [self._r("teach_instr_saved")]
            nm.set_edge(a, b, t.strip(), lang=p.lang)
            if st[0] == "instr":
                self.state = ("rev", b, a)
                return [self._r("teach_instr_saved"),
                        self._r("teach_ask_rev", a=self._nname(a), b=self._nname(b))]
            self.state = None
            return [self._r("teach_instr_saved")]
        self.state = None
        return []
