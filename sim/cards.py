"""Abstract card database for the Captain Sisay goldfish simulator.

Only what the simulator needs is modelled: cost, types, mana output and a set
of tags that the engine keys behaviour off. Interaction (Swords, Veil, ...)
is present but does nothing in a goldfish game.

Mana units: 'G', 'W', 'C' (colorless) and 'A' (either G or W).
Costs are (generic, green, white).
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Card:
    name: str
    types: frozenset
    cost: tuple = (0, 0, 0)
    x: bool = False
    legendary: bool = False
    colors: str = ""
    mana: tuple = ()
    forest: bool = False
    power: int = 1
    tags: frozenset = frozenset()

    @property
    def mv(self):
        return sum(self.cost)

    @property
    def gpips(self):
        return self.cost[1]

    def is_(self, t):
        return t in self.types

    def has(self, tag):
        return tag in self.tags


def _cost(s):
    generic, g, w = 0, 0, 0
    num = ""
    for ch in s:
        if ch.isdigit():
            num += ch
        elif ch == "G":
            g += 1
        elif ch == "W":
            w += 1
    if num:
        generic = int(num)
    return (generic, g, w)


def C(name, types, cost="", leg=False, mana="", tags="", forest=False, power=1, x=False, colors=None):
    c = _cost(cost)
    if colors is None:
        colors = ("G" if c[1] else "") + ("W" if c[2] else "")
    return Card(
        name=name,
        types=frozenset(types.split()),
        cost=c,
        x=x,
        legendary=leg,
        colors=colors,
        mana=tuple(mana),
        forest=forest,
        power=power,
        tags=frozenset(tags.split()),
    )


FETCH = "fetch"

CARDS = [
    # --- lands ---
    C("Ancient Tomb", "land", mana="CC"),
    C("Arid Mesa", "land", tags=FETCH),
    C("Flooded Strand", "land", tags=FETCH),
    C("Marsh Flats", "land", tags=FETCH),
    C("Misty Rainforest", "land", tags=FETCH),
    C("Verdant Catacombs", "land", tags=FETCH),
    C("Windswept Heath", "land", tags=FETCH),
    C("Wooded Foothills", "land", tags=FETCH),
    C("Bountiful Promenade", "land", mana="A"),
    C("Branchloft Pathway", "land", tags="pathway"),
    C("Brushland", "land", mana="A"),
    C("Cavern of Souls", "land", mana="A"),
    C("City of Brass", "land", mana="A"),
    C("Command Tower", "land", mana="A"),
    C("Horizon Canopy", "land", mana="A"),
    C("Savannah", "land", mana="A", forest=True, tags="dual"),
    C("Temple Garden", "land", mana="A", forest=True, tags="dual"),
    C("Forest", "land", mana="G", forest=True, tags="basic"),
    C("Plains", "land", mana="W", tags="basic"),
    C("Boseiju, Who Endures", "land", leg=True, mana="G"),
    C("Eiganjo, Seat of the Empire", "land", leg=True, mana="W"),
    C("Yavimaya, Cradle of Growth", "land", leg=True, mana="G", tags="yavimaya"),
    C("Gemstone Caverns", "land", leg=True, mana="C"),
    C("Talon Gates of Madara", "land", mana="C"),
    C("Gaea's Cradle", "land", leg=True, tags="cradle"),
    C("Nykthos, Shrine to Nyx", "land", leg=True, tags="nykthos"),
    C("Dryad Arbor", "land creature", mana="G", forest=True, colors="G", tags="dork"),
    # --- artifacts ---
    C("Chrome Mox", "artifact", mana="A", tags="imprint"),
    C("Mox Diamond", "artifact", mana="A", tags="diamond"),
    C("Mox Amber", "artifact", leg=True, mana="A", tags="amber"),
    C("Lotus Petal", "artifact", mana="A", tags="petal"),
    C("Mana Vault", "artifact", "1", mana="CCC", tags="vault"),
    C("Sol Ring", "artifact", "1", mana="CC"),
    C("Lightning Greaves", "artifact", "2", tags="greaves"),
    C("Thousand-Year Elixir", "artifact", "3", tags="haste"),
    C("Marvin, Murderous Mimic", "artifact creature", "2", leg=True, power=2),
    # --- mana creatures ---
    C("Arbor Elf", "creature", "G", tags="elf dork arbor"),
    C("Avacyn's Pilgrim", "creature", "G", mana="W", tags="dork"),
    C("Birds of Paradise", "creature", "G", mana="A", tags="dork"),
    C("Elvish Mystic", "creature", "G", mana="G", tags="elf dork"),
    C("Fyndhorn Elves", "creature", "G", mana="G", tags="elf dork"),
    C("Llanowar Elves", "creature", "G", mana="G", tags="elf dork"),
    C("Delighted Halfling", "creature", "1G", mana="A", tags="dork", power=2),
    C("Bloom Tender", "creature", "1G", tags="elf dork bloom"),
    C("Fanatic of Rhonas", "creature", "3G", tags="dork fanatic"),
    C("Selvala, Heart of the Wilds", "creature", "1GG", leg=True, tags="elf dork selvala", power=2),
    C("Voyaging Satyr", "creature", "1G", tags="dork satyr"),
    C("Wall of Roots", "creature", "1G", tags="wall"),
    C("Elvish Spirit Guide", "creature", "2G", tags="esg", power=2),
    # --- combo / engine creatures ---
    C("Ashaya, Soul of the Wild", "creature", "3GG", leg=True, tags="ashaya"),
    C("Hope Tender", "creature", "1G", tags="hope"),
    C("Magus of the Candelabra", "creature", "G", tags="magus"),
    C("Badgermole Cub", "creature", "1G", tags="cub", power=2),
    C("Emiel the Blessed", "creature", "2WW", leg=True, tags="emiel", power=4),
    C("Flash Thompson, Spider-Fan", "creature", "1W", leg=True, tags="flash", power=2),
    C("Formidable Speaker", "creature", "2G", tags="elf speaker", power=2),
    C("Kamahl, Fist of Krosa", "creature", "4GG", leg=True, tags="kamahl", power=4),
    C("Shang-Chi, Master of Kung Fu", "creature", "1G", leg=True, tags="haste", power=2),
    C("Knight of the Reliquary", "creature", "1GW", tags="knight", power=2),
    C("Captain Sisay", "creature", "2GW", leg=True, tags="sisay", power=2),
    # --- other creatures ---
    C("Esper Sentinel", "creature", "W"),
    C("Grand Abolisher", "creature", "WW", power=2),
    C("Ranger-Captain of Eos", "creature", "1W", tags="rangercap", power=3),
    C("Spectacular Spider-Man", "creature", "1W", leg=True, power=3),
    C("Boromir, Warden of the Tower", "creature", "2W", leg=True, power=3),
    C("Mayor Tong of Chin Village", "creature", "1W"),
    C("Voice of Victory", "creature", "1W"),
    C("Jennifer Walters", "creature", "1GW", leg=True, power=2),
    C("Toph, the Blind Bandit", "creature", "2G", leg=True),
    C("Quirion Ranger", "creature", "G", tags="elf"),
    C("Scryb Ranger", "creature", "1G"),
    # --- enchantments ---
    C("Concordant Crossroads", "enchantment", "G", tags="haste"),
    C("Survival of the Fittest", "enchantment", "G", tags="survival"),
    C("Utopia Sprawl", "enchantment", "G", mana="A", tags="aura"),
    C("Wild Growth", "enchantment", "G", mana="G", tags="aura"),
    C("Nature's Chosen", "enchantment", "G", tags="dead"),
    C("Animate Land", "instant", "G", tags="dead"),
    C("Verdant Touch", "sorcery", "1G", tags="dead"),
    C("Fal'Cie Paradise", "enchantment", "G", tags="dead"),
    # --- tutors ---
    C("Chord of Calling", "instant", "GGG", x=True, tags="tutor chord"),
    C("Green Sun's Zenith", "sorcery", "G", x=True, tags="tutor gsz"),
    C("Finale of Devastation", "sorcery", "GG", x=True, tags="tutor finale"),
    C("Nature's Rhythm", "sorcery", "GG", x=True, tags="tutor rhythm"),
    C("Natural Order", "sorcery", "2GG", tags="tutor natorder"),
    C("Eldritch Evolution", "sorcery", "1GG", tags="tutor eldritch"),
    C("Eladamri's Call", "instant", "GW", tags="tutor eladamri"),
    C("Summoner's Pact", "instant", "", colors="G", tags="tutor pact"),
    C("Worldly Tutor", "instant", "G", tags="tutor toptutor"),
    C("Sylvan Tutor", "sorcery", "G", tags="tutor toptutor"),
    C("Enlightened Tutor", "instant", "W", tags="enlightened"),
    C("Crop Rotation", "instant", "G", tags="croprot"),
    C("Sylvan Scrying", "sorcery", "1G", tags="scrying"),
    C("Once Upon a Time", "instant", "1G", tags="ouat"),
    # --- interaction / protection (inert in goldfish) ---
    C("Emerald Charm", "instant", "G", tags="dead"),
    C("Legolas's Quick Reflexes", "instant", "G", tags="dead"),
    C("Silence", "instant", "W", tags="dead"),
    C("Swords to Plowshares", "instant", "W", tags="dead"),
    C("Veil of Summer", "instant", "G", tags="dead"),
    C("Vitalize", "instant", "G", tags="dead"),
]

BLANK = "Blank"

# Not in the list: candidates for swap testing (--add) plus the filler for --remove.
CANDIDATES = [
    C(BLANK, "sorcery", "99", tags="dead"),
    C("Argothian Elder", "creature", "3G", tags="elder", power=2),
    C("Devoted Druid", "creature", "1G", mana="G", tags="elf dork druid"),
    C("Vizier of Remedies", "creature", "1W", tags="vizier", power=2),
    C("Umbral Mantle", "artifact", "3", tags="mantle"),
    C("Elvish Reclaimer", "creature", "G", tags="reclaimer"),
    C("Gilded Goose", "creature", "G", mana="A", tags="dork"),
    C("Walking Ballista", "artifact creature", "", tags="ballista"),
    C("Ezuri, Renegade Leader", "creature", "1GG", leg=True, tags="elf ezuri", power=2),
]

BY_NAME = {c.name: c for c in CARDS + CANDIDATES}

COMMANDER = "Captain Sisay"


def load_decklist(path):
    deck = []
    for line in open(path):
        line = line.strip()
        if not line:
            continue
        n, name = line.split(" ", 1)
        if name not in BY_NAME:
            raise KeyError(f"unknown card in decklist: {name}")
        deck += [BY_NAME[name]] * int(n)
    return deck


def swap(deck, remove=(), add=()):
    """Replace each removed card in place (keeps shuffles comparable) with the next added card or a Blank."""
    deck = list(deck)
    add = list(add)
    for name in remove:
        idx = next((i for i, c in enumerate(deck) if c.name == name), None)
        if idx is None:
            raise KeyError(f"not in deck: {name}")
        new = add.pop(0) if add else BLANK
        if new not in BY_NAME:
            raise KeyError(f"unknown card: {new}")
        deck[idx] = BY_NAME[new]
    if add:
        raise ValueError("more --add than --remove; every addition needs a cut")
    return deck
