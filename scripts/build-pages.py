"""Stage Cloudflare static assets from verified variable-font outputs."""

from __future__ import annotations

from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "pages"
OUTPUT_ROOT = ROOT / "public"
VARIABLE_FONT_ROOT = ROOT / "fonts" / "variable"
PUBLIC_PREFIXES = (Path(), Path("kaiming"))

SITE_ASSETS = (
    (SOURCE_ROOT / "index.html", Path("index.html")),
    (ROOT / "index.css", Path("index.css")),
    (ROOT / "LICENSE", Path("LICENSE")),
)

FONT_ASSETS = tuple(
    (
        VARIABLE_FONT_ROOT / f"kaiming-{family}-variable.woff2",
        Path(f"{family.title()}-VF.woff2"),
    )
    for family in ("sans", "serif")
)


def published_files() -> tuple[tuple[Path, Path], ...]:
    """Return root and /kaiming/ aliases plus Workers routing metadata."""
    assets = SITE_ASSETS + FONT_ASSETS
    return (
        (SOURCE_ROOT / "_headers", Path("_headers")),
        (SOURCE_ROOT / "_redirects", Path("_redirects")),
        *(
            (source, prefix / relative)
            for prefix in PUBLIC_PREFIXES
            for source, relative in assets
        ),
    )


def reset_output_directory() -> None:
    """Remove only the repository's managed public build directory."""
    resolved_root = ROOT.resolve()
    resolved_output = OUTPUT_ROOT.resolve()
    if (
        resolved_output.parent != resolved_root
        or resolved_output.name != "public"
    ):
        raise SystemExit(f"Refusing to replace unexpected path: {resolved_output}")

    is_junction = getattr(OUTPUT_ROOT, "is_junction", lambda: False)
    if OUTPUT_ROOT.is_symlink() or is_junction():
        raise SystemExit("Refusing to replace a linked public directory")
    if OUTPUT_ROOT.exists() and not OUTPUT_ROOT.is_dir():
        raise SystemExit("Refusing to replace public because it is not a directory")
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir()


def main() -> None:
    files = published_files()
    missing = [
        str(source.relative_to(ROOT))
        for source, _ in files
        if not source.is_file()
    ]
    if missing:
        raise SystemExit(
            "Missing Pages inputs; build the fonts first:\n- " + "\n- ".join(missing)
        )

    reset_output_directory()
    for source, relative in files:
        destination = OUTPUT_ROOT / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        print(f"Staged {destination.relative_to(ROOT)}")

    print(
        "Cloudflare static assets are ready at / and /kaiming/ "
        f"in {OUTPUT_ROOT.relative_to(ROOT)}/"
    )


if __name__ == "__main__":
    main()
