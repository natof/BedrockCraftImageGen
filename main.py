import json
import os
from PIL import Image
from fuzzywuzzy import fuzz
from colorama import Fore, Style
import yaml

with open('config.yml', 'r') as f:
    config = yaml.safe_load(f)

ADDON_PATH = config['ADDON_PATH']
CRAFTING_DATA_FILE = config['CRAFTING_DATA_FILE']
OUTPUT_PATH = config['OUTPUT_PATH']
BASE_IMAGE_PATH = config['BASE_IMAGE_PATH']
VANILLA_TEXTURES_PATH = config['VANILLA_TEXTURES_PATH']


def get_all_craft_data():
    craft_file = os.path.join(ADDON_PATH, "BP/recipes")
    items = {}
    for root, dirs, files in os.walk(craft_file):
        for file in files:
            if file.endswith('.json'):
                file_path = os.path.join(root, file)
                with open(file_path, "r") as json_file:
                    data = json.load(json_file)
                    if "minecraft:recipe_shaped" in data:
                        craft_name = data["minecraft:recipe_shaped"]["description"]["identifier"]
                        items[craft_name] = {
                            "item_result": data["minecraft:recipe_shaped"]["result"]["item"],
                            "pattern": data["minecraft:recipe_shaped"]["pattern"]
                        }
                        if "count" in data["minecraft:recipe_shaped"]["result"]:
                            items[craft_name]["count"] = data["minecraft:recipe_shaped"]["result"]["count"]
                        keys = data["minecraft:recipe_shaped"]["key"]
                        items[craft_name]["key"] = {key: value["item"] for key, value in keys.items() if
                                                    "item" in value}
    return items


def generate_crafting_map(name, pattern, mapping, result_name, result_count):
    crafting_array = [[None] * 3 for _ in range(3)]
    for row, line in enumerate(pattern):
        for col, char in enumerate(line):
            crafting_array[row][col] = mapping.get(char)
    return {
        "name": name,
        "pattern": crafting_array,
        "result": {result_name: result_count}
    }


def convert_craft_data_to_map():
    items = get_all_craft_data()
    crafting_datas = []
    for craft_name, item_data in items.items():
        count = item_data.get("count", 0)
        crafting_data = generate_crafting_map(craft_name, item_data["pattern"], item_data["key"],
                                              item_data["item_result"], count)
        crafting_datas.append(crafting_data)
    with open(CRAFTING_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(crafting_datas, f, ensure_ascii=False, indent=4)


def strip_prefix(item_name):
    prefixes = ["minecraft:", "paladium:"]
    for prefix in prefixes:
        if item_name.startswith(prefix):
            return item_name[len(prefix):]
    return item_name


def is_image_16x16(file_path):
    try:
        with Image.open(file_path) as img:
            return img.size == (16, 16)
    except IOError:
        return False


def tryGetTexturePath(item):
    texture_paths = [os.path.join(ADDON_PATH, "RP", "textures", "blocks"),
                     os.path.join(ADDON_PATH, "RP", "textures", "items"),
                     VANILLA_TEXTURES_PATH]

    best_match = None
    best_match_ratio = 0

    for path in texture_paths:
        if os.path.exists(path):
            for root, dirs, files in os.walk(path):
                for file in files:
                    file_name = os.path.splitext(file)[0]
                    similarity_ratio = fuzz.ratio(item.lower(), file_name.lower())
                    if similarity_ratio > best_match_ratio:
                        file_path = os.path.join(root, file)
                        if is_image_16x16(file_path):
                            best_match_ratio = similarity_ratio
                            best_match = file_path

    if best_match_ratio > 70:
        return best_match
    return ''


def generateCraftImage(name, pattern):
    name = strip_prefix(name)
    base_image = Image.open(BASE_IMAGE_PATH)
    width, height = base_image.size
    tile_width = width // 3
    tile_height = height // 3
    found = True

    for row in range(3):
        for col in range(3):
            element = pattern[row][col]
            if element:
                element = strip_prefix(element)
                path = tryGetTexturePath(element)
                if path != '':
                    element_image = Image.open(path).convert("RGBA")
                    element_width, element_height = element_image.size
                    x = col * tile_width + (tile_width - element_width) // 2
                    y = row * tile_height + (tile_height - element_height) // 2
                    base_image.paste(element_image, (x, y), element_image)
                else:
                    print(f"{Fore.RED} {name} file not found {Fore.CYAN} -> {Style.RESET_ALL} ❌")
                    found = False

    if found:
        print(f"{Fore.MAGENTA} {name} {Fore.CYAN} -> {Style.RESET_ALL} ✅")
        resized_image = base_image.resize((width * 5, height * 5), Image.NEAREST)
        resized_image.save(f"{OUTPUT_PATH}{name}.png", format="PNG")


def init():
    if ADDON_PATH == '':
        print(f"{Fore.RED}  [⚠️] addon path is missing in config.yml ❌")
        return
    convert_craft_data_to_map()

    with open(CRAFTING_DATA_FILE, "r") as json_file:
        data = json.load(json_file)

    for craft in data:
        generateCraftImage(craft["name"], craft["pattern"])


init()
