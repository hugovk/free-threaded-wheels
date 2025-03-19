from svg_wheel import generate_svg_wheel
from utils import (
    get_annotated_packages,
    get_top_packages,
    save_to_file,
)

TO_CHART = 360


def main(to_chart: int = TO_CHART) -> None:
    packages = get_annotated_packages(get_top_packages(), to_chart)
    save_to_file(packages, "results.json")
    generate_svg_wheel(packages)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "-n", "--number", type=int, default=TO_CHART, help="number of packages to chart"
    )
    args = parser.parse_args()

    main(args.number)
