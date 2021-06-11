import json
import logging
import os
import re
import requests
import urllib3


def get_repos_json(quayURL, appToken, quayOrg):
    baseUrl = f"https://{quayUrl}/api/v1/repository?namespace={quayOrg}"
    getHeaders = { 'accept': 'application/json', 'Authorization': appToken }
    try:
        response = requests.get(baseUrl, headers=getHeaders, timeout=1.0, verify=False)
    except requests.ConnectionError as err:
        logging.exception("Connection error: %s", err)
        return None
    return response.json()

def get_tags_json(quayURL, appToken, quayOrg, image):
    baseUrl = f"https://{quayUrl}/api/v1/repository/{quayOrg}/{image}/tag/"
    getHeaders = { 'accept': 'application/json', 'Authorization': appToken }
    try:
        response = requests.get(baseUrl, headers=getHeaders, timeout=1.0, verify=False)
    except requests.ConnectionError as err:
        logging.exception("Connection error: %s", err)
        return None
    return response.json()

def select_tags_to_remove(tags, pattern, keepTagN):
    matches = []
    for tag in tags["tags"]:
        match = re.search(pattern, tag["name"])
        if match:
            matches.append(tag)
    matchesLen = len(matches)
    if matchesLen > keepTagN:
        endIndex = matchesLen - keepTagN
        sortedMatches = sorted(matches, key=lambda t:t["start_ts"])
        return sortedMatches[0:endIndex]
    else:
        return None

def delete_tags(quayURL, appToken, quayOrg, image, tags):
    baseUrl = f"https://{quayUrl}/api/v1/repository/{quayOrg}/{image}/tag"
    getHeaders = { 'accept': 'application/json', 'Authorization': appToken }
    for tag in tags:
        deleteUrl = f"{baseUrl}/{tag['name']}"
        response = requests.delete(deleteUrl, headers=getHeaders, timeout=1.0, verify=False)
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            if response.status_code == 400:
                logging.info("%s/%s:%s has already been deleted", quayOrg, image, tag["name"])
            else:
                logging.exception("Error deleting tag %s: %s", tag["name"], err)
            continue
        logging.info("%s/%s:%s deleted", quayOrg, image, tag["name"])


if __name__ == "__main__":

    authFile = "/opt/secret/auth.json"
    try:
        with open(authFile, "r") as fp:
            auth_json = json.loads(fp.read())
    except IOError as err:
        logging.exception("Error reading file %s: %s", authFile, err)
        os._exit(1)

    authToken = f"Bearer {auth_json['quay_app_token']}"

    configFile = "/opt/conf/config.json"
    try:
        with open(configFile, "r") as fp:
            conf_json = json.loads(fp.read())
    except IOError as err:
        logging.exception("Error reading file %s: %s", configFile, err)
        os._exit(1)

    debug   = True if conf_json["vars"]["debug"].upper() == "TRUE" else False
    dryRun  = True if conf_json["vars"]["dry_run"].upper() == "TRUE" else False
    quayUrl = conf_json["vars"]["quay_url"]
    tags    = conf_json["vars"]["tags"]

    if debug:
        logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', datefmt='%Y/%m/%d %H:%M:%S', level=logging.DEBUG)
    else:
        logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', datefmt='%Y/%m/%d %H:%M:%S', level=logging.INFO)
        urllib3.disable_warnings()

    logging.info(f"Quay URL: {quayUrl}")
    logging.debug(f"Quay App Token: {authToken}")
    logging.info(f"Organizations found: {conf_json['vars']['quay_orgs']}")
    logging.info(f"Tags: {tags}")

    for org in conf_json["vars"]["quay_orgs"]:
        repos = get_repos_json(quayUrl, authToken, org)
        if repos is None:
            logging.info("For org %s there are no repositories", org)
            continue

        logging.debug("%s", json.dumps(repos, indent=4))

        for image in repos["repositories"]:
            for tag in tags:
                imageTags = get_tags_json(quayUrl, authToken, org, image["name"])
                if imageTags is None:
                    continue

                badTags = select_tags_to_remove(imageTags, tag["pattern"], int(tag["revisions"]))
                if badTags is None:
                    logging.info("No tags to delete found for image %s", image["name"])
                    continue

                if dryRun:
                    logging.info("DRY-RUN Candidate tags for deletion for image %s: %s", image["name"], json.dumps(badTags, indent=4))
                else:
                    delete_tags(quayUrl, authToken, org, image["name"], badTags)

