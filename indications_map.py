"""
Category tag -> plain-language clinical indication.

An indication answers "what is this herb used FOR", which is a different
question from tcm_functions ("what does it DO"). The formulator needs both:
the action justifies the choice, the indication matches it to the presenting
complaint.

Composed from the existing category tags rather than written per herb, so the
indication text is always consistent with the tags the shortlist filter uses.
If a herb is tagged, its indication says so; there is no third source of truth
to drift out of sync.
"""

INDICATION = {
    # patterns / constitution
    "qi_tonic": "Qi deficiency", "yang_tonic": "Yang deficiency",
    "yin_tonic": "Yin deficiency", "blood_tonic": "Blood deficiency",
    "essence": "Essence (Jing) depletion", "jing": "Essence (Jing) depletion",
    "heat": "Heat patterns", "cold": "Cold patterns",
    "damp": "Damp accumulation", "damp_heat": "Damp-Heat",
    "phlegm": "Phlegm accumulation", "toxin": "toxic Heat / sores",
    "wind": "internal Wind", "wind_cold": "Wind-Cold invasion",
    "wind_heat": "Wind-Heat invasion", "wind_damp": "Wind-Damp obstruction",
    "exterior": "exterior patterns", "summerheat": "summerheat",
    "blood_stasis": "Blood stasis", "blood_move": "Blood stasis",
    "qi_stagnation": "Qi stagnation", "qi_move": "Qi stagnation",
    "liver_qi": "Liver Qi constraint", "liver_yang": "Liver Yang rising",
    # organs / systems
    "heart": "Heart patterns", "liver": "Liver patterns",
    "spleen": "Spleen patterns", "lung": "Lung patterns",
    "kidney": "Kidney patterns", "stomach": "Stomach patterns",
    "gut": "intestinal complaints", "gallbladder": "Gallbladder complaints",
    "uterus": "uterine complaints", "shen": "Shen disturbance",
    # presenting complaints
    "sleep": "poor sleep", "insomnia": "insomnia", "anxiety": "anxiety",
    "stress": "stress", "depression": "low mood", "mood": "low mood",
    "irritability": "irritability", "fatigue": "fatigue",
    "memory": "poor memory", "brain": "cognitive complaints",
    "dizziness": "dizziness", "headache": "headache", "head": "head symptoms",
    "cough": "cough", "asthma": "wheezing and asthma", "throat": "sore throat",
    "voice": "hoarseness", "sinus": "sinus congestion", "nasal": "nasal congestion",
    "allergy": "allergic symptoms", "fever": "fever", "infection": "infection",
    "antiviral": "viral illness", "immune": "low immunity",
    "digestion": "poor digestion", "appetite": "poor appetite",
    "bloating": "bloating and distension", "nausea": "nausea and vomiting",
    "diarrhoea": "diarrhoea", "dysentery": "dysentery",
    "constipation": "constipation", "haemorrhoid": "haemorrhoids",
    "gastric_acid": "acid reflux", "gastric": "gastric complaints",
    "hangover": "alcohol excess", "parasite": "intestinal parasites",
    "urinary": "urinary difficulty", "stone": "urinary or biliary stones",
    "oedema": "oedema", "enuresis": "bedwetting and incontinence",
    "turbid_urine": "turbid urine", "discharge": "abnormal discharge",
    "menstrual": "menstrual disorders", "women": "women's health",
    "menopause": "menopausal symptoms", "postpartum": "postpartum recovery",
    "lactation": "insufficient lactation", "fertility": "fertility support",
    "pregnancy": "pregnancy support", "men": "men's health",
    "paediatric": "paediatric use", "children": "paediatric use",
    "aging": "age-related decline", "bone": "bone weakness",
    "joint": "joint pain", "arthritis": "arthritic pain",
    "back_pain": "lower back pain", "back": "back pain", "leg": "leg weakness",
    "shoulder": "shoulder pain", "neck": "neck stiffness",
    "sinew": "sinew stiffness", "cramp": "muscle cramp", "spasm": "spasm",
    "collateral": "channel obstruction", "pain": "pain",
    "trauma": "traumatic injury", "fracture": "fracture", "wound": "wounds",
    "burn": "burns", "skin": "skin conditions", "itch": "itching",
    "rash": "rashes", "tinea": "fungal skin infection", "hair": "hair loss",
    "eye": "eye complaints", "eyes": "eye complaints", "ears": "ear complaints",
    "toothache": "toothache", "facial_palsy": "facial paralysis",
    "stroke": "stroke sequelae", "spleen_prolapse": "prolapse",
    "prolapse": "organ prolapse", "bleeding": "bleeding",
    "sweating": "abnormal sweating", "thirst": "thirst and dryness",
    "dryness": "dryness", "chest": "chest oppression",
    "hypertension": "raised blood pressure", "blood_pressure": "blood pressure",
    "cholesterol": "raised lipids", "blood_sugar": "blood sugar regulation",
    "circulation": "poor circulation", "weight": "weight management",
    "nodule": "nodules and lumps", "thyroid": "thyroid nodules",
    "lymph": "lymphatic swelling", "abscess": "abscess", "swelling": "swelling",
    "abdominal_mass": "abdominal masses", "jaundice": "jaundice",
    "malaria": "malarial disorders", "tuberculosis": "consumptive cough",
    "snakebite": "snakebite", "oncology_support": "oncology support",
    "inflammation": "inflammation", "detox": "detoxification",
    "antioxidant": "antioxidant support", "hernia": "hernia pain",
    "breast": "breast complaints", "collapse": "Yang collapse",
    # functional / non-clinical tags — no indication text
    "astringent": None, "harmonise": None, "flavour": None,
    "blood_cooling": None,
}


def indications_for(categories) -> str:
    """Compose the indication string for one herb from its category tags."""
    seen, out = set(), []
    for c in categories:
        text = INDICATION.get(c)
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return "; ".join(out)
