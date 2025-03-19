import datetime
import json

from concurrent.futures import ThreadPoolExecutor

import requests_cache

BASE_URL = "https://pypi.org/pypi"

DEPRECATED_PACKAGES = {
    "BeautifulSoup",
    "bs4",
    "distribute",
    "django-social-auth",
    "nose",
    "pep8",
    "pycrypto",
    "pypular",
    "sklearn",
}

# Keep responses for one hour
SESSION = requests_cache.CachedSession("requests-cache", expire_after=60 * 60)


def get_json_url(package_name):
    return BASE_URL + "/" + package_name + "/json"


def annotate_package(package):
    has_any_wheel = False
    has_other_wheel = False
    has_abi_none_wheel = False
    has_free_threaded_wheel = False
    url = get_json_url(package["name"])
    response = SESSION.get(url)
    # Treat data read failures as fatal errors
    response.raise_for_status()
    data = response.json()

    for download in data["urls"]:
        if download["packagetype"] == "bdist_wheel":
            has_any_wheel = True
            # The wheel filename is:
            # {distribution}-{version}(-{build tag})?-{python tag}-{abi tag}-{platform tag}.whl
            # https://packaging.python.org/en/latest/specifications/binary-distribution-format/#file-name-convention
            abi_tag = download["filename"].removesuffix(".whl").split("-")[-2]

            if abi_tag == "none":
                has_abi_none_wheel = True
            elif abi_tag.endswith("t") and abi_tag.startswith("cp31"):
                has_free_threaded_wheel = True
            else:
                has_other_wheel = True

    package["free_threaded_wheel"] = has_free_threaded_wheel
    only_pure_python = has_abi_none_wheel and not (
        has_free_threaded_wheel or has_other_wheel
    )
    package["only_pure_python"] = only_pure_python

    # Display logic (processed by both the Angular JS code and the SVG generator)
    if has_free_threaded_wheel:
        package["css_class"] = "success"
        package["icon"] = "🧵"
        package["title"] = "This package provides at least one free-threaded wheel."
    elif not has_any_wheel:
        package["css_class"] = "default"
        package["icon"] = "🐍"
        package["title"] = "This package does not publish any wheel archives."
    elif has_other_wheel:
        package["css_class"] = "warning"
        package["icon"] = "\u2717"  # Ballot X
        package["title"] = (
            "This package publishes binary wheels, but no free-threaded wheels."
        )
    else:
        # Pure Python wheels are excluded from the display entirely
        assert only_pure_python, package


def get_top_packages():
    print("Getting packages...")

    with open("top-pypi-packages.json") as data_file:
        packages = json.load(data_file)["rows"]

    # Rename keys
    for package in packages:
        package["downloads"] = package.pop("download_count")
        package["name"] = package.pop("project")

    return packages


def scan_package(package):
    annotate_package(package)
    return package


def omit_deprecated(packages):
    for package in packages:
        if package["name"] in DEPRECATED_PACKAGES:
            continue
        yield package


def get_annotated_packages(packages, limit):
    annotated_packages = []
    packages = list(omit_deprecated(packages))
    with ThreadPoolExecutor() as pool:
        submitted_scans = []
        # Need to scan at least "limit" packages
        for package in packages[:limit]:
            submitted_scans.append(pool.submit(scan_package, package))

        for index, scan_future in enumerate(submitted_scans):
            package = scan_future.result()
            name = package["name"]
            index_text = str(index)
            indent = " " * len(index_text)
            print(f"{index_text} Checking published wheels for {name!r}...")
            if package["only_pure_python"]:
                print(f"{indent}  Skipping (project publishes a pure Python wheel)")
                # This scan failed to find a relevant package, so schedule another
                # The number of pending scans will drop as relevant packages are found
                scan_index = len(submitted_scans)
                submitted_scans.append(pool.submit(scan_package, packages[scan_index]))
                continue
            annotated_packages.append(package)
            num_packages = len(annotated_packages)
            print(f"{indent}  Added to results ({num_packages}/{limit})")
            if len(annotated_packages) == limit:
                # Loop should end naturally at this point anyway,
                # but this makes the intended logic more explicit
                break
    print(f"Scanned {index} packages in total")
    return annotated_packages


def save_to_file(packages, file_name):
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    with open(file_name, "w") as f:
        f.write(
            json.dumps(
                {
                    "data": packages,
                    "last_update": now.strftime("%A, %d %B %Y, %X %Z"),
                },
                indent=1,
            )
        )
