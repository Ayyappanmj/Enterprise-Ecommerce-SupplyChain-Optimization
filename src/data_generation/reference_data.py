"""
Static reference pools used to synthesize realistic-looking business data.

Deliberately dependency-free (no Faker / no internet) so the whole pipeline
runs offline with just numpy + pandas.
"""

REGIONS = ["North America", "Europe", "Asia Pacific", "Latin America", "Middle East & Africa"]

COUNTRIES = [
    # (country_name, region, currency_code)
    ("United States", "North America", "USD"),
    ("Canada", "North America", "CAD"),
    ("Mexico", "North America", "MXN"),
    ("United Kingdom", "Europe", "GBP"),
    ("Germany", "Europe", "EUR"),
    ("France", "Europe", "EUR"),
    ("Italy", "Europe", "EUR"),
    ("Spain", "Europe", "EUR"),
    ("Netherlands", "Europe", "EUR"),
    ("Poland", "Europe", "PLN"),
    ("Sweden", "Europe", "SEK"),
    ("China", "Asia Pacific", "CNY"),
    ("Japan", "Asia Pacific", "JPY"),
    ("India", "Asia Pacific", "INR"),
    ("South Korea", "Asia Pacific", "KRW"),
    ("Australia", "Asia Pacific", "AUD"),
    ("Singapore", "Asia Pacific", "SGD"),
    ("Indonesia", "Asia Pacific", "IDR"),
    ("Vietnam", "Asia Pacific", "VND"),
    ("Thailand", "Asia Pacific", "THB"),
    ("Brazil", "Latin America", "BRL"),
    ("Argentina", "Latin America", "ARS"),
    ("Chile", "Latin America", "CLP"),
    ("Colombia", "Latin America", "COP"),
    ("Peru", "Latin America", "PEN"),
    ("United Arab Emirates", "Middle East & Africa", "AED"),
    ("Saudi Arabia", "Middle East & Africa", "SAR"),
    ("South Africa", "Middle East & Africa", "ZAR"),
    ("Egypt", "Middle East & Africa", "EGP"),
    ("Nigeria", "Middle East & Africa", "NGN"),
]

CURRENCIES = {
    "USD": ("US Dollar", "$"), "CAD": ("Canadian Dollar", "$"), "MXN": ("Mexican Peso", "$"),
    "GBP": ("British Pound", "£"), "EUR": ("Euro", "€"), "PLN": ("Polish Zloty", "zł"),
    "SEK": ("Swedish Krona", "kr"), "CNY": ("Chinese Yuan", "¥"), "JPY": ("Japanese Yen", "¥"),
    "INR": ("Indian Rupee", "₹"), "KRW": ("South Korean Won", "₩"), "AUD": ("Australian Dollar", "$"),
    "SGD": ("Singapore Dollar", "$"), "IDR": ("Indonesian Rupiah", "Rp"), "VND": ("Vietnamese Dong", "₫"),
    "THB": ("Thai Baht", "฿"), "BRL": ("Brazilian Real", "R$"), "ARS": ("Argentine Peso", "$"),
    "CLP": ("Chilean Peso", "$"), "COP": ("Colombian Peso", "$"), "PEN": ("Peruvian Sol", "S/"),
    "AED": ("UAE Dirham", "د.إ"), "SAR": ("Saudi Riyal", "﷼"), "ZAR": ("South African Rand", "R"),
    "EGP": ("Egyptian Pound", "£"), "NGN": ("Nigerian Naira", "₦"),
}

# Approximate baseline rate to USD (used as anchor; daily rates add noise around this)
BASE_RATE_TO_USD = {
    "USD": 1.0, "CAD": 0.74, "MXN": 0.058, "GBP": 1.27, "EUR": 1.09, "PLN": 0.25,
    "SEK": 0.096, "CNY": 0.14, "JPY": 0.0067, "INR": 0.012, "KRW": 0.00075, "AUD": 0.66,
    "SGD": 0.75, "IDR": 0.000063, "VND": 0.000040, "THB": 0.028, "BRL": 0.20, "ARS": 0.0011,
    "CLP": 0.0011, "COP": 0.00025, "PEN": 0.27, "AED": 0.27, "SAR": 0.27, "ZAR": 0.055,
    "EGP": 0.021, "NGN": 0.00065,
}

FIRST_NAMES = [
    "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda", "William", "Elizabeth",
    "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica", "Thomas", "Sarah", "Charles", "Karen",
    "Wei", "Mei", "Hiroshi", "Yuki", "Raj", "Priya", "Ahmed", "Fatima", "Carlos", "Maria",
    "Lucas", "Sofia", "Liam", "Olivia", "Noah", "Emma", "Ethan", "Ava", "Mateus", "Isabela",
    "Kwame", "Amara", "Chidi", "Ngozi", "Sven", "Ingrid", "Piotr", "Anna", "Diego", "Valentina",
]
LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
    "Wang", "Li", "Zhang", "Chen", "Tanaka", "Suzuki", "Kim", "Park", "Patel", "Sharma",
    "Khan", "Ali", "Silva", "Santos", "Oliveira", "Müller", "Schmidt", "Rossi", "Kowalski", "Nowak",
    "Andersson", "Johansson", "Nguyen", "Tran", "Osei", "Mensah", "Okafor", "Adeyemi", "Botha", "Van Der Merwe",
]
CITIES_BY_COUNTRY = {
    "United States": ["New York", "Los Angeles", "Chicago", "Houston", "Atlanta", "Seattle"],
    "Canada": ["Toronto", "Vancouver", "Montreal", "Calgary"],
    "Mexico": ["Mexico City", "Guadalajara", "Monterrey"],
    "United Kingdom": ["London", "Manchester", "Birmingham"],
    "Germany": ["Berlin", "Munich", "Hamburg"],
    "France": ["Paris", "Lyon", "Marseille"],
    "Italy": ["Rome", "Milan", "Naples"],
    "Spain": ["Madrid", "Barcelona", "Valencia"],
    "Netherlands": ["Amsterdam", "Rotterdam"],
    "Poland": ["Warsaw", "Krakow"],
    "Sweden": ["Stockholm", "Gothenburg"],
    "China": ["Shanghai", "Beijing", "Shenzhen", "Guangzhou"],
    "Japan": ["Tokyo", "Osaka", "Yokohama"],
    "India": ["Mumbai", "Delhi", "Bengaluru", "Pune", "Hyderabad"],
    "South Korea": ["Seoul", "Busan"],
    "Australia": ["Sydney", "Melbourne", "Brisbane"],
    "Singapore": ["Singapore"],
    "Indonesia": ["Jakarta", "Surabaya"],
    "Vietnam": ["Ho Chi Minh City", "Hanoi"],
    "Thailand": ["Bangkok", "Chiang Mai"],
    "Brazil": ["Sao Paulo", "Rio de Janeiro", "Brasilia"],
    "Argentina": ["Buenos Aires", "Cordoba"],
    "Chile": ["Santiago", "Valparaiso"],
    "Colombia": ["Bogota", "Medellin"],
    "Peru": ["Lima", "Arequipa"],
    "United Arab Emirates": ["Dubai", "Abu Dhabi"],
    "Saudi Arabia": ["Riyadh", "Jeddah"],
    "South Africa": ["Johannesburg", "Cape Town"],
    "Egypt": ["Cairo", "Alexandria"],
    "Nigeria": ["Lagos", "Abuja"],
}

CUSTOMER_SEGMENTS = ["Consumer", "SMB", "Corporate"]
LOYALTY_TIERS = ["Bronze", "Silver", "Gold", "Platinum"]

PRODUCT_CATEGORIES = {
    "Electronics": ["Smartphones", "Laptops", "Audio", "Wearables", "Cameras"],
    "Home & Kitchen": ["Cookware", "Furniture", "Small Appliances", "Decor"],
    "Apparel": ["Men's Clothing", "Women's Clothing", "Footwear", "Accessories"],
    "Health & Beauty": ["Skincare", "Personal Care", "Supplements"],
    "Sports & Outdoors": ["Fitness Equipment", "Outdoor Gear", "Cycling"],
    "Toys & Games": ["Action Figures", "Board Games", "Puzzles"],
    "Office & Stationery": ["Office Supplies", "Notebooks", "Printers"],
    "Automotive": ["Car Accessories", "Tools", "Car Care"],
}

WAREHOUSE_TYPES = ["Fulfillment Center", "Regional Distribution Hub", "Cross-Dock", "Bonded Warehouse"]
ROUTE_TYPES = ["Air", "Sea", "Ground", "Rail"]
SERVICE_LEVELS = ["Standard", "Express", "Economy", "Same-Day"]
ORDER_STATUSES = ["Delivered", "Shipped", "Processing", "Cancelled", "Returned"]
PAYMENT_METHODS = ["Credit Card", "Debit Card", "PayPal", "Bank Transfer", "Cash on Delivery", "Digital Wallet"]
PAYMENT_STATUSES = ["Completed", "Pending", "Failed", "Refunded"]
RETURN_REASONS = [
    "Defective Product", "Wrong Item Shipped", "Item Not as Described", "Changed Mind",
    "Better Price Found Elsewhere", "Late Delivery", "Damaged in Transit", "Size/Fit Issue",
]
RETURN_STATUSES = ["Requested", "Approved", "Rejected", "Refunded", "Received"]
RETURN_CONDITIONS = ["Unopened", "Opened - Like New", "Damaged", "Missing Parts"]
MARKETING_CHANNELS = ["Email", "Social Media", "Search Ads", "Influencer", "Affiliate", "TV/Radio"]
SUPPLIER_NAME_SUFFIXES = ["Industries", "Global Supply", "Manufacturing Co.", "Trading Ltd.", "Exports", "Group"]
