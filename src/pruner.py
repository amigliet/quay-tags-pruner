import json
import logging
import os
import re
import requests
import urllib3
import yaml

from requests.packages.urllib3.exceptions import InsecureRequestWarning

# Disable SSL Warnings
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

def setup_logger():
    logger = logging.getLogger('pruner')
    logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s')
    ch.setFormatter(formatter)

    logger.addHandler(ch)
    return logger


def get_orgs_json(quay_host, app_token):
    base_url = f"https://{quay_host}/api/v1/superuser/organizations/"
    get_headers = {'accept': 'application/json', 'Authorization': 'Bearer '+ app_token }
    try:
        response = requests.get(
            base_url,
            headers=get_headers,
            timeout=5.0,
            verify=False
        )
    except requests.ConnectionError as err:
        logger.exception(f"Connection error: {err}")
    else:
        return response.json()


def get_orgs_list(quay_host, app_token):
    org_list_json = get_orgs_json(quay_host, app_token)

    org_list = []
    for o in org_list_json["organizations"]:
        org_list.append(o["name"])

    return org_list


def get_repos_json(quay_host, app_token, quay_org):
    base_url = f"https://{quay_host}/api/v1/repository?namespace={quay_org}"
    get_headers = {'accept': 'application/json', 'Authorization': 'Bearer '+ app_token }
    try:
        response = requests.get(
            base_url,
            headers=get_headers,
            timeout=5.0,
            verify=False
        )
    except requests.ConnectionError as err:
        logger.exception(f"Connection error: {err}")
    else:
        return response.json()


def get_tags_json(quay_host, app_token, quay_org, image):
    base_url = f"https://{quay_host}/api/v1/repository/{quay_org}/{image}/tag/"
    get_headers = {'accept': 'application/json', 'Authorization': 'Bearer '+ app_token }
    try:
        response = requests.get(
            base_url,
            headers=get_headers,
            timeout=5.0,
            verify=False
        )
    except requests.ConnectionError as err:
        logger.exception(f"Connection error: {err}")
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
    get_headers = {'accept': 'application/json', 'Authorization': 'Bearer '+ app_token }
    for tag in tags:
        response = requests.delete(
            f"{base_url}/{tag['name']}",
            headers=get_headers,
            timeout=5.0,
            verify=False
        )
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            if response.status_code == 400:
                logger.info(
                    f"{quay_org}/{image}:{tag['name']} has already been deleted"
                )
            else:
                logger.exception(f"Error deleting tag {tag['name']}: {err}")
        else:
            logger.info(f"{quay_org}/{image}:{tag['name']} deleted")


def apply_pruner_rule(
        quay_host, app_token, organization,
        parameters, debug, dry_run):

    repos = get_repos_json(quay_host, app_token, organization)
    if repos is None:
       return

    logger.debug(
        f"{organization}'s repositories: {json.dumps(repos, indent=4)}"
    )

    for image in repos["repositories"]:
        for param in parameters:
            logger.info(f"Apply filter: {param['tag_filter']}")
            image_tags = get_tags_json(quay_host, app_token, organization,
                                       image["name"])
            if image_tags is None:
                continue

            bad_tags = select_tags_to_remove(image_tags, param["tag_filter"],
                                             int(param["keep_n_tags"]))
            if bad_tags is None:
                logger.info(
                    f"No tags to delete found for image {image['name']} "
                    f"with pattern {param['tag_filter']}"
                )
                continue

            if dry_run:
                logger.info(
                    f"DRY-RUN Candidate tags for deletion "
                    f"for image {image['name']}: "
                    f"{json.dumps(bad_tags, indent=4)}"
                )
            else:
                delete_tags(quay_host, app_token, organization,
                            image["name"], bad_tags)


if __name__ == "__main__":

    logger = setup_logger()

    debug = True if os.getenv('DEBUG', 'False').upper() == 'TRUE' else False
    dryRun = True if os.getenv('DRY_RUN', 'False').upper() == 'TRUE' else False
    quayUrl = os.getenv('QUAY_URL')
    oauthToken = os.getenv('QUAY_APP_TOKEN')

    logger.info(f"DEBUG {debug}, DRY_RUN {dryRun}, QUAY_URL {quayUrl}")
    if debug:
        logger.debug(f"Quay App Token: {oauthToken}")


    configFile = "/opt/conf/config.yaml"
    try:
        with open(configFile, "r") as fp:
            conf_yaml = yaml.safe_load(fp.read())
        if debug:
            logger.debug(f"Loaded file config.yaml:\n{yaml.dump(conf_yaml)}")
    except IOError as err:
        logger.exception(f"Error reading file {configFile}: {err}")
        os._exit(1)

    # Evaluate rules for specific organization lists
    for rule in conf_yaml["rules"]:
        params = rule["parameters"]

        for org in rule["organization_list"]:
            apply_pruner_rule(quayUrl, oauthToken, org, params, debug, dryRun)

    # Evaluate default rule
    if conf_yaml["default_rule"]["enabled"]:

        org_list = get_orgs_list(quayUrl, oauthToken)
        if debug:
            logger.debug(f"Organizations complete list: {org_list}")

        org_exclude_list = []
        for r in conf_yaml["rules"]:
            for o in r["organization_list"]:
                org_exclude_list.append(o)
        if debug:
            logger.debug(f"Organizations exclude list: {org_exclude_list}")

        org_default_list = list(set(org_list).difference(set(org_exclude_list)))
        logger.info(f"Organizations pruned by default_rule: {org_default_list}")

        default_params = conf_yaml["default_rule"]["parameters"]

        for org in org_default_list:
            apply_pruner_rule(quayUrl, oauthToken, org, default_params,
                              debug, dryRun)

