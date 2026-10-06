"""Build an offline ISO/CLDR snapshot with pycountry==24.6.1 and Babel."""
import json
from pathlib import Path
import pycountry
from babel import Locale


def transliterate(text):
    pairs = dict(zip("абвгґдеєжзиіїйклмнопрстуфхцчшщьюя",
        ["a","b","v","h","g","d","e","ie","zh","z","y","i","i","i","k","l","m","n","o","p","r","s","t","u","f","kh","ts","ch","sh","shch","","iu","ia"]))
    initial = {"є":"ye", "ї":"yi", "й":"y", "ю":"yu", "я":"ya"}
    result, start = [], True
    for char in text:
        lower = char.lower()
        value = initial.get(lower, pairs.get(lower, char)) if start else pairs.get(lower, char)
        result.append(value.capitalize() if char.isupper() else value)
        start = not char.isalpha()
    return "".join(result).replace("zhh", "zgh").replace("'", "").replace("’", "")


if __name__ == "__main__":
    uk, en = Locale("uk"), Locale("en")
    rows = []
    for country in sorted(pycountry.countries, key=lambda c: c.alpha_2):
        name = uk.territories.get(country.alpha_2, country.name)
        rows.append(dict(alpha2=country.alpha_2, alpha3=country.alpha_3, numeric=country.numeric,
            name_uk=name, name_en=en.territories.get(country.alpha_2, country.name),
            transliteration=transliterate(name)))
    target = Path(__file__).resolve().parents[1] / "app/data/countries.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(rows, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(f"Generated {len(rows)} ISO country/territory records")
