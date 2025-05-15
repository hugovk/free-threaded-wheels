import datetime as dt
import json
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


def annotate_wheels(packages, to_chart: int) -> list[dict]:
    print("Getting wheel data...")
    num_packages = len(packages)
    total = 0
    keep = []
    for index, package in enumerate(packages):
        print(f"{total + 1}/{to_chart} {index + 1}/{num_packages} {package['name']}")
        if package["name"] in DEPRECATED_PACKAGES:
            continue

        has_other_binary_wheel = False
        has_free_threaded_wheel = False
        has_pure_python_wheel = False
        url = get_json_url(package["name"])
        response = SESSION.get(url)
        if response.status_code != 200:
            print(" ! Skipping " + package["name"])
            continue

        data = response.json()

        for download in data["urls"]:
            if download["packagetype"] == "bdist_wheel":
                # The wheel filename is:
                # {distribution}-{version}(-{build tag})?-{python tag}-{abi tag}-{platform tag}.whl
                # https://packaging.python.org/en/latest/specifications/binary-distribution-format/#file-name-convention
                abi_tag = download["filename"].removesuffix(".whl").split("-")[-2]

                if abi_tag.endswith("t") and abi_tag.startswith("cp31"):
                    has_free_threaded_wheel = True
                elif abi_tag != "none":
                    has_other_binary_wheel = True
                else:
                    has_pure_python_wheel = True

        if has_free_threaded_wheel:
            package["css_class"] = "success"
            package["icon"] = "🧵"
        elif has_other_binary_wheel:
            if not has_pure_python_wheel:
                package["css_class"] = "warning"
                package["icon"] = "\u2717"  # Ballot X
            else:
                package["css_class"] = "pure-py"
                package["icon"] = "🐍"
        else:
            # Don't show packages with only sdists or pure Python wheels
            continue

        package["free_threaded_wheel"] = has_free_threaded_wheel

        keep.append(package)
        total += 1
        if total == to_chart:
            break

    return keep


def get_top_packages():
    print("Getting packages...")

    with open("top-pypi-packages.json") as data_file:
        packages = json.load(data_file)["rows"]

    # Rename keys
    for package in packages:
        package["downloads"] = package.pop("download_count")
        package["name"] = package.pop("project")

    return packages


def save_to_file(packages, file_name):
    now = dt.datetime.now(tz=dt.timezone.utc)
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
