import re

CATEGORY_RULES: list[tuple[str, list[str]]] = [
    ("food", ["swiggy", "zomato", "dominos", "mcdonald", "kfc", "restaurant", "cafe", "food"]),
    ("transport", ["uber", "ola", "rapido", "irctc", "metro", "petrol", "fuel", "fastag"]),
    ("shopping", ["amazon", "flipkart", "myntra", "ajio", "meesho", "nykaa"]),
    ("groceries", ["bigbasket", "blinkit", "zepto", "dmart", "grocery", "instamart"]),
    ("bills", ["electricity", "bescom", "airtel", "jio", "vi ", "broadband", "rent"]),
    ("entertainment", ["netflix", "spotify", "prime video", "hotstar", "bookmyshow"]),
    ("health", ["pharmacy", "apollo", "medplus", "hospital", "practo"]),
    ("transfer", ["neft", "imps", "rtgs", "upi/", "self transfer", "salary"]),
    ("investment", ["zerodha", "groww", "mutual fund", "sip", "cdsl", "nsdl"]),
]


def categorize(description: str) -> str:
    text = description.lower()
    for category, keywords in CATEGORY_RULES:
        for kw in keywords:
            if kw in text:
                return category
    if re.search(r"upi/(dr|debit)", text):
        return "transfer"
    return "other"
