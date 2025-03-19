import datetime
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


def annotate_package(package):
    has_wheel = False
    has_abi_none_wheel = False
    has_free_threaded_wheel = False
    url = get_json_url(package["name"])
    response = SESSION.get(url)
    # Treat data read failures as fatal errors
    response.raise_for_status()
    data = response.json()

    for download in data["urls"]:
        if download["packagetype"] == "bdist_wheel":
            has_wheel = True
            # The wheel filename is:
            # {distribution}-{version}(-{build tag})?-{python tag}-{abi tag}-{platform tag}.whl
            # https://packaging.python.org/en/latest/specifications/binary-distribution-format/#file-name-convention
            abi_tag = download["filename"].removesuffix(".whl").split("-")[-2]

            if abi_tag == "none":
                has_abi_none_wheel = True

            if abi_tag.endswith("t") and abi_tag.startswith("cp31"):
                has_free_threaded_wheel = True

    package["free_threaded_wheel"] = has_free_threaded_wheel
    package["pure_python_wheel"] = has_abi_none_wheel

    # Display logic. I know, I'm sorry.
    package["value"] = 1
    if has_free_threaded_wheel:
        package["css_class"] = "success"
        package["icon"] = "🧵"
        package["title"] = "This package provides at least one free-threaded wheel."
    elif not has_wheel:
        package["css_class"] = "default"
        package["icon"] = "🐍"
        package["title"] = "This package does not publish any wheel archives."
    else:
        package["css_class"] = "warning"
        package["icon"] = "\u2717"  # Ballot X
        package["title"] = (
            "This package publishes binary wheels, but no free-threaded wheels."
        )


def get_top_packages():
    print("Getting packages...")

    with open("top-pypi-packages.json") as data_file:
        packages = json.load(data_file)["rows"]

    # Rename keys
    for package in packages:
        package["downloads"] = package.pop("download_count")
        package["name"] = package.pop("project")

    return packages


def get_annotated_packages(packages, limit):
    annotated_packages = []
    for index, package in enumerate(packages):
        name = package["name"]
        if name in DEPRECATED_PACKAGES:
            continue
        index_text = str(index)
        indent = " " * len(index_text)
        print(f"{index_text} Checking published wheels for {name!r}...")
        annotate_package(package)
        if package["pure_python_wheel"] and not package["free_threaded_wheel"]:
            print(f"{indent}  Skipping (project publishes a pure Python wheel)")
            continue
        annotated_packages.append(package)
        num_packages = len(annotated_packages)
        print(f"{indent}  Added to results ({num_packages}/{limit})")
        if len(annotated_packages) == limit:
            break
    print(f"Scanned {index} packages in total")
    return annotated_packages


def save_to_file(packages, file_name):
    now = datetime.datetime.now(tz=datetime.UTC)
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
