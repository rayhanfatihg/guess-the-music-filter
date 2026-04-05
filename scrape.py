"""
scrape.py
---------
Downloads song cover art from the Apple iTunes Search API (no API key required).
- Saves covers as zero-padded IDs: cover/001.jpg, cover/002.jpg, …
- Writes  name.csv  with columns: id, song_name, artist
- Skips songs whose cover cannot be fetched and reports them at the end.

Usage:
    python scrape.py
"""

import csv
import os
import time
import requests
from tqdm import tqdm

# ─── Configuration ────────────────────────────────────────────────────────────
COVER_DIR = os.path.join(os.path.dirname(__file__), "assets/cover")
CSV_PATH  = os.path.join(os.path.dirname(__file__), "assets/name.csv")
ITUNES_API = "https://itunes.apple.com/search"
ARTWORK_SIZE = 600          # iTunes returns art up to 600×600

# ─── Song List ────────────────────────────────────────────────────────────────
# Format: ("Song Title", "Artist")
SONGS = [
    ("Blinding Lights",          "The Weeknd"),
    ("Shape of You",             "Ed Sheeran"),
    ("Dance Monkey",             "Tones and I"),
    ("Someone Like You",         "Adele"),
    ("Bohemian Rhapsody",        "Queen"),
    ("Rolling in the Deep",      "Adele"),
    ("Uptown Funk",              "Mark Ronson"),
    ("Happy",                    "Pharrell Williams"),
    ("Thinking Out Loud",        "Ed Sheeran"),
    ("Stay With Me",             "Sam Smith"),
    ("Counting Stars",           "OneRepublic"),
    ("Shallow",                  "Lady Gaga"),
    ("Perfect",                  "Ed Sheeran"),
    ("Let Her Go",               "Passenger"),
    ("Photograph",               "Ed Sheeran"),
    ("Radioactive",              "Imagine Dragons"),
    ("Demons",                   "Imagine Dragons"),
    ("Stressed Out",             "Twenty One Pilots"),
    ("Ride",                     "Twenty One Pilots"),
    ("Believer",                 "Imagine Dragons"),
    ("Thunder",                  "Imagine Dragons"),
    ("Closer",                   "The Chainsmokers"),
    ("Something Just Like This", "The Chainsmokers"),
    ("Bad Guy",                  "Billie Eilish"),
    ("Happier",                  "Billie Eilish"),
    ("Watermelon Sugar",         "Harry Styles"),
    ("Levitating",               "Dua Lipa"),
    ("Don't Start Now",          "Dua Lipa"),
    ("As It Was",                "Harry Styles"),
    ("Anti-Hero",                "Taylor Swift"),
    ("Shake It Off",             "Taylor Swift"),
    ("Love Story",               "Taylor Swift"),
    ("Blank Space",              "Taylor Swift"),
    ("Can't Stop the Feeling",   "Justin Timberlake"),
    ("Senorita",                 "Shawn Mendes"),
    ("Stitches",                 "Shawn Mendes"),
    ("Treat You Better",         "Shawn Mendes"),
    ("Havana",                   "Camila Cabello"),
    ("Despacito",                "Luis Fonsi"),
    ("Cheap Thrills",            "Sia"),
    ("Chandelier",               "Sia"),
    ("Titanium",                 "David Guetta"),
    ("Wake Me Up",               "Avicii"),
    ("The Nights",               "Avicii"),
    ("Faded",                    "Alan Walker"),
    ("Alone",                    "Alan Walker"),
    ("Without Me",               "Eminem"),
    ("Lose Yourself",            "Eminem"),
    ("Hotline Bling",            "Drake"),
    ("One Dance",                "Drake"),

    # ── Spanish ───────────────────────────────────────────────────────────────
    ("Bailando",                 "Enrique Iglesias"),
    ("Gasolina",                 "Daddy Yankee"),
    ("Con Calma",                "Daddy Yankee"),
    ("Mi Gente",                 "J Balvin"),
    ("Hawai",                    "Maluma"),
    ("Dakiti",                   "Bad Bunny"),
    ("La Tortura",               "Shakira"),
    ("Hips Don't Lie",           "Shakira"),
    ("Danza Kuduro",             "Don Omar"),
    ("Taki Taki",                "DJ Snake"),

    # ── Japanese ──────────────────────────────────────────────────────────────
    ("Lemon",                    "Kenshi Yonezu"),
    ("Gurenge",                  "LiSA"),
    ("Pretender",                "Official HIGE DANdism"),
    ("Nandemonaiya",             "RADWIMPS"),
    ("Zankyou Sanka",            "Aimer"),
    ("Cruel Angel Thesis",       "Yoko Takahashi"),
    ("Blue Bird",                "Ikimono-gakari"),
    ("Again",                    "YUI"),
    ("First Love",               "Hikaru Utada"),
    ("One Last Kiss",            "Hikaru Utada"),

    # ── Anime Openings ────────────────────────────────────────────────────────
    ("Kaikai Kitan",             "Eve"),
    ("Guren no Yumiya",          "Linked Horizon"),
    ("Unravel",                  "TK from Ling Tosite Sigure"),
    ("Crossing Field",           "LiSA"),
    ("Peace Sign",               "Kenshi Yonezu"),
    ("Silhouette",               "KANA-BOON"),
    ("We Are",                   "Hiroshi Kitadani"),
    ("Resonance",                "T.M. Revolution"),
    ("Idol",                     "YOASOBI"),
    ("Homura",                   "LiSA"),

    # ── Backstreet Boys ───────────────────────────────────────────────────────
    ("I Want It That Way",       "Backstreet Boys"),
    ("Everybody",                "Backstreet Boys"),
    ("As Long As You Love Me",   "Backstreet Boys"),
    ("Quit Playing Games",       "Backstreet Boys"),
    ("Shape of My Heart",        "Backstreet Boys"),
    ("Show Me the Meaning of Being Lonely", "Backstreet Boys"),
    ("Larger Than Life",         "Backstreet Boys"),
    ("Incomplete",               "Backstreet Boys"),

    # ── Westlife ──────────────────────────────────────────────────────────────
    ("Swear It Again",           "Westlife"),
    ("Flying Without Wings",     "Westlife"),
    ("My Love",                  "Westlife"),
    ("Unbreakable",              "Westlife"),
    ("You Raise Me Up",          "Westlife"),
    ("World of Our Own",         "Westlife"),
    ("When You Tell Me That You Love Me", "Westlife"),
    ("Uptown Girl",              "Westlife"),

    # ── Indonesian ────────────────────────────────────────────────────────────
    ("Separuh Aku",              "Noah"),
    ("Sempurna",                 "Andra and the Backbone"),
    ("Tentang Kamu",             "Rizky Febian"),
    ("Hati-Hati di Jalan",       "Tulus"),
    ("Cinta Luar Biasa",         "Andmesh Kamaleng"),
    ("Yang Terdalam",            "Peterpan"),
    ("Bukan Cinta Biasa",        "Afgan"),
    ("Kangen",                   "Dewa 19"),
    ("Dealova",                  "Once Mekel"),
    ("Terlalu Lama Sendiri",     "Kunto Aji"),
]

# ─── Helpers ─────────────────────────────────────────────────────────────────

def fetch_artwork_url(song: str, artist: str) -> str | None:
    """Query iTunes API and return a 600×600 artwork URL, or None on failure."""
    params = {
        "term":   f"{song} {artist}",
        "entity": "song",
        "limit":  1,
    }
    try:
        resp = requests.get(ITUNES_API, params=params, timeout=10)
        resp.raise_for_status()
        results = resp.json().get("results", [])
        if not results:
            return None
        # iTunes returns 100×100 by default; upgrade to desired size
        url: str = results[0].get("artworkUrl100", "")
        return url.replace("100x100bb", f"{ARTWORK_SIZE}x{ARTWORK_SIZE}bb") if url else None
    except Exception as exc:
        print(f"\n  [WARN] iTunes API error for '{song}': {exc}")
        return None


def download_image(url: str, dest: str) -> bool:
    """Download an image from *url* and save to *dest*. Returns True on success."""
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        with open(dest, "wb") as fh:
            fh.write(resp.content)
        return True
    except Exception as exc:
        print(f"\n  [WARN] Download failed ({url}): {exc}")
        return False


# ─── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
    os.makedirs(COVER_DIR, exist_ok=True)

    rows: list[dict] = []
    failed: list[str] = []

    print(f"Fetching {len(SONGS)} song covers from iTunes …\n")

    for idx, (song, artist) in enumerate(tqdm(SONGS, unit="song"), start=1):
        song_id = f"{idx:03d}"
        dest    = os.path.join(COVER_DIR, f"{song_id}.jpg")

        # Skip if already downloaded (re-run friendly)
        if os.path.exists(dest):
            rows.append({"id": song_id, "song_name": song, "artist": artist})
            continue

        art_url = fetch_artwork_url(song, artist)
        if art_url and download_image(art_url, dest):
            rows.append({"id": song_id, "song_name": song, "artist": artist})
        else:
            failed.append(f"{song_id} – {song} ({artist})")

        # Be polite: iTunes has a 20 req/min soft limit
        time.sleep(0.4)

    # Write CSV
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["id", "song_name", "artist"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n✅  Downloaded {len(rows)} covers → {COVER_DIR}")
    print(f"📄  CSV written  → {CSV_PATH}")

    if failed:
        print(f"\n⚠️  Failed ({len(failed)}):")
        for f in failed:
            print(f"   {f}")


if __name__ == "__main__":
    main()
