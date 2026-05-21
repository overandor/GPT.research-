FILES = [
    {"path": "public/index.html", "usd": 325},
    {"path": "examples/membra_1000_file_values.py", "usd": 350},
    {"path": "public/membra-demo-1000.json", "usd": 125},
    {"path": "docs/DEMO_1000_FILE_APPRAISAL.md", "usd": 200},
]

TOTAL_USD = sum(item["usd"] for item in FILES)

if __name__ == "__main__":
    for item in FILES:
        print(f'{item["path"]}: USD {item["usd"]}')
    print(f'TOTAL: USD {TOTAL_USD}')
