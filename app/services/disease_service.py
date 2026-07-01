WHEAT_DISEASE_ADVISORY = {
    "crop": "wheat",
    "season": "pre-season",
    "source": "static",
    "diseases": [
        {
            "name": "Leaf blight",
            "risk_level": "moderate",
            "advisory_bn": "বীজ বপনের আগে certified seed ব্যবহার করুন এবং ক্ষেতে জমা পানি রাখবেন না।",
        },
        {
            "name": "Rust",
            "risk_level": "high",
            "advisory_bn": "আগাম সতর্কতা: রোগ-resistant জাত বপন করুন এবং প্রয়োজনে কৃষি কর্মকর্তার পরামর্শ নিন।",
        },
        {
            "name": "Smut",
            "risk_level": "low",
            "advisory_bn": "বীজ treatment করুন এবং আক্রান্ত গাছ পুড়িয়ে ফেলুন।",
        },
    ],
    "general_advisory_bn": (
        "গম চাষের preseason পরামর্শ: পরিষ্কার জমি, সময়মতো বপন, "
        "সbalanced সার প্রয়োগ এবং Agvisely-এর স্থানীয় রোগ পূর্বাভাস অনুসরণ করুন।"
    ),
}


def get_wheat_disease_advisory() -> dict:
    return WHEAT_DISEASE_ADVISORY
