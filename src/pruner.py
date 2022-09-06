import copy
import json
import logging
import os
import re
import requests
import urllib3
import yaml
import time

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

        if response.status_code != 200:
            logger.error(f"Error Quay API request to URL {base_url} has the status code {response.status_code}. The expected status code is 200.\n"
                             f"API response reason: {response.reason}\n"
                             f"API response text: {response.text}")
            os._exit(1)

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

        if response.status_code != 200:
            logger.error(f"Error Quay API request to URL {base_url} has the status code {response.status_code}. The expected status code is 200.\n"
                             f"API response reason: {response.reason}\n"
                             f"API response text: {response.text}")
            os._exit(1)

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

        if response.status_code != 200:
            logger.error(f"Error Quay API request to URL {base_url} has the status code {response.status_code}. The expected status code is 200.\n"
                             f"API response reason: {response.reason}\n"
                             f"API response text: {response.text}")
            os._exit(1)

    except requests.ConnectionError as err:
        logger.exception(f"Connection error: {err}")
    else:
        return response.json()


# This function can be used to print tags' list of dictionary in logs printing only important tags' values
# This function accepts as input a list of dictionary and return as result the same list of dict removing the dict keys
# different from [name,start_ts,last_modified]
def prettify_tag_list_of_dict(input_list):
    result = []
    for tag in input_list:
        result.append({
                     "name" : tag["name"],
                     "last_modified": tag["last_modified"],
                     "start_ts": tag["start_ts"]
                      }
        )
    return result


# This function selects and returns the tags that need to be removed based on the values defined in the variable
# parameter
def select_tags_to_remove(organization,repository,tags, parameter, current_ts):
    logger.debug(
        f"Invoke function select_tags_to_remove with the following parameters:\n"
        f"organization {organization}\n"
        f"repository {repository}\n"
        f"tags {tags}\n"
        f"parameter {parameter}\n"
        f"current_ts {current_ts}\n"
    )

    # The dictionary parameter must be contains at least one of the two keys keep_tags_younger_than and keep_n_tags
    if 'keep_n_tags' not in parameter.keys() and 'keep_tags_younger_than' not in parameter.keys():
        logger.error(
            f"Error: The dictionary parameter of repository {repository} of the organization {organization} must "
            f"contain at least one of the following parameters: keep_n_tags keep_tags_younger_than")
        os._exit(1)

    # Filter tags based on the regular expression defined in tag_filter
    pattern=parameter["tag_filter"]
    matches = []
    for tag in tags["tags"]:
        match = re.search(pattern, tag["name"])
        if match:
            matches.append(tag)
    matches_len = len(matches)

    # If keep_n_tags is defined in parameter, filter the tags that needs to be deleted based on this condition and store
    # them in tag_deleted_by_keep_tag_number
    if "keep_n_tags" in parameter.keys():
        keep_tag_number=int(parameter["keep_n_tags"])
        if matches_len > keep_tag_number:
            end_index = matches_len - keep_tag_number
            sorted_matches = sorted(matches, key=lambda t: t["start_ts"])
            tag_deleted_by_keep_tag_number = sorted_matches[0:end_index]
        else:
            tag_deleted_by_keep_tag_number = []
        logger.debug (f"The tags of the organization '{organization}' and repository '{repository}' that can be "
                      f"deleted based on parameter 'keep_n_tags: '{keep_tag_number}' are: "
                      f"{json.dumps(prettify_tag_list_of_dict(tag_deleted_by_keep_tag_number), indent=4)} ")

    # If keep_tags_younger_than is defined in parameter, filter the tags that needs to be deleted based on this
    # condition and store them in tag_deleted_by_keep_tags_younger_than
    if "keep_tags_younger_than" in parameter.keys():
        keep_tags_younger_than = int(parameter["keep_tags_younger_than"])
        # the unit of measure of keep_tags_younger_than is days,keep_tags_younger_than_seconds convert it in seconds
        keep_tags_younger_than_seconds=keep_tags_younger_than*24*3600
        # Select tags if the different between current timestamp and the tag start_ts value is greater than
        # keep_tags_younger_than_seconds
        tag_deleted_by_keep_tags_younger_than=[tag for tag in matches
                                                   if (current_ts - tag["start_ts"] ) >  keep_tags_younger_than_seconds
                                               ]
        logger.debug(f"The tags of the organization '{organization}' and repository '{repository}' that can be deleted "
                     f"based on parameter 'keep_tags_younger_than: '{keep_tags_younger_than}' are: "
                     f"{json.dumps(prettify_tag_list_of_dict(tag_deleted_by_keep_tags_younger_than), indent=4)}")

    result=[]
    # If keep_n_tags and keep_tags_younger_than parameters are both defined, the function return the intersection of
    # both list tag_deleted_by_keep_tag_number tag_deleted_by_keep_tags_younger_than
    # A tag will be selected to be deleted only if tag is present in tag_deleted_by_keep_tag_number and
    # tag_deleted_by_keep_tags_younger_than
    if 'keep_n_tags' in parameter.keys() and 'keep_tags_younger_than' in parameter.keys():
        for tag1 in tag_deleted_by_keep_tag_number:
            if any(tag2['name'] == tag1['name'] for tag2 in tag_deleted_by_keep_tags_younger_than):
                result.append(copy.deepcopy(tag1))

    # If keep_n_tags parameter is defined and keep_tags_younger_than parameter is not defined, the function returns the
    # tag deleted based on the condition keep_n_tags
    elif 'keep_n_tags' in parameter.keys() and 'keep_tags_younger_than' not in parameter.keys():
        result=tag_deleted_by_keep_tag_number
    # If tag_deleted_by_keep_tags_younger_than parameter is defined and keep_n_tags parameter is not defined, the
    # function returns the tag deleted based on the condition tag_deleted_by_keep_tags_younger_than
    elif 'keep_tags_younger_than' in parameter.keys() and 'keep_n_tags' not in parameter.keys():
        result=tag_deleted_by_keep_tags_younger_than

    logger.info(f"The tags of the organization '{organization}' and repository '{repository}' that can be deleted "
                f"based on all the parameters '{parameter}' are: "
                f"{json.dumps( prettify_tag_list_of_dict(result),indent=4 )}")
    return result


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

        if response.status_code != 200:
            logger.error(f"Error Quay API request to URL {base_url} has the status code {response.status_code}. The expected status code is 200.\n"
                             f"API response reason: {response.reason}\n"
                             f"API response text: {response.text}")
            os._exit(1)

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
    logger.debug(
        f"Invoke function apply_pruner_rule with the following parameters:\n"
        f"quay_host {quay_host}\n"
        f"app_token {app_token}\n"
        f"organization {organization}\n"
        f"parameters {parameters}\n"
        f"debug {debug}\n"
        f"dry_run {dry_run}"
    )

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

            current_ts=int(time.time())
            bad_tags = select_tags_to_remove(organization,image["name"],image_tags, param, current_ts)
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
                    f"{json.dumps( prettify_tag_list_of_dict(bad_tags) , indent=4) }"
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

