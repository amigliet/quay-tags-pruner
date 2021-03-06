import json
import logging
import os
import re
import requests
import urllib3


def get_repos_json(quay_host, app_token, quay_org):
    base_url = f"https://{quay_host}/api/v1/repository?namespace={quay_org}"
    get_headers = {'accept': 'application/json', 'Authorization': app_token}
    try:
        response = requests.get(
            base_url,
            headers=get_headers,
            timeout=1.0,
            verify=False
        )
    except requests.ConnectionError as err:
        logging.exception(f"Connection error: {err}")
    else:
        return response.json()


def get_tags_json(quay_host, app_token, quay_org, image):
    base_url = f"https://{quay_host}/api/v1/repository/{quay_org}/{image}/tag/"
    get_headers = {'accept': 'application/json', 'Authorization': app_token}
    try:
        response = requests.get(
            base_url,
            headers=get_headers,
            timeout=1.0,
            verify=False
        )
    except requests.ConnectionError as err:
        logging.exception(f"Connection error: {err}")
    else:
        return response.json()


def select_tags_to_remove(tags, pattern, keep_tag_number):
    matches = []
    for tag in tags["tags"]:
        match = re.search(pattern, tag["name"])
        if match:
            matches.append(tag)
    matches_len = len(matches)
    if matches_len > keep_tag_number:
        end_index = matches_len - keep_tag_number
        sorted_matches = sorted(matches, key=lambda t: t["start_ts"])
        return sorted_matches[0:end_index]
    else:
        return []


def delete_tags(quay_host, app_token, quay_org, image, tags):
    base_url = f"https://{quay_host}/api/v1/repository/{quay_org}/{image}/tag"
    get_headers = {'accept': 'application/json', 'Authorization': app_token}
    for tag in tags:
        response = requests.delete(
            f"{base_url}/{tag['name']}",
            headers=get_headers,
            timeout=1.0,
            verify=False
        )
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            if response.status_code == 400:
                logging.info(
                    f"{quay_org}/{image}:{tag['name']} has already been deleted"
                )
            else:
                logging.exception(f"Error deleting tag {tag['name']}: {err}")
        else:
            logging.info(f"{quay_org}/{image}:{tag['name']} deleted")


if __name__ == "__main__":

    authFile = "/opt/secret/auth.json"
    try:
        with open(authFile, "r") as fp:
            auth_json = json.loads(fp.read())
    except IOError as err:
        logging.exception(f"Error reading file {authFile}: {err}")
        os._exit(1)

    authToken = f"Bearer {auth_json['quay_app_token']}"

    configFile = "/opt/conf/config.json"
    try:
        with open(configFile, "r") as fp:
            conf_json = json.loads(fp.read())
    except IOError as err:
        logging.exception(f"Error reading file {configFile}: {err}")
        os._exit(1)

    debug = True if conf_json["vars"]["debug"].upper() == "TRUE" else False
    dryRun = True if conf_json["vars"]["dry_run"].upper() == "TRUE" else False
    quayUrl = conf_json["vars"]["quay_url"]
    tags = conf_json["vars"]["tags"]

    if debug:
        logging.basicConfig(
            format='%(asctime)s %(levelname)s: %(message)s',
            datefmt='%Y/%m/%d %H:%M:%S',
            level=logging.DEBUG
        )
    else:
        logging.basicConfig(
            format='%(asctime)s %(levelname)s: %(message)s',
            datefmt='%Y/%m/%d %H:%M:%S',
            level=logging.INFO
        )
        urllib3.disable_warnings()

    logging.info(f"Quay URL: {quayUrl}")
    logging.debug(f"Quay App Token: {authToken}")
    logging.info(f"Organizations found: {conf_json['vars']['quay_orgs']}")
    logging.info(f"Tags: {tags}")

    for org in conf_json["vars"]["quay_orgs"]:
        repos = get_repos_json(quayUrl, authToken, org)
        if repos is None:
            continue

        logging.debug(f"{json.dumps(repos, indent=4)}")

        for image in repos["repositories"]:
            for tag in tags:
                imageTags = get_tags_json(quayUrl, authToken, org,
                                          image["name"])
                if imageTags is None:
                    continue

                badTags = select_tags_to_remove(imageTags, tag["pattern"],
                                                int(tag["revisions"]))
                if badTags is None:
                    logging.info(
                        f"No tags to delete found for image {image['name']} "
                        f"with pattern {tag['pattern']}"
                    )
                    continue

                if dryRun:
                    logging.info(
                        f"DRY-RUN Candidate tags for deletion "
                        f"for image {image['name']}: "
                        f"{json.dumps(badTags, indent=4)}"
                    )
                else:
                    delete_tags(quayUrl, authToken, org, image["name"],
                                badTags)
