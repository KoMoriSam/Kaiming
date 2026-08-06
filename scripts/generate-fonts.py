"""Build the sans and serif Kaiming punctuation font families.

Each visual family is emitted as nine static weights and one variable font in
both WOFF2/TrueType and OTF/CFF formats. The variable fonts interpolate the
nine processed masters, so every shipped static weight remains an exact master.

Rules baked into the output:

* pauses, brackets, middle dot, en dash, slash, and vertical bar have a
  centered 0.5-em base advance;
* middle dot, en dash, slash, vertical bar, and em dash are vertically aligned
  on the CJK visual center axis;
* four-per-em, en, and ideographic spaces have 0.25-em, 0.5-em, and 1-em
  advances respectively;
* stops have a 1-em base advance;
* ``。？！`` expose a ``halt`` adjustment that removes their trailing 0.5 em
  when CSS line layout trims fullwidth punctuation at a line end;
* every closing-opening pair is two natural half-em forms, for a 1-em logical
  advance with the source typeface's normal contour gap;
* adjacent stops are compressed from 2 em to 1.5 em;
* an em dash is centered against the CJK em box and ``——`` becomes one
  continuous 2-em ligature with 0.05-em outer side bearings;
* ellipsis pairs remain 2 em and long-mark pairs receive no kerning.

Requires Python packages ``fonttools`` and ``brotli``. Generated font files are
committed assets and only need rebuilding after a Fontsource update or a
punctuation-rule change.
"""

from copy import deepcopy
from math import floor
from pathlib import Path

from fontTools.designspaceLib import (
    AxisDescriptor,
    DesignSpaceDocument,
    InstanceDescriptor,
    SourceDescriptor,
)
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.fontBuilder import FontBuilder
from fontTools.otlLib.builder import buildStatTable
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable
from fontTools.varLib import build as build_variable_font
from fontTools.varLib.instancer import instantiateVariableFont


ROOT = Path(__file__).resolve().parents[1]
STATIC_FONT_ROOT = ROOT / "node_modules" / "@fontsource"
VARIABLE_FONT_ROOT = ROOT / "node_modules" / "@fontsource-variable"
OUTPUT_ROOT = ROOT / "fonts"
VARIABLE_ROOT = OUTPUT_ROOT / "variable"
STATIC_OTF_ROOT = OUTPUT_ROOT / "static" / "otf"
STATIC_WOFF2_ROOT = OUTPUT_ROOT / "static" / "woff2"
WEIGHTS = tuple(range(100, 1000, 100))
WEIGHT_NAMES = {
    100: "Thin",
    200: "ExtraLight",
    300: "Light",
    400: "Regular",
    500: "Medium",
    600: "SemiBold",
    700: "Bold",
    800: "ExtraBold",
    900: "Black",
}

FAMILIES = {
    "sans": "noto-sans-sc",
    "serif": "noto-serif-sc",
}

FAMILY_NAMES = {
    "sans": "Kaiming Punctuation Sans",
    "serif": "Kaiming Punctuation Serif",
}

POSTSCRIPT_FAMILY_NAMES = {
    "sans": "KaimingPunctuationSans",
    "serif": "KaimingPunctuationSerif",
}

CHINESE_FAMILY_NAMES = {
    "sans": "开明标点黑",
    "serif": "开明标点宋",
}

CHINESE_WEIGHT_NAMES = {
    100: "纤细",
    200: "特细",
    300: "细",
    400: "常规",
    500: "中等",
    600: "半粗",
    700: "粗",
    800: "特粗",
    900: "重黑",
}

SOURCE_COPYRIGHTS = {
    "sans": (
        "(c) 2014-2021 Adobe (http://www.adobe.com/), "
        "with Reserved Font Name 'Source'."
    ),
    "serif": "(c) 2017-2024 Adobe (http://www.adobe.com/).",
}
MODIFICATION_COPYRIGHT = (
    "Kaiming punctuation modifications Copyright (c) 2026 "
    "Kaiming contributors."
)
OFL_DESCRIPTION = (
    "This Font Software is licensed under the SIL Open Font License, "
    "Version 1.1."
)
OFL_URL = "https://openfontlicense.org"

SOURCE_PARTS = {
    "latin": (0x2018, 0x2019),
    "5": (0xFF5B, 0xFF5D),
    "91": (0x2002,),
    "100": (0x3008,),
    "101": (0x3009, 0x3016, 0x3017),
    "102": (0xFF3B, 0xFF3D),
    "103": (0x3014, 0x3015),
    "106": (0x300E, 0x300F),
    "110": (0x300C, 0x300D),
    "114": (0x2026,),
    "115": (0xFF1B,),
    "116": (0x3000, 0x300A, 0x300B),
    "117": (0x201C, 0x201D, 0x3010, 0x3011, 0xFF1F),
    "118": (0x007C, 0xFF01, 0xFF08, 0xFF09),
    "119": (
        0x002F,
        0x00B7,
        0x2013,
        0x2014,
        0x3001,
        0x3002,
        0xFF0C,
        0xFF1A,
    ),
}

OPENING = {
    0x2018,
    0x201C,
    0x3008,
    0x300A,
    0x300C,
    0x300E,
    0x3010,
    0x3014,
    0x3016,
    0xFF08,
    0xFF3B,
    0xFF5B,
}

CLOSING = {
    0x2019,
    0x201D,
    0x3009,
    0x300B,
    0x300D,
    0x300F,
    0x3011,
    0x3015,
    0x3017,
    0xFF09,
    0xFF3D,
    0xFF5D,
}

PAUSE_MARKS = {0x3001, 0xFF0C, 0xFF1A, 0xFF1B}
FULL_STOPS = {0x3002, 0xFF01, 0xFF1F}
LONG_MARKS = {0x2014, 0x2026}
DASH_PAIR_SIDE_BEARING_DIVISOR = 20
CENTERED_HALF_WIDTH = {0x002F, 0x007C, 0x00B7, 0x2013}
VERTICALLY_CENTERED_HALF_WIDTH = CENTERED_HALF_WIDTH
HALF_WIDTH = OPENING | CLOSING | PAUSE_MARKS | CENTERED_HALF_WIDTH
SPACE_ADVANCE_DIVISORS = {
    0x2005: 4,
    0x2002: 2,
    0x3000: 1,
}
SYNTHETIC_SOURCES = {0x2005: 0x2002}
ALL_CODEPOINTS = (
    set().union(*SOURCE_PARTS.values()) | set(SYNTHETIC_SOURCES)
)
BRACKET_SIDE_REFERENCES = (
    (0xFF08, 0xFF09),
    (0x201C, 0x201D),
    (0x300C, 0x300D),
    (0x300A, 0x300B),
)


def source_path(
    package: str,
    part: str,
    weight: int,
    variable_source: bool,
) -> Path:
    if variable_source:
        filename = f"{package}-{part}-wght-normal.woff2"
        root = VARIABLE_FONT_ROOT
    else:
        filename = f"{package}-{part}-{weight}-normal.woff2"
        root = STATIC_FONT_ROOT
    path = root / package / "files" / filename
    if not path.is_file():
        source_type = "variable" if variable_source else "static"
        raise FileNotFoundError(
            f"Missing {source_type} Fontsource input: {path}"
        )
    return path


def extrapolate_value(light: int, regular: int) -> int:
    """Extrapolate a 100 value from compatible 200 and 300 masters."""
    return round(2 * light - regular)


def round_half_up(value: float) -> int:
    """Round a coordinate consistently when it lands on a half unit."""
    return floor(value + 0.5)


def extrapolate_glyph(
    light_font: TTFont,
    light_name: str,
    regular_font: TTFont,
    regular_name: str,
):
    """Return a Thin glyph extrapolated from compatible 200/300 outlines."""
    light_glyf = light_font["glyf"]
    regular_glyf = regular_font["glyf"]
    light = light_glyf[light_name]
    regular = regular_glyf[regular_name]
    expand_simple_glyph(light, light_glyf)
    expand_simple_glyph(regular, regular_glyf)
    if (
        light.numberOfContours != regular.numberOfContours
        or light.endPtsOfContours != regular.endPtsOfContours
        or len(light.coordinates) != len(regular.coordinates)
        or [flag & 1 for flag in light.flags]
        != [flag & 1 for flag in regular.flags]
    ):
        raise ValueError(
            f"Incompatible Serif 200/300 outlines for {light_name}"
        )

    glyph = deepcopy(light)
    for index, ((light_x, light_y), (regular_x, regular_y)) in enumerate(
        zip(light.coordinates, regular.coordinates)
    ):
        glyph.coordinates[index] = (
            extrapolate_value(light_x, regular_x),
            extrapolate_value(light_y, regular_y),
        )
    glyph.recalcBounds(light_glyf)
    return glyph


def halt_values(font: TTFont) -> dict[str, tuple[int, int]]:
    """Return cumulative (x placement, x advance) values from GPOS halt."""
    gpos = font["GPOS"].table
    feature = next(
        record
        for record in gpos.FeatureList.FeatureRecord
        if record.FeatureTag == "halt"
    )
    values: dict[str, list[int]] = {}

    for lookup_index in feature.Feature.LookupListIndex:
        lookup = gpos.LookupList.Lookup[lookup_index]
        if lookup.LookupType != 1:
            raise ValueError(f"Unsupported halt lookup type: {lookup.LookupType}")

        for positioning in lookup.SubTable:
            if positioning.Format == 1:
                records = [positioning.Value] * len(positioning.Coverage.glyphs)
            elif positioning.Format == 2:
                records = positioning.Value
            else:
                raise ValueError(f"Unsupported SinglePos format: {positioning.Format}")

            for glyph_name, record in zip(positioning.Coverage.glyphs, records):
                current = values.setdefault(glyph_name, [0, 0])
                current[0] += getattr(record, "XPlacement", 0) or 0
                current[1] += getattr(record, "XAdvance", 0) or 0

    return {glyph: (value[0], value[1]) for glyph, value in values.items()}


def expand_simple_glyph(glyph, glyf) -> None:
    if glyph.isComposite():
        raise ValueError("Unexpected composite punctuation glyph")
    glyph.expand(glyf)


def shift_glyph(
    glyph,
    glyf,
    x_distance: int = 0,
    y_distance: int = 0,
) -> None:
    if not x_distance and not y_distance:
        return
    expand_simple_glyph(glyph, glyf)
    if glyph.numberOfContours:
        for index, (x, y) in enumerate(glyph.coordinates):
            glyph.coordinates[index] = (
                x + x_distance,
                y + y_distance,
            )
        glyph.recalcBounds(glyf)


def outline_bounds(
    glyph,
    glyf,
) -> tuple[float, float, float, float]:
    """Return actual ink bounds, excluding non-extremal curve controls."""
    pen = BoundsPen(None)
    glyph.draw(pen, glyf)
    if pen.bounds is None:
        raise ValueError("Glyph has no outline bounds")
    return pen.bounds


def fit_dash_to_em(
    glyph,
    glyf,
    units_per_em: int,
    target_center_sum: int,
    pair_side_bearing: int,
) -> None:
    """Center a dash with half the final pair's side bearing in each 1-em cell."""
    expand_simple_glyph(glyph, glyf)
    glyph.recalcBounds(glyf)
    ink_width = glyph.xMax - glyph.xMin
    if ink_width <= 0:
        raise ValueError("Em dash has no horizontal ink extent")

    x_min = glyph.xMin
    y_shift = round_half_up(
        (target_center_sum - glyph.yMin - glyph.yMax) / 2
    )
    single_side_bearing = round(pair_side_bearing / 2)
    target_width = units_per_em - single_side_bearing * 2
    for index, (x, y) in enumerate(glyph.coordinates):
        stretched_x = single_side_bearing + round(
            (x - x_min) * target_width / ink_width
        )
        glyph.coordinates[index] = (stretched_x, y + y_shift)
    glyph.recalcBounds(glyf)


def double_dash_glyph(
    glyph,
    glyf,
    units_per_em: int,
    side_bearing: int,
):
    """Return a continuous two-em outline with fixed outer side space."""
    pair = deepcopy(glyph)
    expand_simple_glyph(pair, glyf)
    for index, (x, y) in enumerate(pair.coordinates):
        pair.coordinates[index] = (x * 2, y)
    pair.recalcBounds(glyf)
    ink_width = pair.xMax - pair.xMin
    target_width = units_per_em * 2 - side_bearing * 2
    x_min = pair.xMin
    for index, (x, y) in enumerate(pair.coordinates):
        pair.coordinates[index] = (
            side_bearing + round((x - x_min) * target_width / ink_width),
            y,
        )
    pair.recalcBounds(glyf)
    return pair


def bracket_side_bearing(glyphs, mapping: dict[int, str], half_em: int) -> int:
    """Average the outward side bearings of representative bracket pairs."""
    bearings = []
    for opening, closing in BRACKET_SIDE_REFERENCES:
        opening_glyph = glyphs[mapping[opening]]
        closing_glyph = glyphs[mapping[closing]]
        bearings.append(opening_glyph.xMin)
        bearings.append(half_em - closing_glyph.xMax)
    return round(sum(bearings) / len(bearings))


def build_cmap(mapping: dict[int, str]):
    cmap = newTable("cmap")
    cmap.tableVersion = 0
    cmap.tables = []
    subtable = CmapSubtable.newSubtable(4)
    subtable.platformID = 3
    subtable.platEncID = 1
    subtable.language = 0
    subtable.cmap = mapping
    cmap.tables.append(subtable)

    unicode_subtable = CmapSubtable.newSubtable(4)
    unicode_subtable.platformID = 0
    unicode_subtable.platEncID = 3
    unicode_subtable.language = 0
    unicode_subtable.cmap = mapping.copy()
    cmap.tables.append(unicode_subtable)
    return cmap


def set_font_identity(font: TTFont, style: str, weight: int | None) -> None:
    """Set family identity, legal metadata, and static weight bits."""
    family = FAMILY_NAMES[style]
    postscript_family = POSTSCRIPT_FAMILY_NAMES[style]
    subfamily = WEIGHT_NAMES[weight] if weight is not None else "Regular"
    postscript_name = (
        f"{postscript_family}-{subfamily}"
        if weight is not None
        else postscript_family
    )
    full_name = family if weight is None else f"{family} {subfamily}"
    unique_id = f"1.100;Kaiming;{postscript_name}"
    copyright_notice = (
        f"{SOURCE_COPYRIGHTS[style]} {MODIFICATION_COPYRIGHT}"
    )

    if weight in (None, 400, 700):
        legacy_family = family
        legacy_subfamily = subfamily
    else:
        legacy_family = f"{family} {subfamily}"
        legacy_subfamily = "Regular"

    name_table = font["name"]
    # varLib allocates name IDs >= 256 for axes and named instances. Keep them
    # when setting the variable font's public identity.
    name_table.names = [
        record for record in name_table.names if record.nameID >= 256
    ]
    values = {
        0: copyright_notice,
        1: legacy_family,
        2: legacy_subfamily,
        3: unique_id,
        4: full_name,
        5: "Version 1.100",
        6: postscript_name,
        13: OFL_DESCRIPTION,
        14: OFL_URL,
        16: family,
        17: subfamily,
    }
    if weight is None:
        values[25] = postscript_family
    for name_id, value in values.items():
        name_table.setName(value, name_id, 3, 1, 0x0409)
        name_table.setName(value, name_id, 0, 4, 0)

    chinese_family = CHINESE_FAMILY_NAMES[style]
    chinese_subfamily = CHINESE_WEIGHT_NAMES[weight or 400]
    chinese_full_name = (
        chinese_family
        if weight is None
        else f"{chinese_family} {chinese_subfamily}"
    )
    if weight in (None, 400, 700):
        chinese_legacy_family = chinese_family
        chinese_legacy_subfamily = chinese_subfamily
    else:
        chinese_legacy_family = chinese_full_name
        chinese_legacy_subfamily = CHINESE_WEIGHT_NAMES[400]
    chinese_values = {
        1: chinese_legacy_family,
        2: chinese_legacy_subfamily,
        4: chinese_full_name,
        16: chinese_family,
        17: chinese_subfamily,
    }
    for name_id, value in chinese_values.items():
        name_table.addMultilingualName(
            {"zh": value},
            ttFont=font,
            nameID=name_id,
            windows=True,
            mac=True,
        )

    effective_weight = weight or 400
    os2 = font["OS/2"]
    os2.usWeightClass = effective_weight
    os2.fsSelection &= ~((1 << 0) | (1 << 5) | (1 << 6))
    if effective_weight >= 700:
        os2.fsSelection |= 1 << 5
    elif effective_weight == 400:
        os2.fsSelection |= 1 << 6

    font["head"].macStyle &= ~0b11
    if effective_weight >= 700:
        font["head"].macStyle |= 1
    font["post"].italicAngle = 0


def feature_source(
    mapping: dict[int, str],
    dash_pair_name: str,
    half_em: int,
) -> str:
    lines = [
        "languagesystem DFLT dflt;",
        "feature halt {",
    ]
    for full_stop in sorted(FULL_STOPS):
        lines.append(f"  pos {mapping[full_stop]} <0 0 -{half_em} 0>;")
    lines.extend(
        [
            "} halt;",
            "feature ccmp {",
            f"  sub {mapping[0x2014]} {mapping[0x2014]} by {dash_pair_name};",
            "} ccmp;",
            "feature kern {",
        ]
    )

    full_stops = " ".join(
        mapping[codepoint] for codepoint in sorted(FULL_STOPS)
    )
    lines.extend(
        (
            f"  @full_stops = [{full_stops}];",
            f"  pos @full_stops @full_stops -{half_em};",
            "} kern;",
        )
    )
    return "\n".join(lines)


def build_processed_font(
    style: str,
    package: str,
    weight: int,
    variable_source: bool,
) -> TTFont:
    """Build one processed master from the requested Fontsource package type."""
    fonts: dict[str, tuple[TTFont, ...]] = {}
    sources: dict[int, tuple[tuple[TTFont, str], ...]] = {}

    # Noto Serif SC has no upstream Thin master. Derive a real, distinct Thin
    # outline by linear extrapolation from its compatible 200 and 300 masters.
    # Static and variable builds deliberately use their own package type here.
    source_weights = (
        (200, 300) if style == "serif" and weight == 100 else (weight,)
    )

    for part, codepoints in SOURCE_PARTS.items():
        part_fonts = []
        for source_weight in source_weights:
            source = TTFont(
                source_path(
                    package,
                    part,
                    source_weight,
                    variable_source,
                ),
                recalcBBoxes=True,
            )
            if variable_source:
                source = instantiateVariableFont(
                    source,
                    {"wght": source_weight},
                    inplace=False,
                    optimize=True,
                )
            part_fonts.append(source)
        fonts[part] = tuple(part_fonts)
        cmaps = [font.getBestCmap() for font in part_fonts]
        for codepoint in codepoints:
            sources[codepoint] = tuple(
                (font, cmap[codepoint])
                for font, cmap in zip(part_fonts, cmaps)
            )

    base_fonts = fonts["119"]
    base = base_fonts[0]
    units_per_em = base["head"].unitsPerEm
    half_em = units_per_em // 2
    glyph_order = [".notdef"]
    if len(base_fonts) == 2:
        glyphs = {
            ".notdef": extrapolate_glyph(
                base_fonts[0], ".notdef", base_fonts[1], ".notdef"
            )
        }
        light_metric = base_fonts[0]["hmtx"].metrics[".notdef"]
        regular_metric = base_fonts[1]["hmtx"].metrics[".notdef"]
        metrics = {
            ".notdef": tuple(
                extrapolate_value(light, regular)
                for light, regular in zip(light_metric, regular_metric)
            )
        }
    else:
        glyphs = {".notdef": deepcopy(base["glyf"][".notdef"])}
        metrics = {".notdef": base["hmtx"].metrics[".notdef"]}
    mapping: dict[int, str] = {}
    halt_cache: dict[int, dict[str, tuple[int, int]]] = {}

    reference_names = tuple(
        font.getBestCmap()[0x4E2D] for font in base_fonts
    )
    if len(base_fonts) == 2:
        reference_glyph = extrapolate_glyph(
            base_fonts[0],
            reference_names[0],
            base_fonts[1],
            reference_names[1],
        )
    else:
        reference_glyph = base["glyf"][reference_names[0]]
        reference_glyph.recalcBounds(base["glyf"])
    # Use one integer visual axis for every centered mark. Normalizing the
    # doubled center to an even value prevents glyphs with different bound
    # parity from rounding to opposite sides of a half-unit CJK center.
    reference_center_sum = round(
        (reference_glyph.yMin + reference_glyph.yMax) / 2
    ) * 2

    for codepoint in sorted(ALL_CODEPOINTS):
        source_codepoint = SYNTHETIC_SOURCES.get(codepoint, codepoint)
        source_records = sources[source_codepoint]
        source_font, source_name = source_records[0]
        glyf = source_font["glyf"]
        if (
            len(source_records) == 2
            and codepoint not in SPACE_ADVANCE_DIVISORS
        ):
            regular_font, regular_name = source_records[1]
            glyph = extrapolate_glyph(
                source_font,
                source_name,
                regular_font,
                regular_name,
            )
            light_metric = source_font["hmtx"].metrics[source_name]
            regular_metric = regular_font["hmtx"].metrics[regular_name]
            width, lsb = (
                extrapolate_value(light, regular)
                for light, regular in zip(light_metric, regular_metric)
            )
        else:
            source_glyph = glyf[source_name]
            expand_simple_glyph(source_glyph, glyf)
            glyph = deepcopy(source_glyph)
            width, lsb = source_font["hmtx"].metrics[source_name]

        if codepoint in SPACE_ADVANCE_DIVISORS:
            if glyph.numberOfContours:
                raise ValueError(
                    f"U+{codepoint:04X} unexpectedly has a visible outline"
                )
            divisor = SPACE_ADVANCE_DIVISORS[codepoint]
            if units_per_em % divisor:
                raise ValueError(
                    f"{units_per_em} UPM is not divisible by {divisor}"
                )
            width = units_per_em // divisor
            lsb = 0
        elif codepoint in CENTERED_HALF_WIDTH:
            x_min, y_min, x_max, y_max = outline_bounds(glyph, glyf)
            x_placement = round(
                (half_em - x_min - x_max) / 2
            )
            y_placement = 0
            if codepoint in VERTICALLY_CENTERED_HALF_WIDTH:
                y_placement = round_half_up(
                    (reference_center_sum - y_min - y_max) / 2
                )
            shift_glyph(glyph, glyf, x_placement, y_placement)
            width = half_em
            lsb = glyph.xMin
        elif codepoint in HALF_WIDTH:
            source_halt_values = []
            for halt_font, halt_name in source_records:
                cache_key = id(halt_font)
                if cache_key not in halt_cache:
                    halt_cache[cache_key] = halt_values(halt_font)
                source_halt_values.append(halt_cache[cache_key][halt_name])
            if len(source_halt_values) == 2:
                x_placement, x_advance = (
                    extrapolate_value(light, regular)
                    for light, regular in zip(*source_halt_values)
                )
            else:
                x_placement, x_advance = source_halt_values[0]
            shift_glyph(glyph, glyf, x_placement)
            width += x_advance
            lsb += x_placement
            if width != half_em:
                raise ValueError(
                    f"U+{codepoint:04X} became {width}; expected {half_em}"
                )
        elif codepoint == 0x2014:
            width = units_per_em
            lsb = 0
        elif codepoint in FULL_STOPS | {0x2026} and width != units_per_em:
            raise ValueError(
                f"U+{codepoint:04X} has width {width}; expected {units_per_em}"
            )

        glyph_name = f"u{codepoint:04X}"
        glyph_order.append(glyph_name)
        glyphs[glyph_name] = glyph
        metrics[glyph_name] = (width, lsb)
        mapping[codepoint] = glyph_name

    dash_name = mapping[0x2014]
    dash_glyph = glyphs[dash_name]
    dash_side_bearing = bracket_side_bearing(glyphs, mapping, half_em)
    fit_dash_to_em(
        dash_glyph,
        base["glyf"],
        units_per_em,
        reference_center_sum,
        dash_side_bearing,
    )
    metrics[dash_name] = (units_per_em, dash_glyph.xMin)

    dash_pair_name = "emDash_pair"
    if units_per_em % DASH_PAIR_SIDE_BEARING_DIVISOR:
        raise ValueError(
            f"{units_per_em} UPM is not divisible by "
            f"{DASH_PAIR_SIDE_BEARING_DIVISOR}"
        )
    dash_pair_side_bearing = (
        units_per_em // DASH_PAIR_SIDE_BEARING_DIVISOR
    )
    dash_pair = double_dash_glyph(
        dash_glyph,
        base["glyf"],
        units_per_em,
        dash_pair_side_bearing,
    )
    glyph_order.append(dash_pair_name)
    glyphs[dash_pair_name] = dash_pair
    metrics[dash_pair_name] = (units_per_em * 2, dash_pair.xMin)

    base.flavor = None
    base.setGlyphOrder(glyph_order)
    base["glyf"].glyphs = glyphs
    base["hmtx"].metrics = metrics
    base["cmap"] = build_cmap(mapping)
    base["maxp"].numGlyphs = len(glyph_order)
    base["hhea"].numberOfHMetrics = len(glyph_order)
    base["OS/2"].usFirstCharIndex = min(mapping)
    base["OS/2"].usLastCharIndex = max(mapping)

    for table in (
        "BASE",
        "GDEF",
        "GPOS",
        "GSUB",
        "HVAR",
        "STAT",
        "avar",
        "fvar",
        "gvar",
        "vhea",
        "vmtx",
    ):
        if table in base:
            del base[table]

    addOpenTypeFeaturesFromString(
        base, feature_source(mapping, dash_pair_name, half_em)
    )
    set_font_identity(base, style, weight)
    return base


def convert_to_cff(font: TTFont, style: str, weight: int) -> TTFont:
    """Convert a processed TrueType master to a genuine CFF-flavored OTF."""
    glyph_order = font.getGlyphOrder()
    glyph_set = font.getGlyphSet()
    char_strings = {}

    for glyph_name in glyph_order:
        width = font["hmtx"].metrics[glyph_name][0]
        pen = T2CharStringPen(
            width,
            glyph_set,
            roundTolerance=0.0,
        )
        glyph_set[glyph_name].draw(pen)
        char_strings[glyph_name] = pen.getCharString(optimize=True)

    family = FAMILY_NAMES[style]
    subfamily = WEIGHT_NAMES[weight]
    postscript_name = f"{POSTSCRIPT_FAMILY_NAMES[style]}-{subfamily}"
    copyright_notice = (
        f"{SOURCE_COPYRIGHTS[style]} {MODIFICATION_COPYRIGHT}"
    )
    builder = FontBuilder(font["head"].unitsPerEm, isTTF=False)
    builder.setupGlyphOrder(glyph_order)
    builder.setupCFF(
        postscript_name,
        {
            "version": "1.100",
            "FullName": f"{family} {subfamily}",
            "FamilyName": family,
            "Weight": subfamily,
            "Copyright": copyright_notice,
            "Notice": OFL_DESCRIPTION,
        },
        char_strings,
        {},
    )

    for table in ("glyf", "loca", "prep", "gasp"):
        if table in font:
            del font[table]
    font["CFF "] = builder.font["CFF "]
    font["maxp"] = builder.font["maxp"]
    font.sfntVersion = "OTTO"
    font["post"].formatType = 3.0
    return font


def build_variable(style: str, masters: dict[int, TTFont]) -> TTFont:
    """Build a piecewise-linear variable font from all processed masters."""
    family = FAMILY_NAMES[style]
    designspace = DesignSpaceDocument()
    designspace.addAxis(
        AxisDescriptor(
            tag="wght",
            name="Weight",
            minimum=min(WEIGHTS),
            default=400,
            maximum=max(WEIGHTS),
            labelNames={"en": "Weight"},
        )
    )

    for weight, font in masters.items():
        designspace.addSource(
            SourceDescriptor(
                name=f"master.{style}.{weight}",
                font=font,
                location={"Weight": weight},
                familyName=family,
                styleName=WEIGHT_NAMES[weight],
                copyInfo=weight == 400,
                copyLib=weight == 400,
                copyFeatures=weight == 400,
            )
        )
        designspace.addInstance(
            InstanceDescriptor(
                name=f"instance.{style}.{weight}",
                familyName=family,
                styleName=WEIGHT_NAMES[weight],
                postScriptFontName=(
                    f"{POSTSCRIPT_FAMILY_NAMES[style]}-"
                    f"{WEIGHT_NAMES[weight]}"
                ),
                location={"Weight": weight},
            )
        )

    variable = build_variable_font(designspace)[0]
    set_font_identity(variable, style, None)
    for instance in variable["fvar"].instances:
        weight = int(instance.coordinates["wght"])
        variable["name"].addMultilingualName(
            {"zh": CHINESE_WEIGHT_NAMES[weight]},
            ttFont=variable,
            nameID=instance.subfamilyNameID,
            windows=True,
            mac=True,
        )
    stat_values = []
    for weight in WEIGHTS:
        value = {
            "value": weight,
            "name": {
                "en": WEIGHT_NAMES[weight],
                "zh": CHINESE_WEIGHT_NAMES[weight],
            },
        }
        if weight == 400:
            value.update(flags=0x2, linkedValue=700)
        stat_values.append(value)
    buildStatTable(
        variable,
        [
            {
                "tag": "wght",
                "name": {"en": "Weight", "zh": "字重"},
                "ordering": 0,
                "values": stat_values,
            }
        ],
        elidedFallbackName={"en": "Regular", "zh": "常规"},
    )
    return variable


def save_font(font: TTFont, output: Path, flavor: str | None = None) -> Path:
    # Preserve the source epoch instead of inserting the wall-clock build time.
    # This makes committed fonts and release archives reproducible in CI.
    font.recalcTimestamp = False
    font.flavor = flavor
    font.save(output, reorderTables=True)
    font.flavor = None
    return output


def pair_values(font: TTFont, left: str, right: str) -> tuple[int, int, int, int]:
    """Return (place1, advance1, place2, advance2) from generated kern."""
    gpos = font["GPOS"].table
    feature = next(
        record
        for record in gpos.FeatureList.FeatureRecord
        if record.FeatureTag == "kern"
    )
    totals = [0, 0, 0, 0]

    for lookup_index in feature.Feature.LookupListIndex:
        for positioning in gpos.LookupList.Lookup[lookup_index].SubTable:
            if left not in positioning.Coverage.glyphs:
                continue

            record = None
            if positioning.Format == 1:
                coverage_index = positioning.Coverage.glyphs.index(left)
                pair_set = positioning.PairSet[coverage_index]
                record = next(
                    (
                        candidate
                        for candidate in pair_set.PairValueRecord
                        if candidate.SecondGlyph == right
                    ),
                    None,
                )
            elif positioning.Format == 2:
                class1 = positioning.ClassDef1.classDefs.get(left, 0)
                class2 = positioning.ClassDef2.classDefs.get(right, 0)
                record = positioning.Class1Record[class1].Class2Record[class2]

            if record is None:
                continue

            value1 = getattr(record, "Value1", None)
            value2 = getattr(record, "Value2", None)
            totals[0] += getattr(value1, "XPlacement", 0) or 0
            totals[1] += getattr(value1, "XAdvance", 0) or 0
            totals[2] += getattr(value2, "XPlacement", 0) or 0
            totals[3] += getattr(value2, "XAdvance", 0) or 0

    return tuple(totals)


def glyph_ink_bounds(
    font: TTFont,
    glyph_name: str,
) -> tuple[float, float, float, float]:
    glyph_set = font.getGlyphSet()
    pen = BoundsPen(glyph_set)
    glyph_set[glyph_name].draw(pen)
    if pen.bounds is None:
        raise ValueError(f"{glyph_name} has no outline bounds")
    return pen.bounds


def glyph_bounds(font: TTFont, glyph_name: str) -> tuple[float, float]:
    bounds = glyph_ink_bounds(font, glyph_name)
    return bounds[0], bounds[2]


def ligature_glyph(font: TTFont, feature_tag: str, first: str, second: str) -> str:
    """Return the output glyph for a two-glyph ligature substitution."""
    gsub = font["GSUB"].table
    feature = next(
        record
        for record in gsub.FeatureList.FeatureRecord
        if record.FeatureTag == feature_tag
    )
    for lookup_index in feature.Feature.LookupListIndex:
        lookup = gsub.LookupList.Lookup[lookup_index]
        if lookup.LookupType != 4:
            continue
        for substitution in lookup.SubTable:
            for ligature in substitution.ligatures.get(first, []):
                if ligature.Component == [second]:
                    return ligature.LigGlyph
    raise ValueError(f"Missing {feature_tag} ligature for {first} {second}")


def verify_legal_metadata(font: TTFont, label: str, style: str) -> None:
    expected = {
        0: f"{SOURCE_COPYRIGHTS[style]} {MODIFICATION_COPYRIGHT}",
        13: OFL_DESCRIPTION,
        14: OFL_URL,
    }
    for name_id, value in expected.items():
        for platform_id in (0, 3):
            values = {
                record.toUnicode()
                for record in font["name"].names
                if record.nameID == name_id
                and record.platformID == platform_id
            }
            if value not in values:
                raise ValueError(
                    f"{label}: platform {platform_id} nameID {name_id} "
                    f"is missing {value!r}"
                )

    for platform_id in (0, 3):
        family_names = {
            record.toUnicode()
            for record in font["name"].names
            if record.nameID == 16 and record.platformID == platform_id
            and (platform_id != 3 or record.langID == 0x0409)
        }
        if family_names != {FAMILY_NAMES[style]}:
            raise ValueError(
                f"{label}: platform {platform_id} has incorrect "
                f"typographic family names: {family_names}"
            )
        postscript_names = {
            record.toUnicode()
            for record in font["name"].names
            if record.nameID == 6 and record.platformID == platform_id
        }
        if not postscript_names or any(
            not name.startswith(POSTSCRIPT_FAMILY_NAMES[style])
            for name in postscript_names
        ):
            raise ValueError(
                f"{label}: platform {platform_id} has incorrect "
                f"PostScript names: {postscript_names}"
            )

    weight = None if "fvar" in font else font["OS/2"].usWeightClass
    chinese_family = CHINESE_FAMILY_NAMES[style]
    chinese_subfamily = CHINESE_WEIGHT_NAMES[weight or 400]
    chinese_full_name = (
        chinese_family
        if weight is None
        else f"{chinese_family} {chinese_subfamily}"
    )
    if weight in (None, 400, 700):
        chinese_legacy_family = chinese_family
        chinese_legacy_subfamily = chinese_subfamily
    else:
        chinese_legacy_family = chinese_full_name
        chinese_legacy_subfamily = CHINESE_WEIGHT_NAMES[400]
    expected_chinese = {
        1: chinese_legacy_family,
        2: chinese_legacy_subfamily,
        4: chinese_full_name,
        16: chinese_family,
        17: chinese_subfamily,
    }
    for name_id, expected_value in expected_chinese.items():
        values = {
            record.toUnicode()
            for record in font["name"].names
            if record.nameID == name_id
            and record.platformID == 3
            and record.langID == 0x0804
        }
        if values != {expected_value}:
            raise ValueError(
                f"{label}: Simplified Chinese nameID {name_id} "
                f"is {values}, expected {expected_value!r}"
            )


def glyf_outline_signature(font: TTFont) -> tuple:
    cmap = font.getBestCmap()
    glyf = font["glyf"]
    signatures = []
    for codepoint in sorted(ALL_CODEPOINTS):
        glyph = glyf[cmap[codepoint]]
        expand_simple_glyph(glyph, glyf)
        if glyph.numberOfContours:
            coordinates = tuple(glyph.coordinates)
            end_points = tuple(glyph.endPtsOfContours)
            flags = tuple(flag & 1 for flag in glyph.flags)
        else:
            coordinates = ()
            end_points = ()
            flags = ()
        signatures.append(
            (
                codepoint,
                coordinates,
                end_points,
                flags,
            )
        )
    return tuple(signatures)


def verify_serif_thin_is_distinct() -> None:
    """Ensure the derived Serif Thin is not a relabeled ExtraLight."""
    static_thin = TTFont(STATIC_WOFF2_ROOT / "kaiming-serif-100.woff2")
    static_extra_light = TTFont(
        STATIC_WOFF2_ROOT / "kaiming-serif-200.woff2"
    )
    if glyf_outline_signature(static_thin) == glyf_outline_signature(
        static_extra_light
    ):
        raise ValueError("Static Serif 100 and 200 outlines are identical")

    variable = TTFont(VARIABLE_ROOT / "kaiming-serif-variable.ttf")
    variable_thin = instantiateVariableFont(
        variable, {"wght": 100}, inplace=False, optimize=True
    )
    variable_extra_light = instantiateVariableFont(
        variable, {"wght": 200}, inplace=False, optimize=True
    )
    if glyf_outline_signature(variable_thin) == glyf_outline_signature(
        variable_extra_light
    ):
        raise ValueError("Variable Serif 100 and 200 outlines are identical")


def bracket_side_bearing_from_font(
    font: TTFont,
    mapping: dict[int, str],
    half_em: int,
) -> float:
    bearings = []
    for opening, closing in BRACKET_SIDE_REFERENCES:
        opening_min, _ = glyph_bounds(font, mapping[opening])
        _, closing_max = glyph_bounds(font, mapping[closing])
        bearings.extend((opening_min, half_em - closing_max))
    return round(sum(bearings) / len(bearings))


def verify_layout(
    font: TTFont,
    label: str,
    centered_tolerance: float = 1.01,
) -> None:
    cmap = font.getBestCmap()
    if set(cmap) != ALL_CODEPOINTS:
        raise ValueError(f"{label}: cmap does not match the configured set")

    units_per_em = font["head"].unitsPerEm
    half_em = units_per_em // 2

    for codepoint, glyph_name in cmap.items():
        width = font["hmtx"].metrics[glyph_name][0]
        if codepoint in SPACE_ADVANCE_DIVISORS:
            expected = units_per_em // SPACE_ADVANCE_DIVISORS[codepoint]
        else:
            expected = half_em if codepoint in HALF_WIDTH else units_per_em
        if width != expected:
            raise ValueError(
                f"{label}: U+{codepoint:04X} has width {width}, "
                f"expected {expected}"
            )

    glyph_set = font.getGlyphSet()
    for codepoint in SPACE_ADVANCE_DIVISORS:
        pen = BoundsPen(glyph_set)
        glyph_set[cmap[codepoint]].draw(pen)
        if pen.bounds is not None:
            raise ValueError(
                f"{label}: U+{codepoint:04X} has a visible outline"
            )

    for codepoint in CENTERED_HALF_WIDTH:
        x_min, x_max = glyph_bounds(font, cmap[codepoint])
        # Variable curve interpolation can move an extremum by a few font
        # units even when all compatible masters share the same center axis.
        if abs(x_min + x_max - half_em) > centered_tolerance:
            raise ValueError(
                f"{label}: U+{codepoint:04X} is not centered in its "
                f"half-em advance: bounds={x_min}..{x_max}"
            )

    _, dash_y_min, _, dash_y_max = glyph_ink_bounds(font, cmap[0x2014])
    vertical_center_sum = dash_y_min + dash_y_max
    for codepoint in VERTICALLY_CENTERED_HALF_WIDTH:
        _, y_min, _, y_max = glyph_ink_bounds(font, cmap[codepoint])
        if abs(y_min + y_max - vertical_center_sum) > centered_tolerance:
            raise ValueError(
                f"{label}: U+{codepoint:04X} is not vertically centered "
                f"on the CJK visual axis: bounds={y_min}..{y_max}"
            )

    for closing in CLOSING:
        close_name = cmap[closing]
        _, close_x_max = glyph_bounds(font, close_name)
        for opening in OPENING:
            open_name = cmap[opening]
            open_x_min, _ = glyph_bounds(font, open_name)
            place1, advance1, place2, advance2 = pair_values(
                font, close_name, open_name
            )
            pair_width = units_per_em + advance1 + advance2
            ink_gap = half_em + advance1 + open_x_min + place2 - (
                close_x_max + place1
            )
            if pair_width != units_per_em or ink_gap <= 0:
                raise ValueError(
                    f"{label}: U+{closing:04X} U+{opening:04X}: "
                    f"width={pair_width}, ink_gap={ink_gap}"
                )

    generated_halt = halt_values(font)
    for full_stop in FULL_STOPS:
        halt = generated_halt.get(cmap[full_stop])
        if halt != (0, -half_em):
            raise ValueError(
                f"{label}: U+{full_stop:04X} halt={halt}, "
                f"expected (0, -{half_em})"
            )

    for first in FULL_STOPS:
        for second in FULL_STOPS:
            values = pair_values(font, cmap[first], cmap[second])
            pair_width = units_per_em * 2 + values[1] + values[3]
            expected_width = units_per_em + half_em
            if pair_width != expected_width:
                raise ValueError(
                    f"{label}: U+{first:04X} U+{second:04X}: "
                    f"{pair_width}, expected {expected_width}"
                )

    expected_pair_side = bracket_side_bearing_from_font(font, cmap, half_em)
    expected_single_side = round(expected_pair_side / 2)
    dash_min, dash_max = glyph_bounds(font, cmap[0x2014])
    if (
        abs(dash_min - expected_single_side) > 2
        or abs(dash_max - (units_per_em - expected_single_side)) > 2
    ):
        raise ValueError(
            f"{label}: em dash side bearings do not match brackets: "
            f"{dash_min}..{dash_max}, reference={expected_pair_side}"
        )

    dash_name = cmap[0x2014]
    dash_pair_name = ligature_glyph(font, "ccmp", dash_name, dash_name)
    dash_pair_width = font["hmtx"].metrics[dash_pair_name][0]
    dash_pair_min, dash_pair_max = glyph_bounds(font, dash_pair_name)
    dash_pair_side_bearing = (
        units_per_em // DASH_PAIR_SIDE_BEARING_DIVISOR
    )
    if (
        dash_pair_width != units_per_em * 2
        or abs(dash_pair_min - dash_pair_side_bearing) > 4
        or abs(
            dash_pair_max - (units_per_em * 2 - dash_pair_side_bearing)
        ) > 4
    ):
        raise ValueError(
            f"{label}: em-dash ligature width={dash_pair_width}, "
            f"bounds={dash_pair_min}..{dash_pair_max}"
        )

    for long_mark in LONG_MARKS:
        glyph_name = cmap[long_mark]
        values = pair_values(font, glyph_name, glyph_name)
        pair_width = units_per_em * 2 + values[1] + values[3]
        if pair_width != units_per_em * 2:
            raise ValueError(
                f"{label}: U+{long_mark:04X} pair is {pair_width}, "
                f"expected {units_per_em * 2}"
            )


def verify(output: Path, style: str, variable: bool) -> None:
    font = TTFont(output)
    verify_legal_metadata(font, output.name, style)

    if output.suffix == ".otf":
        expected_table = "CFF2" if variable else "CFF "
        if font.sfntVersion != "OTTO" or expected_table not in font:
            raise ValueError(
                f"{output.name}: expected a genuine {expected_table.strip()} OTF"
            )
    elif output.suffix == ".woff2":
        if font.flavor != "woff2" or "glyf" not in font:
            raise ValueError(f"{output.name}: expected a TrueType WOFF2")
    elif output.suffix == ".ttf":
        if font.sfntVersion != "\x00\x01\x00\x00" or "glyf" not in font:
            raise ValueError(f"{output.name}: expected a TrueType font")

    if variable:
        if "fvar" not in font:
            raise ValueError(f"{output.name}: missing fvar table")
        axes = font["fvar"].axes
        if len(axes) != 1 or (
            axes[0].axisTag,
            axes[0].minValue,
            axes[0].defaultValue,
            axes[0].maxValue,
        ) != ("wght", 100, 400, 900):
            raise ValueError(f"{output.name}: unexpected variable axis")
        if len(font["fvar"].instances) != len(WEIGHTS):
            raise ValueError(f"{output.name}: missing named weight instances")
        instance_coordinates = {
            int(instance.coordinates["wght"])
            for instance in font["fvar"].instances
        }
        if instance_coordinates != set(WEIGHTS):
            raise ValueError(f"{output.name}: incorrect named instance coordinates")
        postscript_name_ids = {
            instance.postscriptNameID for instance in font["fvar"].instances
        }
        if 0xFFFF in postscript_name_ids or len(postscript_name_ids) != len(WEIGHTS):
            raise ValueError(
                f"{output.name}: named instances need distinct PostScript names"
            )
        for instance in font["fvar"].instances:
            weight = int(instance.coordinates["wght"])
            chinese_names = {
                record.toUnicode()
                for record in font["name"].names
                if record.nameID == instance.subfamilyNameID
                and record.platformID == 3
                and record.langID == 0x0804
            }
            if chinese_names != {CHINESE_WEIGHT_NAMES[weight]}:
                raise ValueError(
                    f"{output.name}: fvar {weight} has incorrect "
                    f"Chinese name {chinese_names}"
                )

        stat = font["STAT"].table
        axis_name_id = stat.DesignAxisRecord.Axis[0].AxisNameID
        chinese_axis_names = {
            record.toUnicode()
            for record in font["name"].names
            if record.nameID == axis_name_id
            and record.platformID == 3
            and record.langID == 0x0804
        }
        if chinese_axis_names != {"字重"}:
            raise ValueError(
                f"{output.name}: STAT axis lacks Chinese Weight name"
            )
        axis_values = getattr(stat, "AxisValueArray", None)
        if axis_values is None or len(axis_values.AxisValue) != len(WEIGHTS):
            raise ValueError(f"{output.name}: STAT lacks weight AxisValue records")
        stat_weights = set()
        for axis_value in axis_values.AxisValue:
            value = int(axis_value.Value)
            stat_weights.add(value)
            names = {
                record.toUnicode()
                for record in font["name"].names
                if record.nameID == axis_value.ValueNameID
                and record.platformID == 3
            }
            if WEIGHT_NAMES[value] not in names:
                raise ValueError(
                    f"{output.name}: STAT {value} has incorrect name"
                )
            chinese_names = {
                record.toUnicode()
                for record in font["name"].names
                if record.nameID == axis_value.ValueNameID
                and record.platformID == 3
                and record.langID == 0x0804
            }
            if chinese_names != {CHINESE_WEIGHT_NAMES[value]}:
                raise ValueError(
                    f"{output.name}: STAT {value} has incorrect "
                    f"Chinese name {chinese_names}"
                )
            if value == 400 and (
                axis_value.Format != 3
                or axis_value.LinkedValue != 700
                or not axis_value.Flags & 0x2
            ):
                raise ValueError(
                    f"{output.name}: STAT Regular must link to Bold"
                )
        if stat_weights != set(WEIGHTS):
            raise ValueError(f"{output.name}: STAT weight values are incomplete")

        for weight in range(min(WEIGHTS), max(WEIGHTS) + 1, 50):
            instance = instantiateVariableFont(
                font,
                {"wght": weight},
                inplace=False,
                optimize=True,
            )
            verify_layout(
                instance,
                f"{output.name}@{weight}",
                centered_tolerance=5.01,
            )
    else:
        if "fvar" in font:
            raise ValueError(f"{output.name}: static font unexpectedly has fvar")
        verify_layout(font, output.name)


def main() -> None:
    for directory in (VARIABLE_ROOT, STATIC_OTF_ROOT, STATIC_WOFF2_ROOT):
        directory.mkdir(parents=True, exist_ok=True)
    outputs: list[tuple[Path, str, bool]] = []

    for style, package in FAMILIES.items():
        static_masters = {
            weight: build_processed_font(
                style, package, weight, variable_source=False
            )
            for weight in WEIGHTS
        }
        variable_masters = {
            weight: build_processed_font(
                style, package, weight, variable_source=True
            )
            for weight in WEIGHTS
        }
        variable_ttf = build_variable(style, variable_masters)

        for weight, font in static_masters.items():
            output = STATIC_WOFF2_ROOT / f"kaiming-{style}-{weight}.woff2"
            outputs.append((save_font(font, output, "woff2"), style, False))
        output = VARIABLE_ROOT / f"kaiming-{style}-variable.ttf"
        outputs.append((save_font(variable_ttf, output), style, True))
        output = VARIABLE_ROOT / f"kaiming-{style}-variable.woff2"
        outputs.append((save_font(variable_ttf, output, "woff2"), style, True))

        cff_masters = {
            weight: convert_to_cff(font, style, weight)
            for weight, font in static_masters.items()
        }
        variable_cff_masters = {
            weight: convert_to_cff(font, style, weight)
            for weight, font in variable_masters.items()
        }
        variable_cff = build_variable(style, variable_cff_masters)
        for weight, font in cff_masters.items():
            output = STATIC_OTF_ROOT / f"kaiming-{style}-{weight}.otf"
            outputs.append((save_font(font, output), style, False))
        output = VARIABLE_ROOT / f"kaiming-{style}-variable.otf"
        outputs.append((save_font(variable_cff, output), style, True))

    for output, style, variable in outputs:
        verify(output, style, variable)
    verify_serif_thin_is_distinct()

    expected = {output.resolve() for output, _, _ in outputs}
    for directory in (
        OUTPUT_ROOT,
        VARIABLE_ROOT,
        STATIC_OTF_ROOT,
        STATIC_WOFF2_ROOT,
    ):
        for old_output in directory.glob("kaiming-*.*"):
            if old_output.suffix not in (".otf", ".ttf", ".woff2"):
                continue
            if old_output.resolve() not in expected:
                old_output.unlink()

    total = sum(output.stat().st_size for output, _, _ in outputs)
    print(
        f"Built and verified {len(outputs)} OTF/TTF/WOFF2 files "
        f"({total / 1024:.1f} KiB)."
    )
    print("Every font contains copyright, OFL description, and license URL names.")
    print("Each family includes nine static weights and 100-900 variable fonts.")
    print("All closing-opening pairs are 1 em with positive contour gaps.")
    print("Fullwidth sentence stops expose a trailing 0.5-em halt adjustment.")
    print("Em-dash pairs are centered 2-em ligatures with 0.05-em side space.")


if __name__ == "__main__":
    main()
