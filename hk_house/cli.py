"""Command-line runner for the source pipelines.

    uv run python -m hk_house.cli centanet --max 200
    uv run python -m hk_house.cli midland --max 1000
    uv run python -m hk_house.cli house730 --ids 9089382,9089383
    uv run python -m hk_house.cli hangseng --area 1 --district 5 --estate 646 --block 5711 --floor 10 --flat A1
    uv run python -m hk_house.cli all --max 100
    uv run python -m hk_house.cli centanet            # full crawl (no --max)
"""

from __future__ import annotations

import argparse
import logging

from .sources.base_pipeline import Pipeline


def _build(source: str, args: argparse.Namespace) -> Pipeline:
    if source == "centanet":
        from .sources.centanet import CentanetPipeline
        return CentanetPipeline()
    if source == "midland":
        from .sources.midland import MidlandPipeline
        return MidlandPipeline(tx_type=args.tx_type.upper())
    if source == "house730":
        from .sources.house730 import House730Pipeline
        ids = [s.strip() for s in args.ids.split(",")] if args.ids else None
        return House730Pipeline(property_ids=ids)
    if source == "hse28":
        from .sources.hse28 import Hse28Pipeline
        return Hse28Pipeline()
    if source == "hangseng":
        from .sources.hangseng import HangSengPipeline
        req = {
            "area": args.area,
            "district": args.district,
            "estate": args.estate,
            "block": args.block,
            "floor": args.floor,
            "flat": args.flat,
            "carpark": args.carpark,
            "openCarpark": args.open_carpark,
        }
        missing = [key for key, value in req.items() if key not in {"carpark", "openCarpark"} and not value]
        if missing:
            raise ValueError(f"hangseng requires: {', '.join(missing)}")
        return HangSengPipeline(valuation_requests=[req])
    raise ValueError(f"unknown source: {source}")


SOURCES = ["centanet", "midland", "house730", "hse28", "hangseng"]
CRAWL_SOURCES = ["centanet", "midland", "house730", "hse28"]


def main() -> None:
    parser = argparse.ArgumentParser(description="HK-House data pipelines")
    parser.add_argument("source", choices=[*SOURCES, "all", "export", "map"])
    parser.add_argument("--max", type=int, default=None, help="max records (omit = all)")
    parser.add_argument("--tx-type", default="S", help="midland: S (sale) or R (rent)")
    parser.add_argument("--ids", default=None, help="house730: comma-separated property ids")
    parser.add_argument("--area", default=None, help="hangseng: area code")
    parser.add_argument("--district", default=None, help="hangseng: district code")
    parser.add_argument("--estate", default=None, help="hangseng: estate code")
    parser.add_argument("--block", default=None, help="hangseng: block code")
    parser.add_argument("--floor", default=None, help="hangseng: floor code")
    parser.add_argument("--flat", default=None, help="hangseng: flat code")
    parser.add_argument("--carpark", default="0", help="hangseng: covered carpark flag")
    parser.add_argument("--open-carpark", default="0", help="hangseng: open carpark flag")
    parser.add_argument("--no-save", action="store_true", help="don't write to disk")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    if args.source == "export":
        from .dataset import build_dataset, summary
        df = build_dataset()
        print(f"[export] {summary(df)}")
        from .dataset import OUTPUT
        print(f"[export] -> {OUTPUT}")
        return

    if args.source == "map":
        from .analysis import build_map, build_stats
        stats = build_stats()
        path = build_map(stats)
        print(f"[map] {len(stats)} districts -> {path}")
        print(stats[["district", "count", "ppf_median", "price_median"]].to_string(index=False))
        return

    targets = CRAWL_SOURCES if args.source == "all" else [args.source]
    for src in targets:
        try:
            pipe = _build(src, args)
            result = pipe.run(max_records=args.max, save=not args.no_save)
            print(
                f"[{result.source}] fetched={result.fetched} parsed={result.parsed} "
                f"errors={result.errors} -> {result.processed_path or '(not saved)'}"
            )
        except Exception as exc:  # noqa: BLE001 -- per-source isolation in `all`
            print(f"[{src}] FAILED: {exc}")


if __name__ == "__main__":
    main()
