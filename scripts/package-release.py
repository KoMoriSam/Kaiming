"""Create the three distributable Kaiming Punctuation ZIP archives."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]
FONT_ROOT = ROOT / "fonts"
DIST_ROOT = ROOT / "dist"
FAMILIES = ("sans", "serif")
WEIGHTS = tuple(range(100, 1000, 100))
VARIABLE_FORMATS = ("otf", "ttf", "woff2")

COMMON_FILES = (
    (ROOT / "README.md", Path("README.md")),
    (ROOT / "FONTLOG.txt", Path("FONTLOG.txt")),
    (ROOT / "LICENSES" / "OFL-1.1.txt", Path("LICENSES/OFL-1.1.txt")),
    # OFL.txt at the archive root follows the conventional OFL release layout.
    (ROOT / "LICENSES" / "OFL-1.1.txt", Path("OFL.txt")),
)

ARCHIVE_NAMES = (
    "KaimingPunctuation-VF.zip",
    "KaimingPunctuation-OTFs.zip",
    "KaimingPunctuation-WOFF2.zip",
)


def variable_fonts() -> list[Path]:
    return [
        FONT_ROOT / "variable" / f"kaiming-{family}-variable.{extension}"
        for family in FAMILIES
        for extension in VARIABLE_FORMATS
    ]


def static_fonts(extension: str) -> list[Path]:
    return [
        FONT_ROOT
        / "static"
        / extension
        / f"kaiming-{family}-{weight}.{extension}"
        for family in FAMILIES
        for weight in WEIGHTS
    ]


def with_common_files(
    font_paths: list[Path],
    extra_files: tuple[tuple[Path, Path], ...] = (),
) -> list[tuple[Path, Path]]:
    files = list(COMMON_FILES)
    files.extend(extra_files)
    # Each ZIP already represents one distribution category, so font files are
    # flattened to a single fonts/ directory inside that archive.
    files.extend((path, Path("fonts") / path.name) for path in font_paths)
    missing = [
        str(path.relative_to(ROOT))
        for path, _ in files
        if not path.is_file()
    ]
    if missing:
        raise SystemExit("Missing release files:\n- " + "\n- ".join(missing))
    return files


def release_archives() -> tuple[tuple[str, list[tuple[Path, Path]]], ...]:
    return (
        (
            ARCHIVE_NAMES[0],
            with_common_files(
                variable_fonts(),
                (
                    (
                        ROOT / "kaiming-punctuation-variable.css",
                        Path("kaiming-punctuation-variable.css"),
                    ),
                ),
            ),
        ),
        (
            ARCHIVE_NAMES[1],
            with_common_files(static_fonts("otf")),
        ),
        (
            ARCHIVE_NAMES[2],
            with_common_files(
                static_fonts("woff2"),
                (
                    (
                        ROOT / "kaiming-punctuation.css",
                        Path("kaiming-punctuation.css"),
                    ),
                ),
            ),
        ),
    )


def archive_timestamp() -> int:
    value = os.environ.get("SOURCE_DATE_EPOCH", "315532800")
    try:
        return max(int(value), 315532800)
    except ValueError as error:
        raise SystemExit("SOURCE_DATE_EPOCH must be an integer") from error


def write_zip(
    output: Path,
    root_name: str,
    files: list[tuple[Path, Path]],
    timestamp: int,
) -> None:
    date_time = datetime.fromtimestamp(
        timestamp,
        tz=timezone.utc,
    ).timetuple()[:6]
    with zipfile.ZipFile(
        output,
        "w",
        zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for source, relative in files:
            info = zipfile.ZipInfo(
                (Path(root_name) / relative).as_posix(),
                date_time=date_time,
            )
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            data = source.read_bytes()
            if relative.suffix == ".css":
                # The repository keeps build outputs in categorized folders,
                # while release ZIPs expose every included font as fonts/*.
                css = data.decode("utf-8")
                css = css.replace("./fonts/variable/", "./fonts/")
                css = css.replace("./fonts/static/woff2/", "./fonts/")
                data = css.encode("utf-8")
            archive.writestr(info, data, compresslevel=9)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    timestamp = archive_timestamp()
    DIST_ROOT.mkdir(parents=True, exist_ok=True)
    outputs = []
    for filename, files in release_archives():
        output = DIST_ROOT / filename
        write_zip(output, Path(filename).stem, files, timestamp)
        outputs.append(output)

    sums_path = DIST_ROOT / "SHA256SUMS"
    sums_path.write_text(
        "".join(f"{sha256(path)}  {path.name}\n" for path in outputs),
        encoding="utf-8",
        newline="\n",
    )
    for output in outputs:
        print(f"Created {output.relative_to(ROOT)}")
    print(f"Created {sums_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
