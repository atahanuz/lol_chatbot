#!/usr/bin/env python3
"""
League of Legends Monster Stats Scraper
Scrapes monster statistics from the LoL Wiki using Selenium
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import json
import time
import random
import re
import os

# Get project root directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))  # ssw_chatbot/
GAME_DATA_DIR = os.path.join(PROJECT_ROOT, 'data', 'game_data')

# List of monster pages to scrape
MONSTER_URLS = {
    # Epic Monsters
    "Baron Nashor": "https://wiki.leagueoflegends.com/en-us/Baron_Nashor",
    "Elder Dragon": "https://wiki.leagueoflegends.com/en-us/Elder_Dragon",
    "Rift Herald": "https://wiki.leagueoflegends.com/en-us/Rift_Herald",
    "Voidgrub": "https://wiki.leagueoflegends.com/en-us/Voidgrub",

    # Elemental Drakes
    "Cloud Drake": "https://wiki.leagueoflegends.com/en-us/Cloud_Drake",
    "Infernal Drake": "https://wiki.leagueoflegends.com/en-us/Infernal_Drake",
    "Mountain Drake": "https://wiki.leagueoflegends.com/en-us/Mountain_Drake",
    "Ocean Drake": "https://wiki.leagueoflegends.com/en-us/Ocean_Drake",
    "Hextech Drake": "https://wiki.leagueoflegends.com/en-us/Hextech_Drake",
    "Chemtech Drake": "https://wiki.leagueoflegends.com/en-us/Chemtech_Drake",

    # Large Jungle Monsters
    "Blue Sentinel": "https://wiki.leagueoflegends.com/en-us/Blue_Sentinel",
    "Red Brambleback": "https://wiki.leagueoflegends.com/en-us/Red_Brambleback",
    "Gromp": "https://wiki.leagueoflegends.com/en-us/Gromp",
    "Krug": "https://wiki.leagueoflegends.com/en-us/Krug",
    "Murk Wolf": "https://wiki.leagueoflegends.com/en-us/Murk_Wolf",
    "Crimson Raptor": "https://wiki.leagueoflegends.com/en-us/Crimson_Raptor",
    "Rift Scuttler": "https://wiki.leagueoflegends.com/en-us/Rift_Scuttler",
}

# Fields to extract for each category
BOUNTY_FIELDS = ["gold", "exp", "experience", "cs"]
STATS_FIELDS = ["health", "attack damage", "attack speed", "attack range", "armor",
                "magic resist", "magic resistance", "move speed", "movement speed",
                "unit radius", "monster type"]
LOCATION_FIELDS = ["camp", "initial", "spawn"]


def create_driver():
    """Create a Selenium WebDriver with appropriate options."""
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    return driver


def get_page_content(driver, url):
    """Fetch the HTML content of a page using Selenium."""
    try:
        driver.get(url)
        # Wait for the infobox to load
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "aside.portable-infobox, table.infobox, .infobox-wrapper"))
        )
        time.sleep(2)  # Extra wait for dynamic content
        return driver.page_source
    except Exception as e:
        print(f"  Error fetching page: {e}")
        # Try a simpler wait
        try:
            time.sleep(5)
            return driver.page_source
        except:
            return None


def normalize_label(label):
    """Normalize a label for comparison."""
    return label.lower().strip().replace("_", " ").replace("-", " ")


def categorize_field(label):
    """Determine which category a field belongs to."""
    normalized = normalize_label(label)

    for field in BOUNTY_FIELDS:
        if field in normalized:
            return "bounty"

    for field in STATS_FIELDS:
        if field in normalized:
            return "statistics"

    for field in LOCATION_FIELDS:
        if field in normalized:
            return "location"

    return None


def clean_value(value):
    """Clean extracted value text."""
    if not value:
        return None
    # Remove extra whitespace and newlines
    value = re.sub(r'\s+', ' ', value).strip()
    return value if value else None


def parse_portable_infobox(soup):
    """Parse Fandom's portable infobox structure."""
    data = {"bounty": {}, "statistics": {}, "location": {}}

    # Find portable infobox
    infobox = soup.find("aside", class_="portable-infobox")
    if not infobox:
        return data

    # Parse pi-data items (label-value pairs)
    data_items = infobox.find_all("div", class_="pi-item")
    for item in data_items:
        if "pi-data" not in item.get("class", []):
            continue

        label_elem = item.find(class_="pi-data-label")
        value_elem = item.find(class_="pi-data-value")

        if label_elem and value_elem:
            label = label_elem.get_text(strip=True)
            value = clean_value(value_elem.get_text(strip=True))

            if label and value:
                category = categorize_field(label)
                if category:
                    # Use original label but lowercase
                    data[category][label.lower()] = value

    # Also check for grouped sections
    groups = infobox.find_all("section", class_="pi-item")
    for group in groups:
        # Check group header
        header = group.find(class_="pi-header")
        header_text = header.get_text(strip=True).lower() if header else ""

        # Parse items in this group
        items = group.find_all("div", class_="pi-data")
        for item in items:
            label_elem = item.find(class_="pi-data-label")
            value_elem = item.find(class_="pi-data-value")

            if label_elem and value_elem:
                label = label_elem.get_text(strip=True)
                value = clean_value(value_elem.get_text(strip=True))

                if label and value:
                    # Determine category from group header or field name
                    if "bounty" in header_text:
                        data["bounty"][label.lower()] = value
                    elif "statistic" in header_text:
                        data["statistics"][label.lower()] = value
                    elif "location" in header_text:
                        data["location"][label.lower()] = value
                    else:
                        category = categorize_field(label)
                        if category:
                            data[category][label.lower()] = value

    return data


def parse_table_infobox(soup):
    """Parse traditional table-based infobox."""
    data = {"bounty": {}, "statistics": {}, "location": {}}

    # Find infobox table
    infobox = soup.find("table", class_=re.compile(r"infobox"))
    if not infobox:
        # Try finding tables with stat-like content
        for table in soup.find_all("table"):
            text = table.get_text().lower()
            if "health" in text and "attack" in text:
                infobox = table
                break

    if not infobox:
        return data

    current_section = None
    rows = infobox.find_all("tr")

    for row in rows:
        # Check for section headers
        header = row.find("th", colspan=True) or row.find("th", class_=re.compile(r"header"))
        if header:
            header_text = header.get_text(strip=True).lower()
            if "bounty" in header_text:
                current_section = "bounty"
            elif "statistic" in header_text:
                current_section = "statistics"
            elif "location" in header_text:
                current_section = "location"
            continue

        # Parse data rows
        cells = row.find_all(["th", "td"])
        if len(cells) >= 2:
            label = cells[0].get_text(strip=True)
            value = clean_value(cells[1].get_text(strip=True))

            if label and value:
                # Determine category
                if current_section:
                    data[current_section][label.lower()] = value
                else:
                    category = categorize_field(label)
                    if category:
                        data[category][label.lower()] = value

    return data


def parse_lol_wiki_infobox(soup):
    """Parse LoL Wiki's custom infobox structure."""
    data = {"bounty": {}, "statistics": {}, "location": {}}

    # Find the main infobox div
    infobox = soup.find("div", class_="infobox")
    if not infobox:
        return data

    current_section = None

    # Iterate through all children to track sections
    for element in infobox.find_all(["div"], recursive=True):
        classes = element.get("class", [])

        # Check for section headers
        if "infobox-header" in classes:
            header_text = element.get_text(strip=True).lower()
            if "bounty" in header_text:
                current_section = "bounty"
            elif "statistic" in header_text:
                current_section = "statistics"
            elif "location" in header_text:
                current_section = "location"
            continue

        # Parse data rows - look for exact class match
        if "infobox-data-row" in classes:
            label_elem = element.find("div", class_="infobox-data-label")
            value_elem = element.find("div", class_="infobox-data-value")

            if label_elem and value_elem:
                label = label_elem.get_text(strip=True)
                value = clean_value(value_elem.get_text(strip=True))

                if label and value and label.lower() != value.lower():
                    # Determine category from current section or field name
                    if current_section:
                        data[current_section][label.lower()] = value
                    else:
                        category = categorize_field(label)
                        if category:
                            data[category][label.lower()] = value

    return data


def parse_div_infobox(soup):
    """Parse generic div-based infobox structures."""
    data = {"bounty": {}, "statistics": {}, "location": {}}

    # Look for infobox wrapper divs
    infobox = soup.find("div", class_=re.compile(r"infobox"))
    if not infobox:
        return data

    # Find all stat rows - be more specific to avoid matching labels
    stat_rows = infobox.find_all("div", class_=re.compile(r"data-row|stat-row"))

    for row in stat_rows:
        # Try different label/value patterns - avoid matching "data" alone
        label_elem = row.find(class_=re.compile(r"label|name|key"))
        value_elem = row.find(class_=re.compile(r"-value|^value"))

        if label_elem and value_elem and label_elem != value_elem:
            label = label_elem.get_text(strip=True)
            value = clean_value(value_elem.get_text(strip=True))

            # Skip if label equals value (indicates header row)
            if label and value and label.lower() != value.lower():
                category = categorize_field(label)
                if category:
                    data[category][label.lower()] = value

    return data


def parse_monster_page(html, monster_name):
    """Parse monster stats from the page HTML."""
    soup = BeautifulSoup(html, "html.parser")

    monster_data = {
        "name": monster_name,
        "bounty": {},
        "statistics": {},
        "location": {}
    }

    # Try different parsing strategies (LoL wiki specific parser first)
    parsers = [
        parse_lol_wiki_infobox,
        parse_portable_infobox,
        parse_table_infobox,
        parse_div_infobox
    ]

    for parser in parsers:
        result = parser(soup)
        # Merge results
        for category in ["bounty", "statistics", "location"]:
            monster_data[category].update(result[category])

    # Standardize field names
    monster_data = standardize_fields(monster_data)

    return monster_data


def standardize_fields(data):
    """Standardize field names to match expected output."""
    field_mappings = {
        "experience": "exp",
        "creep score": "cs",
        "magic resistance": "magic resist",
        "movement speed": "move speed",
    }

    for category in ["bounty", "statistics", "location"]:
        new_dict = {}
        for key, value in data[category].items():
            # Apply mappings
            new_key = field_mappings.get(key, key)
            new_dict[new_key] = value
        data[category] = new_dict

    return data


def scrape_monster(driver, name, url):
    """Scrape stats for a single monster."""
    print(f"Scraping {name}...")

    html = get_page_content(driver, url)
    if not html:
        print(f"  Failed to fetch {name}")
        return None

    monster_data = parse_monster_page(html, name)

    # Check if we got any meaningful data
    total_fields = len(monster_data["bounty"]) + len(monster_data["statistics"]) + len(monster_data["location"])
    if total_fields > 0:
        print(f"  Successfully scraped {name} ({total_fields} fields)")
    else:
        print(f"  Warning: No stats found for {name}")

    return monster_data


def scrape_all_monsters():
    """Scrape all monsters and return the data."""
    all_monsters = []

    print("Starting Chrome browser...")
    driver = create_driver()

    try:
        for name, url in MONSTER_URLS.items():
            monster_data = scrape_monster(driver, name, url)
            if monster_data:
                all_monsters.append(monster_data)

            # Random delay between requests
            time.sleep(random.uniform(2, 4))

    finally:
        driver.quit()
        print("Browser closed.")

    return all_monsters


def save_to_json(data, filename=None):
    """Save the scraped data to a JSON file."""
    if filename is None:
        filename = os.path.join(GAME_DATA_DIR, "monsters.json")
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Data saved to {filename}")


def print_monster_stats(monster):
    """Pretty print monster stats in the format shown in the wiki."""
    print(f"\n{'='*50}")
    print(f"  {monster['name']}")
    print(f"{'='*50}")

    if monster["bounty"]:
        print("\n  Bounty")
        print("  " + "-"*20)
        for key, value in monster["bounty"].items():
            print(f"    {key.title()}: {value}")

    if monster["statistics"]:
        print("\n  Statistics")
        print("  " + "-"*20)
        for key, value in monster["statistics"].items():
            print(f"    {key.title()}: {value}")

    if monster["location"]:
        print("\n  Location")
        print("  " + "-"*20)
        for key, value in monster["location"].items():
            print(f"    {key.title()}: {value}")


def main():
    """Main function to run the scraper."""
    print("League of Legends Monster Stats Scraper")
    print("="*50)

    monsters = scrape_all_monsters()

    for monster in monsters:
        print_monster_stats(monster)

    if monsters:
        save_to_json(monsters)
        print(f"\n\nScraped {len(monsters)} monsters successfully!")
    else:
        print("\n\nNo monsters were scraped.")


if __name__ == "__main__":
    main()
