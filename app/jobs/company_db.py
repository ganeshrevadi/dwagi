from app.jobs.config import get_job_settings

COMPANIES: list[dict] = [
    # FAANG + Big Tech
    {"name": "Google", "domain": "google.com", "employees": 190000, "board_type": "google"},
    {"name": "Meta", "domain": "meta.com", "employees": 87000, "board_type": "meta"},
    {"name": "Apple", "domain": "apple.com", "employees": 164000, "board_type": "apple"},
    {"name": "Amazon", "domain": "amazon.com", "employees": 1540000, "board_type": "amazon"},
    {"name": "Microsoft", "domain": "microsoft.com", "employees": 221000, "board_type": "microsoft"},
    {"name": "Netflix", "domain": "netflix.com", "employees": 12800, "board_type": "netflix"},
    {"name": "NVIDIA", "domain": "nvidia.com", "employees": 26000, "board_type": "nvidia"},

    # Cloud / Infrastructure
    {"name": "Cloudflare", "domain": "cloudflare.com", "employees": 3800, "board_type": "greenhouse"},
    {"name": "Datadog", "domain": "datadoghq.com", "employees": 4800, "board_type": "greenhouse"},
    {"name": "Databricks", "domain": "databricks.com", "employees": 7000, "board_type": "greenhouse"},
    {"name": "Snowflake", "domain": "snowflake.com", "employees": 6200, "board_type": ""},
    {"name": "Confluent", "domain": "confluent.io", "employees": 4500, "board_type": ""},
    {"name": "HashiCorp", "domain": "hashicorp.com", "employees": 2800, "board_type": ""},
    {"name": "Elastic", "domain": "elastic.co", "employees": 3500, "board_type": "greenhouse"},
    {"name": "MongoDB", "domain": "mongodb.com", "employees": 5000, "board_type": "greenhouse"},
    {"name": "Redis", "domain": "redis.com", "employees": 900, "board_type": ""},
    {"name": "DigitalOcean", "domain": "digitalocean.com", "employees": 1300, "board_type": ""},
    {"name": "Fastly", "domain": "fastly.com", "employees": 900, "board_type": "greenhouse"},
    {"name": "GitLab", "domain": "gitlab.com", "employees": 2200, "board_type": "greenhouse"},
    {"name": "Netlify", "domain": "netlify.com", "employees": 600, "board_type": "greenhouse"},
    {"name": "Vercel", "domain": "vercel.com", "employees": 500, "board_type": "greenhouse"},

    # SaaS / Enterprise
    {"name": "Stripe", "domain": "stripe.com", "employees": 12000, "board_type": "stripe"},
    {"name": "Square", "domain": "squareup.com", "employees": 12000, "board_type": ""},
    {"name": "Shopify", "domain": "shopify.com", "employees": 16000, "board_type": "lever"},
    {"name": "Notion", "domain": "notion.so", "employees": 1500, "board_type": ""},
    {"name": "Figma", "domain": "figma.com", "employees": 1300, "board_type": "greenhouse"},
    {"name": "Canva", "domain": "canva.com", "employees": 4000, "board_type": ""},
    {"name": "Atlassian", "domain": "atlassian.com", "employees": 11000, "board_type": ""},
    {"name": "Salesforce", "domain": "salesforce.com", "employees": 73000, "board_type": "salesforce"},
    {"name": "Workday", "domain": "workday.com", "employees": 18800, "board_type": "workday"},
    {"name": "ServiceNow", "domain": "servicenow.com", "employees": 22000, "board_type": "servicenow"},
    {"name": "Adobe", "domain": "adobe.com", "employees": 29000, "board_type": "adobe"},
    {"name": "Oracle", "domain": "oracle.com", "employees": 143000, "board_type": "oracle"},
    {"name": "SAP", "domain": "sap.com", "employees": 107000, "board_type": "sap"},
    {"name": "Twilio", "domain": "twilio.com", "employees": 7900, "board_type": "greenhouse"},
    {"name": "SendGrid", "domain": "sendgrid.com", "employees": 900, "board_type": ""},
    {"name": "HubSpot", "domain": "hubspot.com", "employees": 7800, "board_type": "greenhouse"},
    {"name": "Zendesk", "domain": "zendesk.com", "employees": 6000, "board_type": ""},
    {"name": "Intercom", "domain": "intercom.com", "employees": 1200, "board_type": "greenhouse"},
    {"name": "Dropbox", "domain": "dropbox.com", "employees": 3100, "board_type": "greenhouse"},
    {"name": "Box", "domain": "box.com", "employees": 2500, "board_type": ""},
    {"name": "Asana", "domain": "asana.com", "employees": 1800, "board_type": "lever"},
    {"name": "Monday.com", "domain": "monday.com", "employees": 2000, "board_type": ""},
    {"name": "Airtable", "domain": "airtable.com", "employees": 1200, "board_type": "greenhouse"},
    {"name": "Coda", "domain": "coda.io", "employees": 300, "board_type": ""},
    {"name": "ClickUp", "domain": "clickup.com", "employees": 900, "board_type": ""},

    # Fintech
    {"name": "Chime", "domain": "chime.com", "employees": 1600, "board_type": "greenhouse"},
    {"name": "Plaid", "domain": "plaid.com", "employees": 1200, "board_type": ""},
    {"name": "Brex", "domain": "brex.com", "employees": 1200, "board_type": "greenhouse"},
    {"name": "Ramp", "domain": "ramp.com", "employees": 1100, "board_type": ""},
    {"name": "Deel", "domain": "deel.com", "employees": 3000, "board_type": ""},
    {"name": "Revolut", "domain": "revolut.com", "employees": 9000, "board_type": ""},
    {"name": "Wise", "domain": "wise.com", "employees": 5000, "board_type": ""},
    {"name": "PayPal", "domain": "paypal.com", "employees": 30000, "board_type": "paypal"},
    {"name": "Block", "domain": "block.xyz", "employees": 12000, "board_type": "greenhouse"},
    {"name": "Robinhood", "domain": "robinhood.com", "employees": 3800, "board_type": "greenhouse"},
    {"name": "Coinbase", "domain": "coinbase.com", "employees": 5000, "board_type": "greenhouse"},
    {"name": "Kraken", "domain": "kraken.com", "employees": 3000, "board_type": ""},
    {"name": "Gemini", "domain": "gemini.com", "employees": 1000, "board_type": "greenhouse"},
    {"name": "OpenSea", "domain": "opensea.io", "employees": 500, "board_type": ""},

    # E-commerce / Marketplace
    {"name": "Airbnb", "domain": "airbnb.com", "employees": 6800, "board_type": "greenhouse"},
    {"name": "Uber", "domain": "uber.com", "employees": 33000, "board_type": "lever"},
    {"name": "Lyft", "domain": "lyft.com", "employees": 4500, "board_type": "greenhouse"},
    {"name": "DoorDash", "domain": "doordash.com", "employees": 20000, "board_type": ""},
    {"name": "Instacart", "domain": "instacart.com", "employees": 3000, "board_type": "greenhouse"},
    {"name": "Pinterest", "domain": "pinterest.com", "employees": 4000, "board_type": "greenhouse"},
    {"name": "Snap", "domain": "snap.com", "employees": 6000, "board_type": ""},
    {"name": "Reddit", "domain": "redditinc.com", "employees": 2000, "board_type": "greenhouse"},
    {"name": "Spotify", "domain": "spotify.com", "employees": 9000, "board_type": ""},
    {"name": "Discord", "domain": "discord.com", "employees": 1500, "board_type": "greenhouse"},
    {"name": "Slack", "domain": "slack.com", "employees": 3000, "board_type": ""},
    {"name": "Zoom", "domain": "zoom.us", "employees": 7500, "board_type": ""},
    {"name": "Etsy", "domain": "etsy.com", "employees": 2500, "board_type": ""},
    {"name": "Wayfair", "domain": "wayfair.com", "employees": 16000, "board_type": "wayfair"},
    {"name": "Zillow", "domain": "zillow.com", "employees": 6000, "board_type": ""},
    {"name": "Roku", "domain": "roku.com", "employees": 3600, "board_type": "greenhouse"},

    # Consulting / Agencies
    {"name": "McKinsey", "domain": "mckinsey.com", "employees": 45000, "board_type": "mckinsey"},
    {"name": "BCG", "domain": "bcg.com", "employees": 32000, "board_type": "bcg"},
    {"name": "Bain", "domain": "bain.com", "employees": 18000, "board_type": "bain"},
    {"name": "Accenture", "domain": "accenture.com", "employees": 750000, "board_type": "accenture"},
    {"name": "Deloitte", "domain": "deloitte.com", "employees": 450000, "board_type": "deloitte"},
    {"name": "PwC", "domain": "pwc.com", "employees": 370000, "board_type": "pwc"},
    {"name": "EY", "domain": "ey.com", "employees": 400000, "board_type": "ey"},
    {"name": "KPMG", "domain": "kpmg.com", "employees": 275000, "board_type": "kpmg"},

    # AI / ML
    {"name": "OpenAI", "domain": "openai.com", "employees": 4000, "board_type": "openai"},
    {"name": "Anthropic", "domain": "anthropic.com", "employees": 1500, "board_type": "greenhouse"},
    {"name": "Scale AI", "domain": "scale.com", "employees": 1500, "board_type": ""},
    {"name": "Cohere", "domain": "cohere.com", "employees": 500, "board_type": ""},
    {"name": "Hugging Face", "domain": "huggingface.co", "employees": 600, "board_type": ""},
    {"name": "Replicate", "domain": "replicate.com", "employees": 50, "board_type": ""},

    # Gaming
    {"name": "Epic Games", "domain": "epicgames.com", "employees": 4500, "board_type": ""},
    {"name": "Roblox", "domain": "roblox.com", "employees": 5500, "board_type": "greenhouse"},
    {"name": "Unity", "domain": "unity.com", "employees": 7000, "board_type": ""},
    {"name": "Riot Games", "domain": "riotgames.com", "employees": 4500, "board_type": ""},
    {"name": "Blizzard", "domain": "blizzard.com", "employees": 13000, "board_type": "blizzard"},
    {"name": "Electronic Arts", "domain": "ea.com", "employees": 13000, "board_type": "ea"},

    # Remote-first
    {"name": "Automattic", "domain": "automattic.com", "employees": 2000, "board_type": "automattic"},
    {"name": "Zapier", "domain": "zapier.com", "employees": 700, "board_type": ""},
    {"name": "Toggl", "domain": "toggl.com", "employees": 100, "board_type": "toggl"},
    {"name": "Buffer", "domain": "buffer.com", "employees": 100, "board_type": "buffer"},
    {"name": "Doist", "domain": "doist.com", "employees": 100, "board_type": "doist"},
    {"name": "Basecamp", "domain": "basecamp.com", "employees": 100, "board_type": "basecamp"},
    {"name": "37signals", "domain": "37signals.com", "employees": 100, "board_type": "37signals"},

    # Social / Media
    {"name": "TikTok", "domain": "tiktok.com", "employees": 150000, "board_type": "bytedance"},
    {"name": "ByteDance", "domain": "bytedance.com", "employees": 150000, "board_type": "bytedance"},
    {"name": "Twitter", "domain": "twitter.com", "employees": 1500, "board_type": "twitter"},
    {"name": "LinkedIn", "domain": "linkedin.com", "employees": 20000, "board_type": "linkedin"},
    {"name": "Medium", "domain": "medium.com", "employees": 500, "board_type": "greenhouse"},
    {"name": "Substack", "domain": "substack.com", "employees": 100, "board_type": ""},
    {"name": "NewsCorp", "domain": "newscorp.com", "employees": 24000, "board_type": "newscorp"},
    {"name": "The New York Times", "domain": "nytimes.com", "employees": 5000, "board_type": "nytimes"},

    # Hardware / Semiconductor
    {"name": "AMD", "domain": "amd.com", "employees": 26000, "board_type": "amd"},
    {"name": "Intel", "domain": "intel.com", "employees": 125000, "board_type": "intel"},
    {"name": "Qualcomm", "domain": "qualcomm.com", "employees": 50000, "board_type": "qualcomm"},
    {"name": "ARM", "domain": "arm.com", "employees": 7000, "board_type": "arm"},
    {"name": "TSMC", "domain": "tsmc.com", "employees": 77000, "board_type": "tsmc"},
    {"name": "ASML", "domain": "asml.com", "employees": 42000, "board_type": "asml"},
    {"name": "HP", "domain": "hp.com", "employees": 58000, "board_type": "hp"},
    {"name": "Dell", "domain": "dell.com", "employees": 133000, "board_type": "dell"},
    {"name": "IBM", "domain": "ibm.com", "employees": 288000, "board_type": "ibm"},
    {"name": "Cisco", "domain": "cisco.com", "employees": 85000, "board_type": "cisco"},
    {"name": "Tesla", "domain": "tesla.com", "employees": 140000, "board_type": "tesla"},
    {"name": "SpaceX", "domain": "spacex.com", "employees": 13000, "board_type": "spacex"},

    # Security
    {"name": "CrowdStrike", "domain": "crowdstrike.com", "employees": 10000, "board_type": ""},
    {"name": "Palo Alto Networks", "domain": "paloaltonetworks.com", "employees": 15000, "board_type": "paloaltonetworks"},
    {"name": "Okta", "domain": "okta.com", "employees": 6000, "board_type": "greenhouse"},
    {"name": "1Password", "domain": "1password.com", "employees": 1000, "board_type": ""},
    {"name": "Snyk", "domain": "snyk.io", "employees": 1200, "board_type": ""},
    {"name": "Wiz", "domain": "wiz.io", "employees": 2000, "board_type": ""},
    {"name": "Lacework", "domain": "lacework.com", "employees": 1000, "board_type": ""},

    # Telecom
    {"name": "Verizon", "domain": "verizon.com", "employees": 118000, "board_type": "verizon"},
    {"name": "AT&T", "domain": "att.com", "employees": 230000, "board_type": "att"},
    {"name": "T-Mobile", "domain": "t-mobile.com", "employees": 75000, "board_type": "tmobile"},
    {"name": "Comcast", "domain": "comcast.com", "employees": 190000, "board_type": "comcast"},

    # GCCs in India (retained for scoring via Google/LinkedIn scrapers)
    {"name": "Walmart Global Tech", "domain": "walmart.com", "employees": 2100000, "board_type": ""},
    {"name": "Goldman Sachs", "domain": "goldmansachs.com", "employees": 49000, "board_type": ""},
    {"name": "JPMorgan Chase", "domain": "jpmorganchase.com", "employees": 310000, "board_type": ""},
    {"name": "Morgan Stanley", "domain": "morganstanley.com", "employees": 82000, "board_type": ""},
    {"name": "American Express", "domain": "americanexpress.com", "employees": 77000, "board_type": ""},
    {"name": "Capital One", "domain": "capitalone.com", "employees": 55000, "board_type": ""},
    {"name": "Citi", "domain": "citi.com", "employees": 240000, "board_type": ""},
    {"name": "Barclays", "domain": "barclays.com", "employees": 81000, "board_type": ""},
    {"name": "Visa", "domain": "visa.com", "employees": 30000, "board_type": ""},
    {"name": "Mastercard", "domain": "mastercard.com", "employees": 33000, "board_type": ""},
    {"name": "Fidelity Investments", "domain": "fidelity.com", "employees": 74000, "board_type": ""},
    {"name": "UBS", "domain": "ubs.com", "employees": 74000, "board_type": ""},

    # Indian tech unicorns (confirmed Greenhouse)
    {"name": "Groww", "domain": "groww.in", "employees": 1500, "board_type": "greenhouse"},
    {"name": "PhonePe", "domain": "phonepe.com", "employees": 5000, "board_type": "greenhouse"},
    {"name": "Postman", "domain": "postman.com", "employees": 1200, "board_type": "greenhouse"},

    # Indian tech unicorns (for scoring — not on Greenhouse)
    {"name": "Flipkart", "domain": "flipkart.com", "employees": 55000, "board_type": ""},
    {"name": "Swiggy", "domain": "swiggy.com", "employees": 6000, "board_type": ""},
    {"name": "Zomato", "domain": "zomato.com", "employees": 5000, "board_type": ""},
    {"name": "Razorpay", "domain": "razorpay.com", "employees": 3000, "board_type": ""},
    {"name": "CRED", "domain": "cred.club", "employees": 1500, "board_type": ""},
    {"name": "Zerodha", "domain": "zerodha.com", "employees": 1500, "board_type": ""},
    {"name": "Nykaa", "domain": "nykaa.com", "employees": 3500, "board_type": ""},
    {"name": "Meesho", "domain": "meesho.com", "employees": 3000, "board_type": ""},
    {"name": "Delhivery", "domain": "delhivery.com", "employees": 35000, "board_type": ""},
    {"name": "Paytm", "domain": "paytm.com", "employees": 30000, "board_type": ""},
    {"name": "Zoho", "domain": "zoho.com", "employees": 15000, "board_type": ""},
    {"name": "Freshworks", "domain": "freshworks.com", "employees": 6000, "board_type": ""},
    {"name": "BrowserStack", "domain": "browserstack.com", "employees": 1000, "board_type": ""},

    # Global unicorns (confirmed Greenhouse)
    {"name": "Webflow", "domain": "webflow.com", "employees": 800, "board_type": "greenhouse"},

    # Ashby ATS companies (open JSON API)
    {"name": "Linear", "domain": "linear.app", "employees": 200, "board_type": "ashby"},
    {"name": "Supabase", "domain": "supabase.com", "employees": 300, "board_type": "ashby"},
    {"name": "PostHog", "domain": "posthog.com", "employees": 200, "board_type": "ashby"},
    {"name": "Warp", "domain": "warp.dev", "employees": 100, "board_type": "ashby"},
    {"name": "Ashby", "domain": "ashbyhq.com", "employees": 200, "board_type": "ashby"},

    # Global unicorns (for scoring — not on Greenhouse)
    {"name": "Rippling", "domain": "rippling.com", "employees": 3000, "board_type": ""},
]

_settings = get_job_settings()
_COMPANY_CACHE: dict[str, dict] | None = None


def get_company_list() -> list[dict]:
    global _COMPANY_CACHE
    if _COMPANY_CACHE is not None:
        return list(_COMPANY_CACHE.values())

    min_emp = _settings.company_min_employees
    name_index: dict[str, dict] = {}

    for c in COMPANIES:
        if c["employees"] >= min_emp:
            name_index[c["name"].lower()] = {**c, "matched": False}

    _COMPANY_CACHE = name_index
    return list(name_index.values())


def lookup_company(name: str) -> dict | None:
    companies = get_company_list()
    cleaned = name.strip().lower()
    if cleaned in _COMPANY_CACHE:
        return _COMPANY_CACHE[cleaned]
    for c in companies:
        if cleaned in c["name"].lower():
            return c
    return None


def is_company_qualified(name: str, min_employees: int | None = None) -> bool | None:
    company = lookup_company(name)
    if company is None:
        return None
    threshold = min_employees or _settings.company_min_employees
    emp = company.get("employees", 0)
    return emp >= threshold if emp else None
