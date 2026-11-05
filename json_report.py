import json

def write_json_report(page_data, filename="report.json"):
    sorted_pages = sorted(page_data.values(), key=lambda page: page["url"])

    with open(filename, "w", encoding="utf-8") as file:
        json.dump(sorted_pages, file, indent=2)