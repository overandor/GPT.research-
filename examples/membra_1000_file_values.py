"""MEMBRA USD 1,000 file-value demo.

Run:
    python examples/membra_1000_file_values.py

The numbers are internal demo appraisals for repository packaging.
They are not a promise of resale price, revenue, financing, or profit.
"""

FILES = [
    {
        "path": "public/index.html",
        "usd": 325,
        "layer": "DemoUI",
        "why": "Vercel-ready landing page that explains MEMBRA and routes visitors to the code.",
    },
    {
        "path": "examples/membra_1000_file_values.py",
        "usd": 350,
        "layer": "PriceOS code",
        "why": "Runnable code that appraises every demo file in dollars and verifies the total.",
    },
    {
        "path": "docs/DEMO_1000_FILE_APPRAISAL.md",
        "usd": 200,
        "layer": "Buyer memo",
        "why": "Human-readable explanation of the USD allocation and MEMBRA demo narrative.",
    },
    {
        "path": "vercel.json",
        "usd": 75,
        "layer": "Deploy config",
        "why": "Tells Vercel how to build and publish the static interface.",
    },
    {
        "path": "package.json",
        "usd": 50,
        "layer": "Build script",
        "why": "Defines the build command that packages the landing UI into dist for deployment.",
    },
]

TOTAL_USD = sum(item["usd"] for item in FILES)
TARGET_USD = 1000


def print_report():
    print("MEMBRA USD 1,000 FILE APPRAISAL DEMO")
    print("=" * 44)
    for item in FILES:
        print(f'{item["path"]}: USD {item["usd"]} | {item["layer"]}')
        print(f'  reason: {item["why"]}')
    print("-" * 44)
    print(f"TOTAL: USD {TOTAL_USD}")
    print(f"TARGET MET: {TOTAL_USD == TARGET_USD}")


if __name__ == "__main__":
    print_report()
