import datetime
import json
import pytz
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


def annotate_wheels(packages):
    # TODO we only want to process files with extension modules and skip pure python packages
    print("Getting wheel data...")
    num_packages = len(packages)
    for index, package in enumerate(packages):
        print(index + 1, num_packages, package["name"])
        has_free_threaded_wheel = False
        url = get_json_url(package["name"])
        response = SESSION.get(url)
        if response.status_code != 200:
            print(" ! Skipping " + package["name"])
            continue
        data = response.json()
        all_abi_are_none = True

        for download in data["urls"]:
            if download["packagetype"] == "bdist_wheel":
                # The wheel filename is:
                # {distribution}-{version}(-{build tag})?-{python tag}-{abi tag}-{platform tag}.whl
                # https://packaging.python.org/en/latest/specifications/binary-distribution-format/#file-name-convention
                abi_tag = download["filename"].removesuffix(".whl").split("-")[-2]

                if abi_tag != "none":
                    all_abi_are_none = False

                if abi_tag.endswith("t") and abi_tag.startswith("cp31"):
                    has_free_threaded_wheel = True

        package["wheel"] = has_free_threaded_wheel or all_abi_are_none

        # Display logic. I know, I'm sorry.
        package["value"] = 1
        if has_free_threaded_wheel:
            package["css_class"] = "success"
            package["icon"] = "🧵"
            package["title"] = "This package provides a free-threaded wheel."
        elif all_abi_are_none:
            package["css_class"] = "default"
            package["icon"] = "🐍"
            package["title"] = "This package provides pure Python wheels."
        else:
            package["css_class"] = "warning"
            package["icon"] = "\u2717"  # Ballot X
            package["title"] = "This package has no wheel archives uploaded (yet!)."


def get_top_packages():
    print("Getting packages...")

    with open("top-pypi-packages.json") as data_file:
        packages = json.load(data_file)["rows"]

    # Rename keys
    for package in packages:
        package["downloads"] = package.pop("download_count")
        package["name"] = package.pop("project")

    return packages


def not_deprecated(package):
    return package["name"] not in DEPRECATED_PACKAGES


def remove_irrelevant_packages(packages, limit):
    print("Removing cruft...")
    active_packages = list(filter(not_deprecated, packages))
    return active_packages[:limit]


def save_to_file(packages, file_name):
    now = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
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
